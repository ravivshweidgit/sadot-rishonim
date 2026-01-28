"""
Convert book cover PDFs (000.pdf) to JPG images for display on the home page.
This script converts books/{book_id}/pdf_pages/000.pdf to books/{book_id}/pdf_pages/000.jpg
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io

def convert_pdf_to_jpg(pdf_path, output_path, dpi=150):
    """
    Convert the first page of a PDF to a JPG image.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path where the JPG will be saved
        dpi: Resolution for the output image (default 150)
    """
    try:
        # Open PDF
        pdf_document = fitz.open(str(pdf_path))
        
        if len(pdf_document) == 0:
            print(f"  [ERROR] PDF {pdf_path.name} has no pages")
            return False
        
        # Get first page
        page = pdf_document[0]
        
        # Convert to image with specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # Scale factor for DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to RGB if necessary (for JPG compatibility)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as JPG with good quality
        img.save(str(output_path), 'JPEG', quality=90, optimize=True)
        
        pdf_document.close()
        
        print(f"  [OK] Converted {pdf_path.name} -> {output_path.name}")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Failed to convert {pdf_path.name}: {e}")
        return False

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Get book IDs from books directory
    books_dir = project_root / "books"
    
    if not books_dir.exists():
        print(f"Error: {books_dir} directory not found!")
        return
    
    # Find all books
    books = [d.name for d in books_dir.iterdir() if d.is_dir()]
    
    if not books:
        print("No books found!")
        return
    
    print(f"Found {len(books)} book(s): {', '.join(books)}\n")
    
    success_count = 0
    total_count = 0
    
    # Process each book
    for book_id in books:
        pdf_pages_dir = books_dir / book_id / "pdf_pages"
        cover_pdf = pdf_pages_dir / "000.pdf"
        
        if not cover_pdf.exists():
            print(f"[SKIP] {book_id}: 000.pdf not found")
            continue
        
        total_count += 1
        cover_jpg = pdf_pages_dir / "000.jpg"
        
        print(f"Processing {book_id}...")
        if convert_pdf_to_jpg(cover_pdf, cover_jpg):
            success_count += 1
        print()
    
    print(f"Conversion complete: {success_count}/{total_count} covers converted successfully")

if __name__ == "__main__":
    main()
