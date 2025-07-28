import json
from pathlib import Path
from extractor import extract_document_structure

# Define input and output directories
INPUT_DIR = Path("/app/input")
OUTPUT_DIR = Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def process_all_pdfs():
    """
    Processes all PDFs in the input directory using the universal
    extraction logic and saves the structured output.
    """
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s) to process.")

    for pdf_file in pdf_files:
        print(f"\nProcessing {pdf_file.name}...")

        # Get the complete structure using the single, generic function
        output_data = extract_document_structure(pdf_file)

        # Write the final data to the output directory
        out_path = OUTPUT_DIR / f"{pdf_file.stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        if "Error:" in output_data["title"]:
             print(f"--> Finished processing {pdf_file.name} with an error.")
        else:
            headings_count = len(output_data.get('outline', []))
            print(f"--> Successfully processed {pdf_file.name}. Found {headings_count} headings.")

if __name__ == "__main__":
    process_all_pdfs()