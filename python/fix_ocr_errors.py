"""
OCR Error Correction Script - Document and Line Specific
Fixes OCR errors based on specific file, line number, and context
"""

from pathlib import Path
import json

# Document-specific corrections
# Format: {filename: {line_number: (old_text, new_text)}}
CORRECTIONS = {
    "010.txt": {
        11: ("קיבל אנא,", "קיבל אבא,"),
        18: ("יעברנו", "עברנו"),
        20: ("זויים", "זרים"),
        23: ("האיכויס", "האיכרים"),
        26: ("בית נופר", "בית ספר"),
        31: ("הייליה", "העלייה"),
        32: ("ינפתח", "נפתח"),
        5: ("קוסטינה'", "קוסטינה$^1$"),
        21: ('שץ"', "שץ$^2$"),
        22: ("השניה", "השנייה"),
    },
    "009.txt": {
        22: ('ישראלי -', 'ישראל" -'),
    },
}

def apply_corrections(file_path, corrections_dict):
    """Apply document-specific corrections to a file"""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Track changes
        changes_made = []
        
        # Apply corrections line by line
        for line_num, (old_text, new_text) in corrections_dict.items():
            # Line numbers are 1-based, list is 0-based
            idx = line_num - 1
            if 0 <= idx < len(lines):
                if old_text in lines[idx]:
                    lines[idx] = lines[idx].replace(old_text, new_text)
                    changes_made.append(f"Line {line_num}: {old_text} → {new_text}")
        
        # Only write if there were changes
        if changes_made:
            # Create backup
            backup_path = file_path.with_suffix('.txt.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Write corrected text (overwrite original)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True, changes_made, backup_path
        else:
            return False, [], None
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, [], None

def add_correction(filename, line_number, old_text, new_text):
    """Add a new correction to the corrections dictionary"""
    if filename not in CORRECTIONS:
        CORRECTIONS[filename] = {}
    CORRECTIONS[filename][line_number] = (old_text, new_text)

def save_corrections_to_file(corrections_file="python/ocr_corrections.json"):
    """Save corrections to a JSON file for future reference"""
    script_dir = Path(__file__).parent
    corrections_path = script_dir / corrections_file if not Path(corrections_file).is_absolute() else Path(corrections_file)
    
    with open(corrections_path, 'w', encoding='utf-8') as f:
        json.dump(CORRECTIONS, f, ensure_ascii=False, indent=2)
    
    print(f"Corrections saved to {corrections_path}")

def load_corrections_from_file(corrections_file="python/ocr_corrections.json"):
    """Load corrections from a JSON file"""
    script_dir = Path(__file__).parent
    corrections_path = script_dir / corrections_file if not Path(corrections_file).is_absolute() else Path(corrections_file)
    
    if corrections_path.exists():
        with open(corrections_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    """Main function to process text files"""
    import sys
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Get book ID from command line argument or default to sadot_rishonim
    book_id = 'sadot_rishonim'
    if len(sys.argv) > 1 and sys.argv[1] not in ['--book', '-b']:
        # First arg might be book ID or file name - check if it's a book ID
        potential_book_id = sys.argv[1]
        book_dir = project_root / "books" / potential_book_id
        if book_dir.exists() and (book_dir / "text").exists():
            book_id = potential_book_id
            sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove book_id from args
    
    # Check for --book or -b flag
    if '--book' in sys.argv or '-b' in sys.argv:
        flag_idx = sys.argv.index('--book') if '--book' in sys.argv else sys.argv.index('-b')
        if flag_idx + 1 < len(sys.argv):
            book_id = sys.argv[flag_idx + 1]
            # Remove book flag and value from args
            sys.argv = [arg for i, arg in enumerate(sys.argv) if i not in [flag_idx, flag_idx + 1]]
    
    text_dir = project_root / "books" / book_id / "text"
    
    if not text_dir.exists():
        print(f"Error: {text_dir} directory not found!")
        print(f"Available books: {', '.join([d.name for d in (project_root / 'books').iterdir() if d.is_dir()])}")
        return
    
    print(f"Processing book: {book_id}")
    print(f"Text directory: {text_dir}\n")
    
    # Check for command-line argument
    if len(sys.argv) > 1:
        # Process specific file
        txt_name = sys.argv[1]
        if not txt_name.endswith('.txt'):
            txt_name = txt_name + '.txt'
        
        file_path = text_dir / txt_name
        
        if not file_path.exists():
            print(f"Error: File {txt_name} not found in {text_dir}")
            return
        
        # Get corrections for this file
        corrections = CORRECTIONS.get(txt_name, {})
        
        if not corrections:
            print(f"No corrections defined for {txt_name}")
            return
        
        print(f"Processing {txt_name}...")
        changed, changes, backup = apply_corrections(file_path, corrections)
        
        if changed:
            print(f"  ✓ Fixed {len(changes)} error(s), backup saved to {backup.name}")
            for change in changes:
                print(f"    - {change}")
        else:
            print(f"  - No matching errors found (corrections may have already been applied)")
    
    else:
        # Process all files with corrections
        print(f"Processing files with corrections defined...\n")
        
        fixed_count = 0
        total_changes = 0
        
        for txt_name, corrections in CORRECTIONS.items():
            file_path = text_dir / txt_name
            
            if not file_path.exists():
                print(f"Skipping {txt_name} - file not found")
                continue
            
            print(f"Processing {txt_name}...", end=' ')
            changed, changes, backup = apply_corrections(file_path, corrections)
            
            if changed:
                print(f"✓ Fixed {len(changes)} error(s)")
                for change in changes:
                    print(f"    - {change}")
                fixed_count += 1
                total_changes += len(changes)
            else:
                print("No matching errors found")
        
        print(f"\nDone! Fixed {total_changes} error(s) in {fixed_count} file(s).")

if __name__ == "__main__":
    main()
