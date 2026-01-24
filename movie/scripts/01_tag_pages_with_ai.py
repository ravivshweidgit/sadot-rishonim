#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט שיוצר תבנית לתיוג עמודים עם AI.
הסקריפט יוצר קובץ JSON עם כל העמודים, ואז אתה יכול לשלוח ל-AI לתיוג.
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
        # Keep all lines (including empty ones for structure)
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def prepare_page_with_line_numbers(text):
    """Prepare page text with line numbers for AI tagging.
    
    Returns:
        dict with:
        - 'full_text': The complete text
        - 'lines': List of dicts with 'line_number', 'text', 'is_empty'
        - 'total_lines': Total number of lines
        - 'non_empty_lines': Number of non-empty lines
    """
    lines = text.split('\n')
    line_entries = []
    non_empty_count = 0
    
    for line_num, line in enumerate(lines, start=1):
        is_empty = not line.strip()
        if not is_empty:
            non_empty_count += 1
        
        line_entries.append({
            'line_number': line_num,
            'text': line,
            'is_empty': is_empty
        })
    
    return {
        'full_text': text,
        'lines': line_entries,
        'total_lines': len(lines),
        'non_empty_lines': non_empty_count
    }

def create_tagging_template():
    """Create a JSON template for AI tagging"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load books configuration
    books_config = load_books_config()
    
    pages_to_tag = []
    
    # Process each book
    for book_id, book_config in books_config['books'].items():
        if book_id not in ['sadot_rishonim', 'beit_markovski']:
            continue
        
        print(f"\nProcessing book: {book_config['name']} ({book_id})")
        
        text_dir = project_root / 'books' / book_id / 'text'
        if not text_dir.exists():
            print(f"  Text directory not found: {text_dir}")
            continue
        
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
            
            # Prepare page with line numbers
            page_structure = prepare_page_with_line_numbers(cleaned_text)
            
            # Create page entry with line structure
            page_entry = {
                'id': f"{book_id}_page_{page_num:03d}",
                'book_id': book_id,
                'book_name': book_config['name'],
                'page_number': page_num,
                'chapter': chapter_info['name'] if chapter_info else None,
                'full_text': page_structure['full_text'],  # Full page text
                'lines': page_structure['lines'],  # Lines with numbers for AI to tag
                # These will be filled by AI - list of tags per line/range:
                'line_tags': None  # Will be: [{'line_start': 1, 'line_end': 5, 'year': 1904, 'month': None, 'location': 'metula', ...}, ...]
            }
            
            pages_to_tag.append(page_entry)
            total_lines = page_structure.get('total_lines', len(page_structure['lines']))
            non_empty = page_structure.get('non_empty_lines', sum(1 for line in page_structure['lines'] if not line['is_empty']))
            print(f"  Page {page_num:03d}: {total_lines} lines ({non_empty} non-empty) ready for tagging")
    
    # Create output structure
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(pages_to_tag),
            'books': ['sadot_rishonim', 'beit_markovski'],
            'tagging_granularity': 'line_ranges',  # AI tags ranges of lines within each page
            'instructions': 'For each page, tag ranges of lines (or individual lines) with year, month (if available), location, and other metadata. Each line range should be tagged independently based on its content. Python will use these tags to merge pages while preserving line numbers.'
        },
        'pages': pages_to_tag
    }
    
    # Save template
    template_file = output_dir / 'pages_for_ai_tagging.json'
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # Calculate approximate file size
    import sys
    estimated_size = sys.getsizeof(json.dumps(output, ensure_ascii=False)) / (1024 * 1024)  # MB
    
    # Calculate statistics
    total_lines = sum(len(page.get('lines', [])) for page in pages_to_tag)
    total_non_empty = sum(
        sum(1 for line in page.get('lines', []) if not line.get('is_empty', True))
        for page in pages_to_tag
    )
    
    print(f"\n✅ Created tagging template with {len(pages_to_tag)} pages")
    print(f"✅ Saved to: {template_file}")
    print(f"📊 Estimated file size: ~{estimated_size:.1f} MB")
    print(f"📝 Tagging granularity: Line-ranges within pages (Python-friendly!)")
    print(f"\n📊 Statistics:")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Non-empty lines: {total_non_empty:,}")
    print(f"   Average lines per page: {total_lines // len(pages_to_tag) if pages_to_tag else 0}")
    
    print(f"\n📝 Next steps:")
    print(f"   1. Run: python 02_tag_pages_with_gemini.py")
    print(f"      (This will automatically tag all pages using Gemini API)")
    print(f"   2. Or manually: Open {template_file} and send to ChatGPT/Claude")
    print(f"      AI should tag ranges of lines (or individual lines) within each page")
    print(f"      Each tag should include: line_start, line_end, year, month, location, etc.")
    print(f"   3. Save the tagged result as 'pages_tagged_by_ai.json'")
    print(f"   4. Run: python 03_merge_books_with_ai_tags.py to merge based on tags")
    
    if estimated_size > 10:
        print(f"\n⚠️  Note: File is large ({estimated_size:.1f} MB).")
        print(f"   If AI has trouble, you can split into batches (see AI_TAGGING_INSTRUCTIONS.md)")

if __name__ == "__main__":
    create_tagging_template()
