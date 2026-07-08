import sys

from pypdf import PdfReader


def read_pdf(path):
    reader = PdfReader(path)
    print(f"File: {path}")
    print(f"Pages: {len(reader.pages)}\n")
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        print(f"===== PAGE {i + 1} =====")
        print(text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_pdf.py <file.pdf>")
        sys.exit(1)
    read_pdf(sys.argv[1])
