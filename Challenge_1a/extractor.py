import fitz  # PyMuPDF
import re
import statistics
from collections import Counter

def _profile_document_styles(doc):
    """Performs a single pass to analyze the document's font styles and create font size hierarchy."""
    spans = []
    font_size_stats = {}
    
    # Collect spans from all pages for comprehensive analysis
    for page in doc:
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                spans.extend(line.get("spans", []))

    if not spans:
        return None

    # Analyze font sizes and their characteristics
    for span in spans:
        size = round(span['size'], 2)
        font = span['font']
        text = span.get('text', '').strip()
        
        if size not in font_size_stats:
            font_size_stats[size] = {
                'count': 0,
                'bold_count': 0,
                'fonts': Counter(),
                'total_chars': 0
            }
        
        font_size_stats[size]['count'] += 1
        font_size_stats[size]['fonts'][font] += 1
        font_size_stats[size]['total_chars'] += len(text)
        
        # Check if font indicates bold/heavy styling
        if any(keyword in font.lower() for keyword in ['bold', 'heavy', 'black', 'demi']):
            font_size_stats[size]['bold_count'] += 1
    
    # Determine body text size (most frequent size with substantial content)
    body_candidates = [(size, stats) for size, stats in font_size_stats.items() 
                      if stats['total_chars'] > 100]  # Minimum character threshold
    
    if body_candidates:
        body_size = max(body_candidates, key=lambda x: x[1]['count'])[0]
    else:
        # Fallback to most common size
        body_size = max(font_size_stats.items(), key=lambda x: x[1]['count'])[0] if font_size_stats else 10.0
    
    # Get most common font
    all_fonts = Counter()
    for stats in font_size_stats.values():
        all_fonts.update(stats['fonts'])
    body_font = all_fonts.most_common(1)[0][0] if all_fonts else "Unknown"
    
    # Create sorted list of unique font sizes (largest first)
    sorted_sizes = sorted(font_size_stats.keys(), reverse=True)
    
    # Identify top 3 largest sizes for heading hierarchy
    heading_sizes = {
        'largest': sorted_sizes[0] if len(sorted_sizes) > 0 else body_size,
        'second_largest': sorted_sizes[1] if len(sorted_sizes) > 1 else body_size,
        'third_largest': sorted_sizes[2] if len(sorted_sizes) > 2 else body_size
    }
    
    return {
        "body_size": body_size, 
        "body_font": body_font,
        "font_size_stats": font_size_stats,
        "heading_sizes": heading_sizes,
        "sorted_sizes": sorted_sizes
    }

