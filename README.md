# Adobe Hackathon Challenge 1A 

This repository contains a CPU-only, Dockerized Python solution for extracting structured outlines from PDFs. It identifies the document **title** and **headings (H1, H2, H3)** based on visual layout, font size, and other features.

---

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


---

## How to Run (via Docker)

1. **Build Docker Image**:
docker build --platform=linux/amd64 -t pdf-outline-extractor .
2. **Run with PDF files**:
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output pdf-outline-extractor
**Replace $(pwd) with your local path if using Windows**:
docker run --rm -v D:/Adobe/input:/app/input -v D:/Adobe/output:/app/output pdf-outline-extractor


