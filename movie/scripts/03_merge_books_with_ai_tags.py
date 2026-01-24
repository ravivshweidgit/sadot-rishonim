#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט שממזג את שני הספרים לפי insertion points שקבע AI.

הגישה החדשה:
1. הספר של יהודה (שדות ראשונים) נשאר בסדר המקורי שלו
2. קטעים מהספר של רוחמה (בית מרקובסקי) נכנסים בנקודות שקבע AI
3. AI קבע insertion points לפי הקשר כרונולוגי ונרטיבי

קורא:
- pages_tagged_by_ai.json - תיוגים של כל העמודים
- insertion_points.json - נקודות הכנסה שקבע AI

ואז ממזג את הספרים לפי ה-insertion points.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_ai_tagged_pages():
    """Load pages with line tags that were tagged by AI"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    tagged_file = project_root / 'movie' / 'output' / 'scripts' / 'pages_tagged_by_ai.json'
    
    if not tagged_file.exists():
        print(f"Error: {tagged_file} not found.")
        print(f"Please tag pages first using AI (run 02_tag_pages_with_gemini.py), then save as 'pages_tagged_by_ai.json'")
        return None
    
    with open(tagged_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_insertion_points():
    """Load insertion points determined by AI"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    insertion_file = project_root / 'movie' / 'output' / 'scripts' / 'insertion_points.json'
    
    if not insertion_file.exists():
        print(f"Warning: {insertion_file} not found.")
        print(f"Please run 02b_determine_insertion_points.py first to determine insertion points.")
        return None
    
    with open(insertion_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_line_range(page, line_start, line_end):
    """Validate that a line range is valid for a page"""
    if not isinstance(line_start, int) or not isinstance(line_end, int):
        return False, "Line numbers must be integers"
    
    if line_start < 1 or line_end < 1:
        return False, "Line numbers must be >= 1"
    
    if line_start > line_end:
        return False, f"line_start ({line_start}) > line_end ({line_end})"
    
    lines = page.get('lines', [])
    max_line = max([line.get('line_number', 0) for line in lines], default=0)
    
    if line_end > max_line:
        return False, f"line_end ({line_end}) > max line ({max_line})"
    
    return True, None

def extract_text_from_line_range(page, line_start, line_end):
    """Extract text from a specific line range in a page"""
    lines = page.get('lines', [])
    text_lines = []
    
    for line in lines:
        line_num = line.get('line_number', 0)
        if line_start <= line_num <= line_end:
            text_lines.append(line.get('text', ''))
    
    return '\n'.join(text_lines)

def check_line_coverage(page):
    """Check which lines are covered by tags and which are missing"""
    lines = page.get('lines', [])
    line_tags = page.get('line_tags', [])
    
    if not line_tags:
        return {
            'total_lines': len(lines),
            'covered_lines': set(),
            'missing_lines': set(range(1, len(lines) + 1)),
            'overlapping_ranges': [],
            'invalid_ranges': []
        }
    
    covered_lines = set()
    invalid_ranges = []
    overlapping_ranges = []
    
    # Check each tag
    for i, tag in enumerate(line_tags):
        line_start = tag.get('line_start')
        line_end = tag.get('line_end')
        
        # Validate range
        is_valid, error_msg = validate_line_range(page, line_start, line_end)
        if not is_valid:
            invalid_ranges.append({
                'tag_index': i,
                'line_start': line_start,
                'line_end': line_end,
                'error': error_msg
            })
            continue
        
        # Check for overlaps with previous ranges
        tag_range = set(range(line_start, line_end + 1))
        for prev_tag in line_tags[:i]:
            prev_start = prev_tag.get('line_start')
            prev_end = prev_tag.get('line_end')
            if prev_start and prev_end:
                prev_range = set(range(prev_start, prev_end + 1))
                if tag_range & prev_range:  # Overlap detected
                    overlapping_ranges.append({
                        'tag1': {'start': prev_start, 'end': prev_end},
                        'tag2': {'start': line_start, 'end': line_end}
                    })
        
        # Add to covered lines
        covered_lines.update(tag_range)
    
    # Find missing lines (non-empty lines that aren't covered)
    all_line_nums = set(range(1, len(lines) + 1))
    non_empty_lines = {line.get('line_number', 0) for line in lines if line.get('text', '').strip()}
    missing_lines = non_empty_lines - covered_lines
    
    return {
        'total_lines': len(lines),
        'covered_lines': covered_lines,
        'missing_lines': missing_lines,
        'overlapping_ranges': overlapping_ranges,
        'invalid_ranges': invalid_ranges
    }

def merge_by_insertion_points(tagged_data, insertion_data):
    """Merge books based on insertion points determined by AI.
    
    Preserves the original order of Yehuda's book (sadot_rishonim)
    and inserts Ruchama's book (beit_markovski) segments at the points determined by AI.
    """
    pages = tagged_data.get('pages', [])
    insertion_points = insertion_data.get('insertion_points', []) if insertion_data else []
    
    # Separate books
    yehuda_pages = [p for p in pages if p.get('book_id') == 'sadot_rishonim']
    ruchama_pages = [p for p in pages if p.get('book_id') == 'beit_markovski']
    
    # Sort by page number (preserve original order)
    yehuda_pages.sort(key=lambda p: p.get('page_number', 0))
    ruchama_pages.sort(key=lambda p: p.get('page_number', 0))
    
    # Create lookup for Ruchama paragraphs (AI divided pages into paragraphs)
    ruchama_paragraphs_lookup = {}
    for ip in insertion_points:
        source_page = ip.get('source_page')
        source_line_start = ip.get('source_line_start')
        source_line_end = ip.get('source_line_end')
        
        # Find the page
        ruchama_page = next((p for p in ruchama_pages if p.get('page_number') == source_page), None)
        if ruchama_page:
            # Extract text for this paragraph (line range)
            text = extract_text_from_line_range(ruchama_page, source_line_start, source_line_end)
            key = f"{source_page}_{source_line_start}_{source_line_end}"
            ruchama_paragraphs_lookup[key] = {
                'page': ruchama_page,
                'text': text,
                'line_start': source_line_start,
                'line_end': source_line_end,
                'insertion_point': ip
            }
    
    # Build a list of all content segments (Yehuda + Ruchama) with their insertion positions
    all_segments = []
    inserted_segments = set()  # Track which Ruchama segments we've already inserted
    
    # Add all Yehuda pages with their positions (simple: whole pages)
    for yehuda_page in yehuda_pages:
        page_num = yehuda_page.get('page_number')
        chapter = yehuda_page.get('chapter', '')
        text = yehuda_page.get('full_text', '')
        
        all_segments.append({
            'type': 'yehuda',
            'page': page_num,
            'chapter': chapter,
            'text': text,
            'insert_position': (page_num, 0)  # Position: (page, line=0 means after whole page)
        })
    
    # Add Ruchama paragraphs at their insertion points (AI divided pages into paragraphs)
    for ip in insertion_points:
        source_page = ip.get('source_page')
        source_line_start = ip.get('source_line_start')
        source_line_end = ip.get('source_line_end')
        key = f"{source_page}_{source_line_start}_{source_line_end}"
        
        if key in ruchama_paragraphs_lookup and key not in inserted_segments:
            para_data = ruchama_paragraphs_lookup[key]
            ruchama_page = para_data['page']
            text = para_data['text']
            
            insert_after_page = ip.get('insert_after_page', 0)
            insert_after_line = ip.get('insert_after_line', 0)
            
            all_segments.append({
                'type': 'ruchama',
                'page': ruchama_page.get('page_number'),
                'chapter': ruchama_page.get('chapter', ''),
                'line_start': source_line_start,
                'line_end': source_line_end,
                'text': text,
                'insert_position': (insert_after_page, insert_after_line),
                'insert_reason': ip.get('insert_reason'),
                'confidence': ip.get('confidence', 'medium')
            })
            
            inserted_segments.add(key)
    
    # Sort all segments by insertion position
    # Yehuda segments keep their original order, Ruchama segments inserted at their points
    all_segments.sort(key=lambda s: (
        s['insert_position'][0],  # First by page
        s['insert_position'][1],  # Then by line (0 = after whole page)
        0 if s['type'] == 'yehuda' else 1  # Yehuda segments come first at same position
    ))
    
    # Build merged text
    merged_text_parts = []
    merged_structure = []
    
    for segment in all_segments:
        if segment['type'] == 'yehuda':
            # Full page from Yehuda's book
            header = f"\n[משדות ראשונים - {segment['chapter']}, עמוד {segment['page']}]\n"
            
            merged_text_parts.append(header)
            merged_text_parts.append(segment['text'])
            merged_text_parts.append("\n")
            
            merged_structure.append({
                'book': 'sadot_rishonim',
                'page': segment['page'],
                'preserved_order': True
            })
        
        else:  # ruchama
            # Paragraph from Ruchama's book (AI divided pages into paragraphs)
            header = f"\n[מבית מרקובסקי - {segment['chapter']}, עמוד {segment['page']}, שורות {segment.get('line_start')}-{segment.get('line_end')}"
            if segment.get('insert_reason'):
                header += f" | {segment['insert_reason']}"
            header += "]\n"
            
            merged_text_parts.append(header)
            merged_text_parts.append(segment['text'])
            merged_text_parts.append("\n")
            
            merged_structure.append({
                'book': 'beit_markovski',
                'page': segment['page'],
                'line_start': segment.get('line_start'),
                'line_end': segment.get('line_end'),
                'inserted_after_page': segment['insert_position'][0],
                'inserted_after_line': segment['insert_position'][1],
                'insert_reason': segment.get('insert_reason'),
                'confidence': segment.get('confidence', 'medium')
            })
    
    merged_text = ''.join(merged_text_parts)
    return merged_text, merged_structure

def merge_by_ai_tags(tagged_data):
    """Merge books based on AI tags (year, month, location) - OLD METHOD"""
    pages = tagged_data.get('pages', [])
    
    print(f"Processing {len(pages)} tagged pages...")
    
    # Validate and check coverage for each page
    validation_results = []
    total_invalid_ranges = 0
    total_overlapping_ranges = 0
    total_missing_lines = 0
    
    for page in pages:
        page_num = page.get('page_number', '?')
        book_name = page.get('book_name', '?')
        coverage = check_line_coverage(page)
        
        validation_results.append({
            'page': page_num,
            'book': book_name,
            'coverage': coverage
        })
        
        total_invalid_ranges += len(coverage['invalid_ranges'])
        total_overlapping_ranges += len(coverage['overlapping_ranges'])
        total_missing_lines += len(coverage['missing_lines'])
    
    # Print validation summary
    if total_invalid_ranges > 0 or total_overlapping_ranges > 0 or total_missing_lines > 0:
        print(f"\n⚠️  Validation Results:")
        print(f"  Invalid line ranges: {total_invalid_ranges}")
        print(f"  Overlapping ranges: {total_overlapping_ranges}")
        print(f"  Missing lines (not tagged): {total_missing_lines}")
        
        # Show details for pages with issues
        for result in validation_results:
            coverage = result['coverage']
            if coverage['invalid_ranges'] or coverage['overlapping_ranges'] or coverage['missing_lines']:
                print(f"\n  Page {result['page']} ({result['book']}):")
                if coverage['invalid_ranges']:
                    print(f"    ❌ Invalid ranges: {len(coverage['invalid_ranges'])}")
                    for invalid in coverage['invalid_ranges'][:3]:  # Show first 3
                        print(f"      Lines {invalid['line_start']}-{invalid['line_end']}: {invalid['error']}")
                if coverage['overlapping_ranges']:
                    print(f"    ⚠️  Overlapping ranges: {len(coverage['overlapping_ranges'])}")
                if coverage['missing_lines']:
                    missing_list = sorted(list(coverage['missing_lines']))[:10]  # Show first 10
                    print(f"    ⚠️  Missing lines: {len(coverage['missing_lines'])} (e.g., {missing_list})")
    else:
        print("✅ All line ranges are valid and cover all lines!")
    
    # Extract all line range tags from all pages
    line_range_entries = []
    skipped_invalid = 0
    
    for page in pages:
        line_tags = page.get('line_tags', [])
        if not line_tags:
            continue
        
        book_name = page.get('book_name', page.get('book_id', ''))
        page_num = page.get('page_number')
        chapter = page.get('chapter')
        
        for tag in line_tags:
            line_start = tag.get('line_start')
            line_end = tag.get('line_end')
            
            if not line_start or not line_end:
                skipped_invalid += 1
                continue
            
            # Validate range
            is_valid, error_msg = validate_line_range(page, line_start, line_end)
            if not is_valid:
                skipped_invalid += 1
                continue
            
            # Extract text for this line range
            text = extract_text_from_line_range(page, line_start, line_end)
            
            if not text.strip():
                continue
            
            # Create entry for this line range
            entry = {
                'book_name': book_name,
                'book_id': page.get('book_id'),
                'page_number': page_num,
                'chapter': chapter,
                'line_start': line_start,
                'line_end': line_end,
                'text': text,
                'year': tag.get('year'),
                'month': tag.get('month') or 'unknown',
                'location': tag.get('location') or 'unknown',
                'locations': tag.get('locations', []),
                'characters': tag.get('characters', []),
                'confidence': tag.get('confidence', 'medium')
            }
            
            line_range_entries.append(entry)
    
    if skipped_invalid > 0:
        print(f"\n⚠️  Skipped {skipped_invalid} invalid line range tags")
    
    print(f"✅ Extracted {len(line_range_entries)} valid line range entries from pages")
    
    # Group line ranges by year, then by month, then by location
    grouped_entries = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for entry in line_range_entries:
        year = entry.get('year')
        month = entry.get('month') or 'unknown'
        location = entry.get('location') or 'unknown'
        
        if not year:
            year = 9999  # Unknown year goes to end
        
        grouped_entries[year][month][location].append(entry)
    
    # Create merged text
    merged_text_parts = []
    merged_structure = []
    
    # Sort by year, month, location
    for year in sorted([y for y in grouped_entries.keys() if isinstance(y, int) and y != 9999]):
        year_entries = grouped_entries[year]
        
        # Add year header
        merged_text_parts.append(f"\n\n{'='*60}\nשנה: {year}\n{'='*60}\n")
        
        # Sort months (if available)
        months_order = ['ינואר', 'פברואר', 'מרץ', 'מרס', 'אפריל', 'מאי', 'יוני', 
                        'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר', 'unknown']
        
        for month in sorted(year_entries.keys(), key=lambda m: months_order.index(m) if m in months_order else 999):
            month_entries = year_entries[month]
            
            # Add month header if not unknown
            if month != 'unknown':
                merged_text_parts.append(f"\n--- חודש: {month} ---\n")
            
            # Sort by location
            for location in sorted(month_entries.keys()):
                location_entries = month_entries[location]
                
                # Add location header if not unknown
                if location != 'unknown':
                    merged_text_parts.append(f"\n### מיקום: {location} ###\n")
                
                # Sort entries by page number and line_start within same location
                location_entries.sort(key=lambda e: (e.get('page_number', 0), e.get('line_start', 0)))
                
                # Add line range entries
                for entry in location_entries:
                    book_name = entry.get('book_name', entry.get('book_id', ''))
                    page_num = entry.get('page_number')
                    line_start = entry.get('line_start')
                    line_end = entry.get('line_end')
                    chapter = entry.get('chapter')
                    text = entry.get('text', '')
                    
                    # Add book/chapter header with line numbers
                    header = f"\n[מ{book_name}"
                    if chapter:
                        header += f" - {chapter}"
                    header += f", עמוד {page_num}"
                    if line_start == line_end:
                        header += f", שורה {line_start}"
                    else:
                        header += f", שורות {line_start}-{line_end}"
                    
                    # Add AI tags if available
                    tags = []
                    if entry.get('year'):
                        tags.append(f"שנה: {entry['year']}")
                    if entry.get('month') and entry.get('month') != 'unknown':
                        tags.append(f"חודש: {entry['month']}")
                    if entry.get('location') and entry.get('location') != 'unknown':
                        tags.append(f"מיקום: {entry['location']}")
                    
                    if tags:
                        header += f" | {', '.join(tags)}"
                    header += "]\n"
                    
                    merged_text_parts.append(header)
                    merged_text_parts.append(text)
                    merged_text_parts.append("\n")
                    
                    # Add to structure
                    merged_structure.append({
                        'year': year,
                        'month': month if month != 'unknown' else None,
                        'location': location if location != 'unknown' else None,
                        'book': book_name,
                        'chapter': chapter,
                        'page': page_num,
                        'line_start': line_start,
                        'line_end': line_end,
                        'text_length': len(text),
                        'ai_confidence': entry.get('confidence')
                    })
    
    # Handle unknown year entries
    if 9999 in grouped_entries:
        merged_text_parts.append(f"\n\n{'='*60}\nשנה לא ידועה\n{'='*60}\n")
        for month in grouped_entries[9999].keys():
            for location in grouped_entries[9999][month].keys():
                entries = grouped_entries[9999][month][location]
                entries.sort(key=lambda e: (e.get('page_number', 0), e.get('line_start', 0)))
                for entry in entries:
                    book_name = entry.get('book_name', entry.get('book_id', ''))
                    page_num = entry.get('page_number')
                    line_start = entry.get('line_start')
                    line_end = entry.get('line_end')
                    chapter = entry.get('chapter')
                    text = entry.get('text', '')
                    
                    header = f"\n[מ{book_name}"
                    if chapter:
                        header += f" - {chapter}"
                    header += f", עמוד {page_num}"
                    if line_start == line_end:
                        header += f", שורה {line_start}"
                    else:
                        header += f", שורות {line_start}-{line_end}"
                    header += "]\n"
                    
                    merged_text_parts.append(header)
                    merged_text_parts.append(text)
                    merged_text_parts.append("\n")
    
    # Combine all text
    merged_text = ''.join(merged_text_parts)
    
    return merged_text, merged_structure

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load AI-tagged pages
    print("Loading AI-tagged pages...")
    tagged_data = load_ai_tagged_pages()
    if not tagged_data:
        return
    
    # Load insertion points
    print("Loading insertion points...")
    insertion_data = load_insertion_points()
    
    if insertion_data:
        # Use new method: merge based on insertion points
        print("Merging books based on insertion points (preserving Yehuda's order)...")
        merged_text, merged_structure = merge_by_insertion_points(tagged_data, insertion_data)
    else:
        # Fallback: use old chronological method
        print("⚠️  No insertion points found. Using chronological merge (old method)...")
        print("   (Run 02b_determine_insertion_points.py to use the new insertion point method)")
        merged_text, merged_structure = merge_by_ai_tags(tagged_data)
    
    # Save merged text
    output_file = output_dir / 'merged_books_with_ai_tags.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_text)
    
    # Save structure JSON
    structure_file = output_dir / 'merged_books_with_ai_tags_structure.json'
    with open(structure_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_line_ranges': len(merged_structure),
                'books': ['sadot_rishonim', 'beit_markovski'],
                'time_period': '1900-1921',
                'method': 'ai_tagged_merge',
                'tagging_granularity': 'line_ranges'
            },
            'structure': merged_structure
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Merged {len(merged_structure)} line ranges based on AI tags")
    print(f"✅ Saved merged text to: {output_file}")
    print(f"✅ Saved structure to: {structure_file}")
    
    # Print detailed summary
    print("\n📊 Summary:")
    print(f"  Total line ranges: {len(merged_structure)}")
    
    # Count by year
    year_counts = {}
    for item in merged_structure:
        year = item.get('year')
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    
    print(f"\n  Line ranges by year:")
    for year in sorted([y for y in year_counts.keys() if isinstance(y, int) and y != 9999]):
        print(f"    {year}: {year_counts[year]} line ranges")
    
    if 9999 in year_counts:
        print(f"    Unknown: {year_counts[9999]} line ranges")
    
    # Count by location
    location_counts = {}
    for item in merged_structure:
        loc = item.get('location')
        if loc:
            location_counts[loc] = location_counts.get(loc, 0) + 1
    
    print(f"\n  Line ranges by location (top 10):")
    for loc, count in sorted(location_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {loc}: {count} line ranges")
    
    # Count by confidence
    confidence_counts = {}
    for item in merged_structure:
        conf = item.get('ai_confidence', 'unknown')
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
    
    print(f"\n  Line ranges by confidence:")
    for conf, count in sorted(confidence_counts.items()):
        print(f"    {conf}: {count} line ranges")
    
    # Calculate total text length
    total_text_length = sum(item.get('text_length', 0) for item in merged_structure)
    print(f"\n  Total text length: {total_text_length:,} characters (~{total_text_length/1000:.1f}K)")
    
    print(f"\n📝 The merged text is ready to use as script!")

if __name__ == "__main__":
    main()