def _extract_title(doc, style_profile):
    try:
        if len(doc) == 0:
            return doc.metadata.get('title', 'Untitled')

        page = doc[0]  # Only process the first page (page 0) for the title
        blocks = page.get_text("dict").get("blocks", [])
        
        # Get all text lines from the top portion of the page
        text_lines = []
        top_section = page.rect.height * 0.5  # Look at top half of page
        
        for block in blocks:
            if block['bbox'][1] > top_section:
                continue
                
            for line in block.get("lines", []):
                if not line.get("spans"):
                    continue
                    
                # Get text and span info
                text = "".join(s["text"] for s in line["spans"]).strip()
                if not text or len(text) < 3:
                    continue
                    
                # Clean text
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
                
                span = line["spans"][0]
                
                text_lines.append({
                    'text': text,
                    'y': line['bbox'][1],
                    'size': span['size'],
                    'font': span['font'],
                    'bbox': line['bbox']
                })
        
        if not text_lines:
            return doc.metadata.get('title', 'Untitled')
        
        # Sort by y-position (top to bottom)
        text_lines.sort(key=lambda x: x['y'])
        
        # Find the largest font size in the top section
        max_size = max(line['size'] for line in text_lines)
        body_size = style_profile['body_size']
        
        # Look for title candidates - must be significantly larger than body text
        title_candidates = []
        for line in text_lines:
            # Skip if not significantly larger than body text
            if line['size'] < body_size * 1.3:
                continue
                
            # Skip common non-title patterns
            text_lower = line['text'].lower()
            if any(skip in text_lower for skip in ['page', 'copyright', 'confidential', 'draft']):
                continue
                
            # Skip very long lines (likely paragraphs)
            word_count = len(line['text'].split())
            if word_count > 20:
                continue
                
            # Skip lines that end with periods (likely sentences)
            if line['text'].rstrip().endswith('.'):
                continue
                
            # Calculate score based on size and position
            score = 0
            
            # Size scoring - prefer largest fonts
            size_ratio = line['size'] / body_size
            if size_ratio >= 2.0:
                score += 10
            elif size_ratio >= 1.5:
                score += 7
            elif size_ratio >= 1.3:
                score += 5
            
            # Position scoring - prefer top of page
            relative_y = line['y'] / page.rect.height
            if relative_y < 0.1:
                score += 5
            elif relative_y < 0.2:
                score += 3
            elif relative_y < 0.3:
                score += 1
            
            # Font weight scoring
            font_lower = line['font'].lower()
            if any(weight in font_lower for weight in ['bold', 'heavy', 'black']):
                score += 3
            
            # Reasonable length scoring
            if 3 <= word_count <= 15:
                score += 2
            
            title_candidates.append({
                'text': line['text'],
                'score': score,
                'y': line['y'],
                'size': line['size']
            })
        
        if not title_candidates:
            
            largest_lines = [line for line in text_lines if line['size'] == max_size]
            if largest_lines:
                # Take the topmost largest text
                best_line = min(largest_lines, key=lambda x: x['y'])
                return best_line['text']
            return doc.metadata.get('title', 'Untitled')
        
        # Sort by score, then by position
        title_candidates.sort(key=lambda x: (-x['score'], x['y']))
        best_title = title_candidates[0]['text']
        title_parts = [best_title]
        best_y = title_candidates[0]['y']
        best_size = title_candidates[0]['size']
        remaining_candidates = title_candidates[1:]
        for candidate in remaining_candidates:
            y_diff = abs(candidate['y'] - best_y)
            size_diff = abs(candidate['size'] - best_size)
            
            # More flexible criteria for multi-line titles
            if (y_diff < best_size * 3 and  size_diff < 4 and  candidate['score'] >= 3): 
                combined_text = ' '.join(title_parts + [candidate['text']])
                if not _is_repetitive_text(combined_text):
                    title_parts.append(candidate['text'])
                    best_y = candidate['y']  
                else:
                    break
            else:
                break
        final_title = ' '.join(title_parts).strip()
        final_title = _clean_repetitive_title(final_title)
        final_title = re.sub(r'\s+', ' ', final_title)
        
        return final_title if final_title else doc.metadata.get('title', 'Untitled')

    except Exception as e:
        # Fallback to metadata title if extraction fails
        return doc.metadata.get('title', 'Untitled')

def _is_repetitive_text(text):
    words = text.lower().split()
    if len(words) < 3:
        return False
    word_counts = {}
    for word in words:
        if len(word) > 2: 
            word_counts[word] = word_counts.get(word, 0) + 1
    for count in word_counts.values():
        if count > 3:
            return True
            
    return False

def _clean_repetitive_title(title):
    words = title.split()
    cleaned_words = []
    
    for i, word in enumerate(words):
        if i > 0 and word.lower() == words[i-1].lower():
            continue
        if (i > 1 and 
            word.lower() == words[i-2].lower() and 
            len(cleaned_words) > 1 and 
            cleaned_words[-1].lower() == words[i-1].lower()):
            continue
        cleaned_words.append(word)
    
    return ' '.join(cleaned_words)

