import os
import sys
import re
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_books_config(project_root):
    """Load books configuration to get chapter information"""
    config_path = project_root / "books-config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('books', {}).get('sadot_rishonim', {}).get('chapters', [])
        except Exception as e:
            print(f"Warning: Could not load books config: {e}")
    return []

def get_chapter_for_page(chapters, page_num):
    """Find which chapter a page belongs to"""
    page_num_int = int(page_num) if page_num.isdigit() else 0
    # Find the chapter with the highest page number <= current page
    chapter = None
    for ch in chapters:
        if ch['page'] <= page_num_int:
            chapter = ch
        else:
            break
    return chapter

def fix_page_header(file_path, chapters=None):
    """
    Fix the first line of a text file to match the standard format: "מספר • כותרת"
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        first_line = lines[0].strip()
        page_num = file_path.stem
        
        # Check if already in correct format: "מספר • כותרת" (without duplicate numbers/symbols)
        match = re.match(r'^(\d+)\s+•\s+(.+)', first_line)
        if match:
            page_num_int = int(page_num) if page_num.isdigit() else 0
            title = match.group(2).strip()
            
            # For pages 63+, check odd/even pattern
            if page_num_int >= 63:
                expected_title = get_expected_title(page_num_int, chapters)
                if title == expected_title:
                    return False  # Already correct
                else:
                    # Wrong title, fix it
                    return create_header(lines, page_num, expected_title, chapters=chapters)
            
            # Check if title has duplicate numbers or symbols that need cleaning
            if re.search(r'\d+\s*[•●]', title) or '●' in title:
                # Needs cleaning - continue to fix
                pass
            elif not title.startswith(match.group(1)) and len(title) > 2:
                # Already correct format
                return False
        
        # Extract title from various formats
        title = None
        
        # Pattern 1: "כותרת • מספר" -> "מספר • כותרת"
        match = re.match(r'^(.+?)\s+[•●]\s*(\d+)$', first_line)
        if match:
            title = match.group(1).strip()
            return create_header(lines, page_num, title, chapters=chapters)
        
        # Pattern 2: "מספר" alone, title in next line
        if first_line.isdigit() and len(lines) > 1:
            title = lines[1].strip()
            if title and not title.isdigit():
                return create_header(lines, page_num, title, start_from=2, chapters=chapters)
        
        # Pattern 3: "כותרת" alone, number in next line
        if not first_line.isdigit() and len(lines) > 1:
            next_line = lines[1].strip()
            if next_line.isdigit():
                return create_header(lines, page_num, first_line, start_from=2, chapters=chapters)
        
        # Pattern 4: Starts with ``` (markdown code block)
        if first_line.startswith('```'):
            # Remove markdown code blocks and find title
            clean_lines = [l for l in lines if not l.strip().startswith('```')]
            if clean_lines:
                first_clean = clean_lines[0].strip()
                # Try to extract from "מספר • כותרת" or "כותרת • מספר"
                match = re.match(r'(\d+)\s+[•●]\s+(.+)$', first_clean)
                if match:
                    title = match.group(2).strip()
                    return create_header(clean_lines, page_num, title, start_from=1, chapters=chapters)
                match = re.match(r'(.+?)\s+[•●]\s*(\d+)$', first_clean)
                if match:
                    title = match.group(1).strip()
                    return create_header(clean_lines, page_num, title, start_from=1, chapters=chapters)
        
        # Pattern 5: Just number, try to find title in content
        if first_line == page_num or first_line.isdigit():
            # Look for common titles in the first few lines
            for i in range(1, min(5, len(lines))):
                line = lines[i].strip()
                if line and not line.isdigit() and len(line) > 2:
                    # Common titles from the book
                    if any(word in line for word in ['שדות ראשונים', 'מטולה', 'ראשית', 'הקדמה']):
                        title = line
                        return create_header(lines, page_num, title, start_from=i+1, chapters=chapters)
                    # Or just use first substantial line
                    if len(line) > 5:
                        title = line
                        return create_header(lines, page_num, title, start_from=i+1, chapters=chapters)
        
        # Pattern 6: OCR error - starts with prompt text
        if 'תמלל' in first_line or 'הקובץ המצורף' in first_line:
            # Skip to first real content line
            for i in range(1, min(10, len(lines))):
                line = lines[i].strip()
                if line and len(line) > 5 and not 'תמלל' in line:
                    # Try to extract page number and title
                    match = re.search(r'(\d+)', line)
                    if match:
                        # Look for title pattern
                        title_match = re.search(r'([א-ת\s]+)', line)
                        if title_match:
                            title = title_match.group(1).strip()
                            if len(title) > 2:
                                return create_header(lines, page_num, title, start_from=i+1, chapters=chapters)
        
        # Default: use page number with generic title
        if not title:
            page_num_int = int(page_num) if page_num.isdigit() else 0
            if page_num_int >= 63:
                title = get_expected_title(page_num_int, chapters)
            else:
                # Try to extract from first meaningful line
                for line in lines[:5]:
                    clean_line = line.strip()
                    if clean_line and len(clean_line) > 3 and not clean_line.isdigit():
                        # Check if it's a title-like line
                        if any(word in clean_line for word in ['שדות ראשונים', 'מטולה', 'ראשית']):
                            title = clean_line
                            break
                
                if not title:
                    title = "שדות ראשונים"  # Default title
        
        return create_header(lines, page_num, title, chapters=chapters)
        
    except Exception as e:
        print(f"  [ERROR] Error processing {file_path.name}: {e}")
        return False

def get_expected_title(page_num_int, chapters):
    """Get the expected title for a page based on odd/even pattern"""
    if page_num_int < 63:
        return "שדות ראשונים"  # Default for pages < 63
    
    # Find which chapter this page belongs to
    chapter = get_chapter_for_page(chapters or [], str(page_num_int))
    
    # Odd pages: chapter name, Even pages: "שדות ראשונים"
    if page_num_int % 2 == 1:  # Odd page
        if chapter:
            return chapter['name']
        else:
            return "שדות ראשונים"  # Fallback
    else:  # Even page
        return "שדות ראשונים"

def create_header(lines, page_num, title, start_from=1, chapters=None):
    """
    Create new content with proper header format: "מספר • כותרת"
    """
    page_num_int = int(page_num) if page_num.isdigit() else 0
    
    # For pages 63+, determine correct title based on odd/even
    if page_num_int >= 63:
        title = get_expected_title(page_num_int, chapters)
    else:
        # Clean title - remove duplicate page numbers and symbols
        title = title.strip()
        
        # Remove all bullet symbols (●) from title
        title = title.replace('●', '')
        
        # Remove leading/trailing symbols and whitespace
        title = re.sub(r'^[•\s]+', '', title)
        title = re.sub(r'[•\s]+$', '', title)
        
        # Remove duplicate page number if it appears anywhere in title
        title = re.sub(rf'{page_num}\s*[•●]?\s*', '', title)
        
        # Remove any number followed by bullet symbol (e.g., "26 •" or "53")
        title = re.sub(r'\d+\s*[•●]?\s*', '', title)
        
        # Remove trailing numbers (e.g., "מטולה 53" -> "מטולה")
        title = re.sub(r'\s+\d+\s*$', '', title)
        
        # Clean up common OCR errors
        title = title.replace('ר. ושונים', 'ראשונים')
        title = title.replace('שדות ר. ושונים', 'שדות ראשונים')
        title = title.replace('ר ושונים', 'ראשונים')
        
        # Remove extra whitespace
        title = ' '.join(title.split())
    
    # If title is empty or just numbers, use default
    if not title or title.isdigit() or len(title) < 2:
        page_num_int = int(page_num) if page_num.isdigit() else 0
        if page_num_int >= 63:
            title = get_expected_title(page_num_int, chapters)
        else:
            # Try to find title from content
            for line in lines[start_from:start_from+3]:
                clean_line = line.strip()
                if clean_line and len(clean_line) > 3:
                    if any(word in clean_line for word in ['שדות ראשונים', 'מטולה', 'ראשית', 'הקדמה']):
                        title = clean_line.split()[0] if ' ' in clean_line else clean_line
                        break
            
            if not title or title.isdigit():
                title = "שדות ראשונים"  # Default title
    
    # Remove empty lines at start
    while start_from < len(lines) and not lines[start_from].strip():
        start_from += 1
    
    # Create new header
    new_header = f"{page_num} • {title}\n"
    
    # Combine header with rest of content
    new_lines = [new_header, "\n"] + lines[start_from:]
    
    return new_lines

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Support both old structure (text/) and new structure (books/sadot_rishonim/text/)
    text_dir = project_root / "books" / "sadot_rishonim" / "text"
    if not text_dir.exists():
        text_dir = project_root / "text"
    
    if not text_dir.exists():
        print(f"Error: {text_dir} directory not found!")
        return
    
    # Load chapter information
    chapters = load_books_config(project_root)
    print(f"Loaded {len(chapters)} chapters from config\n")
    
    # Get all text files except 004.txt and not_in_use folder
    txt_files = sorted([f for f in text_dir.glob("*.txt") 
                       if f.name != "004.txt" and f.name != "not_in_use"])
    
    print(f"Found {len(txt_files)} text files to check\n")
    
    fixed_count = 0
    skipped_count = 0
    
    for txt_file in txt_files:
        print(f"Checking {txt_file.name}...")
        
        # Read first line to check format
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            # Check if already correct
            page_num = txt_file.stem
            page_num_int = int(page_num) if page_num.isdigit() else 0
            
            # For pages 63+, check if it matches expected title (odd/even pattern)
            if page_num_int >= 63:
                expected_title = get_expected_title(page_num_int, chapters)
                if re.match(rf'^{page_num}\s+•\s+{re.escape(expected_title)}', first_line):
                    print(f"  [SKIP] Already in correct format")
                    skipped_count += 1
                    continue
            else:
                # For pages 0-62, check if it matches the standard format
                if re.match(rf'^{page_num}\s+•\s+', first_line):
                    print(f"  [SKIP] Already in correct format")
                    skipped_count += 1
                    continue
            
            # Fix the header
            new_lines = fix_page_header(txt_file, chapters)
            
            if new_lines:
                # Write back
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"  [FIXED] Updated header to: {new_lines[0].strip()}")
                fixed_count += 1
            else:
                print(f"  [SKIP] Could not determine correct format")
                skipped_count += 1
                
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    print(f"\nProcessing complete!")
    print(f"Fixed: {fixed_count} files")
    print(f"Skipped: {skipped_count} files")
    
    # List missing files
    print(f"\nChecking for missing page numbers...")
    existing_nums = {int(f.stem) for f in txt_files}
    max_num = max(existing_nums) if existing_nums else 0
    missing = [i for i in range(max_num + 1) if i not in existing_nums and i != 4]
    
    if missing:
        print(f"Missing page numbers: {missing}")
    else:
        print("No missing page numbers found!")

if __name__ == "__main__":
    main()

