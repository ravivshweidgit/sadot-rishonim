# PDF OCR using Gemini API

This script uses Google's Gemini 1.5 Pro API to extract text from PDF files using OCR.

## Setup

1. Install Python dependencies:
```bash
# In WSL:
pip3 install --user -r requirements.txt

# Or in Windows:
pip install -r requirements.txt
```

**Note:** No additional system dependencies needed! The script uses PyMuPDF which doesn't require Poppler.

## Usage

**Process a specific PDF file:**
```bash
# From python directory (defaults to sadot_rishonim book):
python ocr_pdfs.py 010

# Specify a book:
python ocr_pdfs.py --book beit_markovski 010
python ocr_pdfs.py -b sadot_rishonim 010

# This will process books/{book_id}/pdf_pages/010.pdf and save to books/{book_id}/text/010.txt
```

**Process all PDF files:**
```bash
# From python directory (defaults to sadot_rishonim book):
python ocr_pdfs.py

# Specify a book:
python ocr_pdfs.py --book beit_markovski
python ocr_pdfs.py -b sadot_rishonim

# Or from WSL:
cd "/mnt/g/My Drive/Sadot_rishonim/python"
python3 ocr_pdfs.py --book sadot_rishonim

# Or from Windows project root:
python python/ocr_pdfs.py --book sadot_rishonim
```

The script will:
- Process all PDF files in the `books/{book_id}/pdf_pages/` folder
- Extract text using Gemini OCR
- Save extracted text to the `books/{book_id}/text/` folder
- Default book is `sadot_rishonim` if not specified

## Notes

- The API key is configured in the script
- Hebrew text extraction is supported
- Processing time depends on PDF size and number of pages
- Free tier has rate limits - large batches may need delays between requests