def _extract_headings(doc, style_profile, title):
    """
    Extracts headings from page 1 to the end of the PDF.
    Uses enhanced font size dictionary analysis and formatting checks
    to determine heading levels. Supports multilingual content.
    """
    heading_candidates = []
    body_size = style_profile['body_size']
    
    # Enhanced dictionary to store font sizes and their characteristics
    font_size_profiles = {}
    
    # Multi-lingual heading patterns
    heading_patterns = {
        'numbered': r'^(?:\d+\.\d+\.\d+\.\d+|\d+\.\d+\.\d+|\d+\.\d+|\d+\.|[IVXLCDM]+\.|[A-Za-z]\.)\s+',
        'appendix': r'^(appendix|annex|anhang|appendice|附录|부록|приложение|ملحق)\b',
        'chapter': r'^(chapter|chapitre|kapitel|capitolo|capítulo|章|장|глава|فصل)\s+',
        'section': r'^(section|section|abschnitt|sezione|sección|节|섹션|раздел|قسم)\s+'
    }
    
    # Start heading extraction from page 1 (index 1) - skip page 0 which is for title
    for page_num in range(1, len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict", sort=True).get("blocks", [])
        previous_block = None
        
        for block in blocks:
            # Skip headers/footers with more precise detection
            page_height = page.rect.height
            if (block['bbox'][1] < page_height * 0.08 or 
                block['bbox'][3] > page_height * 0.92):
                continue
                
            for line in block.get("lines", []):
                if not line['spans']:
                    continue
                    
                span = line['spans'][0]
                text = "".join(s['text'] for s in line['spans']).strip()
                
                if not text or len(text) < 2:
                    continue
                
                # Enhanced filtering for non-headings
                word_count = len(text.split())
                
                # Skip very long text (likely paragraphs, not headings)
                if word_count > 15:  
                    continue
                
                # Skip text ending with sentence punctuation (likely body text)
                if re.search(r'[.,;:!?]\s*$', text):
                    continue
                
                # Skip very short text (likely not meaningful headings)
                if word_count < 2:
                    continue
                
                # Skip common non-heading patterns
                text_lower = text.lower().strip()
                skip_patterns = {
                    'page', 'seite', 'página', 'pagina', 'страница', '页', '페이지',
                    'copyright', 'confidential', 'draft', 'preliminary',
                    'table of contents', 'inhaltsverzeichnis', 'índice', 'sommaire',
                    'date', 'remarks', 'version', 'revision', 'author', 'title'
                }
                if any(pattern == text_lower for pattern in skip_patterns):  # Exact match
                    continue
                
                # Skip date-like patterns (various formats)
                if (re.match(r'^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}$', text_lower) or
                    re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', text) or
                    re.match(r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}$', text_lower)):
                    continue
                
                # Skip table-like content and single word labels
                if (word_count == 1 and len(text) < 12 and 
                    not re.match(r'^\d+\.', text) and 
                    not any(keyword in text_lower for keyword in ['summary', 'background', 'introduction', 'conclusion', 'appendix'])):
                    continue
                
                # Skip lines that look like table headers or data
                if re.match(r'^[A-Z]{2,}\s*$', text):  # All caps single words/abbreviations
                    continue
                
                # Skip lines with excessive punctuation or special characters
                if len(re.findall(r'[^\w\s]', text)) > len(text) * 0.3:
                    continue
                
                # Enhanced heading detection with multilingual support
                font_lower = span['font'].lower()
                
                # Font style analysis
                is_bold = any(keyword in font_lower for keyword in ['bold', 'heavy', 'black', 'demi'])
                is_medium = any(keyword in font_lower for keyword in ['medium', 'semi'])
                
                # Size analysis using the enhanced profile
                size_ratio = span['size'] / body_size
                is_larger = size_ratio > 1.1
                is_much_larger = size_ratio > 1.5
                
                # Pattern matching (multilingual)
                is_numbered = bool(re.match(heading_patterns['numbered'], text))
                is_appendix = bool(re.match(heading_patterns['appendix'], text.lower()))
                is_chapter = bool(re.match(heading_patterns['chapter'], text.lower()))
                is_section = bool(re.match(heading_patterns['section'], text.lower()))
                
                # Text formatting analysis
                is_all_caps = text.isupper() and word_count <= 10  # Reasonable caps limit
                is_title_case = text.istitle()
                is_short = word_count <= 15
                
                # Position analysis
                line_center = (line['bbox'][0] + line['bbox'][2]) / 2
                page_center = page.rect.width / 2
                is_centered = abs(line_center - page_center) < 50
                is_left_aligned = line['bbox'][0] < page.rect.width * 0.2
                
                # Spacing analysis
                has_space_before = (
                    previous_block and 
                    (block['bbox'][1] - previous_block['bbox'][3]) > body_size * 1.2
                )
                
                # Check if it matches one of the top font sizes from the profile
                is_top_size = abs(span['size'] - style_profile['heading_sizes']['largest']) < 1
                is_second_size = abs(span['size'] - style_profile['heading_sizes']['second_largest']) < 1
                is_third_size = abs(span['size'] - style_profile['heading_sizes']['third_largest']) < 1
                
                # Enhanced scoring system with stricter criteria
                score = 0
                
                # Size-based scoring (more weight)
                if is_much_larger: score += 6
                elif is_larger: score += 4
                elif size_ratio > 1.05: score += 2
                
                # Font style scoring
                if is_bold: score += 4
                elif is_medium: score += 2
                
                # Pattern-based scoring (high weight for clear patterns)
                if is_numbered: score += 6
                if is_chapter: score += 5
                if is_section: score += 4
                if is_appendix: score += 5
                
                # Formatting scoring
                if is_all_caps and word_count <= 5: score += 3  # Only short all-caps
                elif is_title_case: score += 2
                
                # Position scoring (less weight)
                if is_centered: score += 1
                elif is_left_aligned: score += 1
                
                # Context scoring
                if has_space_before: score += 3
                if is_short and word_count >= 2: score += 2  # Reasonable length
                
                # Top font size bonus
                if is_top_size: score += 4
                elif is_second_size: score += 3
                elif is_third_size: score += 2
                
                # Dynamic threshold based on content characteristics
                min_threshold = 8  # Base threshold
                
                # Lower threshold for clearly structured headings
                if is_numbered or is_chapter or is_appendix:
                    min_threshold = 6
                elif is_much_larger and is_bold:
                    min_threshold = 7
                elif word_count <= 5 and is_larger:
                    min_threshold = 7
                
                # Higher threshold for potentially problematic content
                if word_count > 10 or not is_larger:
                    min_threshold = 10
                
                if score >= min_threshold:
                    heading_candidates.append({
                        "text": text,
                        "size": span['size'],
                        "font": span['font'],
                        "page": page_num, 
                        "y": line['bbox'][1],
                        "score": score,
                        "is_numbered": is_numbered,
                        "is_appendix": is_appendix,
                        "is_chapter": is_chapter,
                        "is_section": is_section,
                        "is_bold": is_bold,
                        "is_all_caps": is_all_caps,
                        "size_ratio": size_ratio
                    })
                    
                    # Update enhanced font size profiles
                    rounded_size = round(span['size'], 2)
                    if rounded_size not in font_size_profiles:
                        font_size_profiles[rounded_size] = {
                            'count': 0, 
                            'bold_count': 0, 
                            'caps_count': 0, 
                            'total_score': 0,
                            'avg_score': 0,
                            'numbered_count': 0,
                            'fonts': Counter()
                        }
                    
                    profile = font_size_profiles[rounded_size]
                    profile['count'] += 1
                    profile['fonts'][span['font']] += 1
                    if is_bold: profile['bold_count'] += 1
                    if is_all_caps: profile['caps_count'] += 1
                    if is_numbered: profile['numbered_count'] += 1
                    profile['total_score'] += score
                    profile['avg_score'] = profile['total_score'] / profile['count']
                    
            previous_block = block
    
    if not heading_candidates:
        return []
    
    outline = []
    
    # Process special headings first (chapters, appendices)
    special_headings = [h for h in heading_candidates if h['is_chapter'] or h['is_appendix']]
    special_headings.sort(key=lambda x: (x['page'], x['y']))
    for h in special_headings:
        level = "H1"  # Chapters and appendices are typically top-level
        outline.append({
            "level": level,
            "text": h['text'],
            "page": h['page']
        })
    
    # Process numbered headings with enhanced hierarchy detection
    numbered_headings = [h for h in heading_candidates if h['is_numbered'] and not h['is_chapter'] and not h['is_appendix']]
    numbered_headings.sort(key=lambda x: (x['page'], x['y']))
    for h in numbered_headings:
        # Enhanced numbering pattern analysis
        text = h['text']
        level = "H1"  # Default
        
        if re.match(r'^\d+\.\d+\.\d+\.\d+', text):
            level = "H4"
        elif re.match(r'^\d+\.\d+\.\d+', text):
            level = "H3"
        elif re.match(r'^\d+\.\d+', text):
            level = "H2"
        elif re.match(r'^\d+\.', text):
            level = "H1"
        elif re.match(r'^[IVXLCDM]+\.', text):  # Roman numerals
            level = "H1"
        elif re.match(r'^[A-Za-z]\.', text):  # Alphabetical
            level = "H2"  # Often sub-level
        
        outline.append({
            "level": level,
            "text": text,
            "page": h['page']
        })
    unnumbered_headings = [h for h in heading_candidates 
                          if not h['is_numbered'] and not h['is_appendix'] and not h['is_chapter']]
    
    if unnumbered_headings:
        # Create a more sophisticated font size hierarchy
        # Use the pre-computed heading sizes from style_profile
        heading_sizes = style_profile['heading_sizes']
        
        # Create size-to-level mapping using multiple criteria
        size_level_map = {}
        
        # Get all unique sizes from unnumbered headings
        unique_sizes = list(set(round(h['size'], 2) for h in unnumbered_headings))
        unique_sizes.sort(reverse=True)  # Largest first
        
        # Enhanced size tier analysis with better hierarchy detection
        size_analysis = {}
        for size in unique_sizes:
            headings_with_size = [h for h in unnumbered_headings if abs(h['size'] - size) < 0.5]
            
            size_analysis[size] = {
                'count': len(headings_with_size),
                'avg_score': sum(h['score'] for h in headings_with_size) / len(headings_with_size),
                'bold_ratio': sum(1 for h in headings_with_size if h['is_bold']) / len(headings_with_size),
                'caps_ratio': sum(1 for h in headings_with_size if h['is_all_caps']) / len(headings_with_size),
                'size_ratio': size / body_size,
                'headings': headings_with_size
            }
        
        # Improved sorting: prioritize size first, then formatting characteristics
        def improved_composite_score(size):
            analysis = size_analysis[size]
            # Weight size more heavily, then bold/formatting
            size_weight = analysis['size_ratio'] * 0.6
            format_weight = (analysis['bold_ratio'] + analysis['caps_ratio']) * 0.3
            score_weight = (analysis['avg_score'] / 10) * 0.1  # Normalize score
            return size_weight + format_weight + score_weight
        
        sorted_sizes = sorted(unique_sizes, key=improved_composite_score, reverse=True)
        
        # Conservative level assignment with stricter thresholds
        level_thresholds = {
            'H1': {'min_size_ratio': 1.6, 'min_score': 10},
            'H2': {'min_size_ratio': 1.4, 'min_score': 8}, 
            'H3': {'min_size_ratio': 1.2, 'min_score': 7},
            'H4': {'min_size_ratio': 1.1, 'min_score': 6}
        }
        
        # Assign levels based on both size and characteristics
        assigned_levels = set()
        for size in sorted_sizes:
            analysis = size_analysis[size]
            
            # Determine appropriate level based on characteristics
            assigned_level = None
            for level, thresholds in level_thresholds.items():
                if (level not in assigned_levels and 
                    analysis['size_ratio'] >= thresholds['min_size_ratio'] and
                    analysis['avg_score'] >= thresholds['min_score']):
                    assigned_level = level
                    assigned_levels.add(level)
                    break
            
            # Fallback assignment for remaining sizes
            if not assigned_level:
                for level in ['H1', 'H2', 'H3', 'H4']:
                    if level not in assigned_levels:
                        assigned_level = level
                        assigned_levels.add(level)
                        break
            
            if assigned_level:
                # Group similar sizes together
                for check_size in unique_sizes:
                    if abs(check_size - size) < 1.0:  # Similar sizes
                        size_level_map[check_size] = assigned_level
        
        # Apply level mapping to unnumbered headings
        unnumbered_headings.sort(key=lambda x: (x['page'], x['y']))
        for h in unnumbered_headings:
            size_key = round(h['size'], 2)
            
            # Find the closest mapped size
            closest_size = min(size_level_map.keys(), 
                             key=lambda s: abs(s - size_key), 
                             default=None)
            
            if closest_size and abs(closest_size - size_key) < 2.0:
                level = size_level_map[closest_size]
                
                # Enhanced text cleaning
                clean_text = h['text'].strip()
                # Remove trailing dots, numbers, underscores from TOC-style entries
                clean_text = re.sub(r'\s*[\._]{2,}\s*(\d+|[ivx]+)\s*$', '', clean_text)
                # Remove excessive whitespace and control characters
                clean_text = re.sub(r'\s+', ' ', clean_text)
                clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', clean_text)
                # Remove leading/trailing punctuation and whitespace
                clean_text = re.sub(r'^[\s\._]+|[\s\._]+$', '', clean_text)
                
                # Additional filtering
                if (clean_text and 
                    len(clean_text) > 2 and
                    clean_text.lower() != title.lower() and
                    not clean_text.lower() in {'table of contents', 'contents', 'index'}):
                    
                    outline.append({
                        "level": level,
                        "text": clean_text,
                        "page": h['page']
                    })
    
    # Final sort by page and remove duplicates
    outline.sort(key=lambda x: (x['page'], x['text']))
    
    # Remove duplicate headings (same text and page)
    seen = set()
    filtered_outline = []
    for item in outline:
        key = (item['text'].lower(), item['page'])
        if key not in seen:
            seen.add(key)
            filtered_outline.append(item)
    return filtered_outline

def extract_document_structure(pdf_path):
    """Main function to extract document structure."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {"title": f"Error: Failed to open or read PDF: {e}", "outline": []}

    if len(doc) == 0:
        return {"title": "Error: Empty or invalid PDF.", "outline": []}

    style_profile = _profile_document_styles(doc)
    if not style_profile:
        doc.close()
        return {"title": "Error: PDF contains no text content.", "outline": []}

    try:
        title = _extract_title(doc, style_profile)
        outline = _extract_headings(doc, style_profile, title)
    except Exception as e:
        return {"title": f"Error: Failed during content extraction: {e}", "outline": []}
    finally:
        doc.close()

    return {"title": title, "outline": outline}
