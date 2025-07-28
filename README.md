# Adobe Hackathon Challenge 1A 

This repository contains a CPU-only, Dockerized Python solution for extracting structured outlines from PDFs. It identifies the document **title** and **headings (H1, H2, H3)** based on visual layout, font size, and other features.
## Features

- Extracts:
  - Title
  - H1, H2, H3 headings
  - Page numbers
- Uses font size, boldness, and positional rules (no external APIs)
- Offline and lightweight
- Fast execution (<10s for 50-page PDFs)

---

## 📁 Folder Structure

├── process_pdfs.py # Main script to process all PDFs
├── extractor.py # Heading & title detection logic
├── Dockerfile # Offline, CPU-only Docker environment
├── requirements.txt # Python dependencies
├── input/ # Put your PDFs here before running
├── output/ # Outputs JSON files here after run

## Approach

- **Font-based heuristics**: Uses PyMuPDF to analyze font size, weight, and positioning.
- **Rule-based structure**: Determines hierarchy levels (H1–H3) based on visual layout and regex patterns.
- **Title detection**: Extracts the most prominent text block on the first page.
- **Output format**: Follows the required schema structure (see `output_schema.json`).

## Libraries Used

- [`pymupdf`](https://pymupdf.readthedocs.io/) (for PDF parsing)
- Python Standard Libraries (`json`, `os`, `pathlib`)

## How to Run (via Docker)

1. **Build Docker Image**:
docker build --platform linux/amd64 -t <reponame.someidentifier> .

docker build --platform=linux/amd64 -t pdf-outline-extractor .
3. **Run the container**:
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output/repoidentifier/:/app/output --network none <reponame.someidentifier>
**Replace $(pwd) with your local path if using Windows**:
docker run --rm -v D:/Challenge_1a/sample_dataset/pdfs:/app/input:ro -v D:/Challenge_1a/sample_dataset/outputs:/app/output --network none pdf-outline-extractor



