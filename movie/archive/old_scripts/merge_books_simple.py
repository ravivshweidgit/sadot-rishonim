#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט פשוט למזג את שני הספרים לטקסט אחד לפי ציר זמן.
התסריט יהיה הטקסט מהספרים עצמם, בלי יצירה חדשה.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_books_config():
    """Load books configuration"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    config_path = project_root / 'books-config.json'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def read_text_file(file_path):
    """Read text file and return content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def extract_year_from_text(text):
    """Extract year from text (simple pattern matching)"""
    import re
    # Look for 4-digit years between 1900-1921
    years = re.findall(r'\b(19[0-2][0-9]|192[01])\b', text)
    if years:
        return int(years[0])  # Return first year found
    return None

def clean_text(text):
    """Clean text - remove headers, page numbers, etc."""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip page headers like "ראשית ● 9" or "מטולה ● 27"
        if '●' in line and len(line) < 30:
            continue
        # Skip page numbers at end of line
        if line.isdigit() and len(line) < 4:
            continue
        # Skip empty lines (but keep paragraph breaks)
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def process_book(book_id, book_config, project_root):
    """Process a single book and return all pages with metadata"""
    print(f"\nProcessing book: {book_config['name']} ({book_id})")
    
    text_dir = project_root / 'books' / book_id / 'text'
    if not text_dir.exists():
        print(f"  Text directory not found: {text_dir}")
        return []
    
    pages = []
    chapters = book_config.get('chapters', [])
    max_page = book_config.get('maxPage', 0)
    
    # Create chapter lookup
    chapter_lookup = {}
    for chapter in chapters:
        start_page = chapter['page']
        chapter_lookup[start_page] = chapter
    
    # Process each text file
    for page_num in range(max_page + 1):
        page_file = text_dir / f"{page_num:03d}.txt"
        
        if not page_file.exists():
            continue
        
        text = read_text_file(page_file)
        if not text:
            continue
        
        cleaned_text = clean_text(text)
        if not cleaned_text:
            continue
        
        # Find which chapter this page belongs to
        chapter_info = None
        for start_page in sorted(chapter_lookup.keys(), reverse=True):
            if page_num >= start_page:
                chapter_info = chapter_lookup[start_page]
                break
        
        # Try to extract year from text
        year = extract_year_from_text(cleaned_text)
        
        # If no year found, estimate from chapter
        if not year and chapter_info:
            chapter_name = chapter_info.get('name', '')
            if 'בית אבא' in chapter_name:
                year = 1900
            elif 'באר־טוביה' in chapter_name or 'באר טוביה' in chapter_name or 'קוסטינה' in chapter_name:
                year = 1904
            elif 'ביפו' in chapter_name or 'יפו' in chapter_name:
                year = 1904
            elif 'מטולה' in chapter_name:
                year = 1905
            elif 'מלחמת העולם' in chapter_name:
                year = 1914
            elif 'תל-חי' in chapter_name or 'תל חי' in chapter_name:
                year = 1920
            elif 'נהלל' in chapter_name:
                year = 1921
        
        pages.append({
            'book_id': book_id,
            'book_name': book_config['name'],
            'page_number': page_num,
            'chapter': chapter_info['name'] if chapter_info else None,
            'year': year,
            'text': cleaned_text,
            'full_text': cleaned_text
        })
        
        print(f"  Page {page_num:03d}: year={year}, chapter={chapter_info['name'] if chapter_info else 'None'}")
    
    return pages

def merge_books_by_timeline():
    """Merge both books into a single chronological text"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load books configuration
    books_config = load_books_config()
    
    all_pages = []
    
    # Process each book
    for book_id, book_config in books_config['books'].items():
        if book_id in ['sadot_rishonim', 'beit_markovski']:
            pages = process_book(book_id, book_config, project_root)
            all_pages.extend(pages)
    
    # Sort by year, then by page number
    all_pages.sort(key=lambda x: (
        x.get('year') or 9999,  # Pages without year go to end
        x.get('page_number', 0)
    ))
    
    # Create merged text
    merged_text_parts = []
    merged_structure = []
    
    current_year = None
    for page in all_pages:
        year = page.get('year')
        book_name = page.get('book_name')
        page_num = page.get('page_number')
        chapter = page.get('chapter')
        text = page.get('text', '')
        
        # Add year header if year changed
        if year and year != current_year:
            merged_text_parts.append(f"\n\n{'='*60}\nשנה: {year}\n{'='*60}\n")
            current_year = year
        
        # Add book/chapter header
        header = f"\n[מ{book_name}"
        if chapter:
            header += f" - {chapter}"
        header += f", עמוד {page_num}]\n"
        merged_text_parts.append(header)
        
        # Add text
        merged_text_parts.append(text)
        merged_text_parts.append("\n")
        
        # Add to structure
        merged_structure.append({
            'year': year,
            'book': book_name,
            'chapter': chapter,
            'page': page_num,
            'text_length': len(text)
        })
    
    # Combine all text
    merged_text = ''.join(merged_text_parts)
    
    # Save merged text
    output_file = output_dir / 'merged_books_text.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_text)
    
    # Save structure JSON
    structure_file = output_dir / 'merged_books_structure.json'
    with open(structure_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_pages': len(all_pages),
                'books': ['sadot_rishonim', 'beit_markovski'],
                'time_period': '1900-1921'
            },
            'structure': merged_structure
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Merged {len(all_pages)} pages from both books")
    print(f"✅ Saved merged text to: {output_file}")
    print(f"✅ Saved structure to: {structure_file}")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  Total pages: {len(all_pages)}")
    
    # Count by year
    year_counts = {}
    for page in all_pages:
        year = page.get('year')
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    
    print(f"\n  Pages by year:")
    for year in sorted(year_counts.keys()):
        print(f"    {year}: {year_counts[year]} pages")
    
    print(f"\n📝 The merged text is ready to use as script!")
    print(f"   You can now use this text with AI to create narration and video prompts.")

if __name__ == "__main__":
    merge_books_by_timeline()
