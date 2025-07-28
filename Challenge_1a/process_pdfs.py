import json
from pathlib import Path
from extractor import extract_document_structure

def process_pdfs():
    print("Starting processing PDFs")

    # Define input and output directories
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all PDF files in the input directory
    pdf_files = list(input_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s) to process.")

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")

        # Extract document structure using actual logic
        output_data = extract_document_structure(pdf_file)

        # Write the structured output to a JSON file
        output_file = output_dir / f"{pdf_file.stem}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

        if "Error:" in output_data.get("title", ""):
            print(f"--> Finished {pdf_file.name} with an error.")
        else:
            headings_count = len(output_data.get("outline", []))
            print(f"--> Successfully processed. Found {headings_count} headings.")

    print("Completed processing PDFs")

if __name__ == "__main__":
    process_pdfs()
