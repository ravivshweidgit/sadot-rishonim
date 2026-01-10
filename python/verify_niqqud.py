"""
Verify Hebrew Niqqud - Compare niqqud files with their backups
Checks that only niqqud was added and no letters were changed
"""

import os
import sys
from pathlib import Path
import unicodedata

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def remove_niqqud(text):
    """
    Remove all Hebrew niqqud (diacritics) from text, keeping only base letters
    """
    # Remove all combining diacritical marks (niqqud)
    normalized = unicodedata.normalize('NFD', text)
    # Filter out combining characters (niqqud marks)
    without_niqqud = ''.join(char for char in normalized 
                            if unicodedata.category(char) != 'Mn')
    return without_niqqud

def compare_texts(original, niqqud_text):
    """
    Compare original text with niqqud text to ensure only niqqud was added
    Returns (match, differences) tuple
    """
    original_no_niqqud = remove_niqqud(original)
    niqqud_no_niqqud = remove_niqqud(niqqud_text)
    
    if original_no_niqqud == niqqud_no_niqqud:
        return True, []
    
    # Find differences
    differences = []
    orig_lines = original_no_niqqud.split('\n')
    niqqud_lines = niqqud_no_niqqud.split('\n')
    
    max_lines = max(len(orig_lines), len(niqqud_lines))
    for i in range(max_lines):
        orig_line = orig_lines[i] if i < len(orig_lines) else ""
        niqqud_line = niqqud_lines[i] if i < len(niqqud_lines) else ""
        if orig_line != niqqud_line:
            # Find character-level differences
            orig_chars = list(orig_line)
            niqqud_chars = list(niqqud_line)
            max_chars = max(len(orig_chars), len(niqqud_chars))
            
            diff_start = None
            diff_end = None
            for j in range(max_chars):
                orig_char = orig_chars[j] if j < len(orig_chars) else ""
                niqqud_char = niqqud_chars[j] if j < len(niqqud_chars) else ""
                if orig_char != niqqud_char:
                    if diff_start is None:
                        diff_start = j
                    diff_end = j
            
            differences.append({
                'line': i + 1,
                'original': orig_line,
                'niqqud': niqqud_line,
                'diff_start': diff_start,
                'diff_end': diff_end,
                'original_context': orig_line[max(0, diff_start-10):min(len(orig_line), diff_end+11)] if diff_start is not None else orig_line[:50],
                'niqqud_context': niqqud_line[max(0, diff_start-10):min(len(niqqud_line), diff_end+11)] if diff_start is not None else niqqud_line[:50]
            })
    
    return False, differences

def verify_file(file_path, backup_path):
    """
    Verify a single file against its backup
    """
    try:
        # Read both files
        with open(file_path, 'r', encoding='utf-8') as f:
            niqqud_content = f.read()
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Compare
        match, differences = compare_texts(original_content, niqqud_content)
        
        return match, differences
        
    except FileNotFoundError:
        return None, f"Backup file not found: {backup_path.name}"
    except Exception as e:
        return None, f"Error: {e}"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify Hebrew niqqud files against backups')
    parser.add_argument('--book', '-b', type=str, default='beit_markovski',
                       help='Book ID (beit_markovski or sadot_rishonim)')
    parser.add_argument('--file', '-f', type=str, default=None,
                       help='Verify specific file only (optional)')
    
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    text_dir = project_root / "books" / args.book / "text"
    
    if not text_dir.exists():
        print(f"Error: Text directory not found: {text_dir}")
        return
    
    print(f"Verifying book: {args.book}")
    print(f"Text directory: {text_dir}")
    print()
    
    # Find all files with backups
    if args.file:
        # Verify specific file
        file_path = text_dir / args.file
        backup_path = text_dir / f"{args.file}.bak"
        
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return
        
        print(f"Verifying {file_path.name}...")
        match, result = verify_file(file_path, backup_path)
        
        if match is None:
            print(f"  [ERROR] {result}")
        elif match:
            print(f"  [OK] All letters match - only niqqud was added")
        else:
            print(f"  [WARNING] Differences found:")
            for diff in result:
                print(f"    Line {diff['line']}:")
                print(f"      Original: ...{diff['original_context']}...")
                print(f"      Niqqud:   ...{diff['niqqud_context']}...")
    else:
        # Verify all files
        txt_files = sorted(text_dir.glob("*.txt"))
        # Get backup files - remove .bak extension to get base name
        bak_files = {}
        for bak_file in text_dir.glob("*.txt.bak"):
            base_name = bak_file.name.replace('.txt.bak', '')
            bak_files[base_name] = bak_file
        
        if not txt_files:
            print("No text files found")
            return
        
        print(f"Found {len(txt_files)} text files")
        print(f"Found {len(bak_files)} backup files")
        print()
        
        verified = 0
        errors = 0
        warnings = 0
        
        for txt_file in txt_files:
            # Skip table of contents
            if txt_file.name in ['004.txt', '135.txt']:
                continue
            
            # Skip if no backup
            base_name = txt_file.stem
            if base_name not in bak_files:
                continue
            
            backup_file = bak_files[base_name]
            
            match, result = verify_file(txt_file, backup_file)
            
            if match is None:
                print(f"[ERROR] {txt_file.name}: {result}")
                errors += 1
            elif match:
                verified += 1
            else:
                print(f"[WARNING] {txt_file.name}: Differences found")
                warnings += 1
                for diff in result[:2]:  # Show first 2 differences per file
                    print(f"  Line {diff['line']}:")
                    print(f"    Original: ...{diff['original_context']}...")
                    print(f"    Niqqud:   ...{diff['niqqud_context']}...")
                if len(result) > 2:
                    print(f"    ... and {len(result) - 2} more differences")
                print()
        
        print()
        print(f"Verification complete!")
        print(f"  ✓ Verified (OK): {verified}")
        print(f"  ⚠ Warnings (differences): {warnings}")
        print(f"  ✗ Errors: {errors}")

if __name__ == "__main__":
    main()

