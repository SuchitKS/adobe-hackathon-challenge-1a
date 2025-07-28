FROM python:3.10-slim

WORKDIR /app

# Directly install only pymupdf (minimal and fast)
RUN pip install --no-cache-dir pymupdf==1.23.14

COPY . .

CMD ["python", "process_titles.py"]
