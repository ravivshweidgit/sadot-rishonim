"""
Fix niqqud errors by restoring changed words from backup and re-adding niqqud only to those words
"""

import os
import sys
from pathlib import Path
import unicodedata
import re

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def remove_niqqud(text):
    """
    Remove all Hebrew niqqud (diacritics) from text, keeping only base letters
    """
    normalized = unicodedata.normalize('NFD', text)
    without_niqqud = ''.join(char for char in normalized 
                            if unicodedata.category(char) != 'Mn')
    return without_niqqud

def find_word_differences(original, niqqud_text):
    """
    Find words that changed between original and niqqud text
    Returns list of (word_original, word_niqqud, position) tuples
    """
    orig_no_niqqud = remove_niqqud(niqqud_text)
    
    if original == orig_no_niqqud:
        return []
    
    # Split into words (Hebrew words + punctuation)
    # Hebrew word pattern: [א-ת]+ with optional niqqud
    orig_words = re.findall(r'[\u0590-\u05FF\s\S]+?', original)
    niqqud_words = re.findall(r'[\u0590-\u05FF\s\S]+?', orig_no_niqqud)
    
    differences = []
    orig_chars = list(original)
    niqqud_chars = list(orig_no_niqqud)
    
    # Simple character-by-character comparison to find changed sections
    i = 0
    j = 0
    while i < len(orig_chars) and j < len(niqqud_chars):
        if orig_chars[i] == niqqud_chars[j]:
            i += 1
            j += 1
        else:
            # Found a difference - find the word boundaries
            start_i = i
            start_j = j
            
            # Find word end in original
            while i < len(orig_chars) and orig_chars[i] not in ' \n\t.,;:!?':
                i += 1
            # Find word end in niqqud
            while j < len(niqqud_chars) and niqqud_chars[j] not in ' \n\t.,;:!?':
                j += 1
            
            orig_word = ''.join(orig_chars[start_i:i])
            niqqud_word = ''.join(niqqud_chars[start_j:j])
            
            if orig_word != niqqud_word:
                differences.append((orig_word, niqqud_word, start_i))
    
    return differences

def fix_file(file_path, book_id='beit_markovski'):
    """
    Fix a file by restoring changed words from backup
    """
    backup_path = file_path.with_suffix('.txt.bak')
    
    if not backup_path.exists():
        print(f"  [SKIP] No backup found for {file_path.name}")
        return False
    
    # Read both files
    with open(file_path, 'r', encoding='utf-8') as f:
        niqqud_content = f.read()
    
    with open(backup_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Remove niqqud from niqqud version for comparison
    niqqud_no_niqqud = remove_niqqud(niqqud_content)
    
    # If they match after removing niqqud, no changes needed
    if original_content == niqqud_no_niqqud:
        print(f"  [OK] {file_path.name} - no letter changes detected")
        return True
    
    # Find differences line by line
    orig_lines = original_content.split('\n')
    niqqud_lines = niqqud_content.split('\n')
    niqqud_no_niqqud_lines = niqqud_no_niqqud.split('\n')
    
    fixed_lines = []
    changes_count = 0
    
    max_lines = max(len(orig_lines), len(niqqud_lines))
    for line_idx in range(max_lines):
        orig_line = orig_lines[line_idx] if line_idx < len(orig_lines) else ""
        niqqud_line = niqqud_lines[line_idx] if line_idx < len(niqqud_lines) else ""
        niqqud_no_niqqud_line = niqqud_no_niqqud_lines[line_idx] if line_idx < len(niqqud_no_niqqud_lines) else ""
        
        if orig_line == niqqud_no_niqqud_line:
            # Line is OK, keep niqqud version
            fixed_lines.append(niqqud_line)
        else:
            # Line has changes - restore from original and we'll add niqqud later
            fixed_lines.append(orig_line)
            changes_count += 1
    
    # Write fixed content (without niqqud for changed lines)
    fixed_content = '\n'.join(fixed_lines)
    
    # Save fixed version
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    if changes_count > 0:
        print(f"  [FIXED] {file_path.name} - restored {changes_count} lines from backup")
        return True
    else:
        print(f"  [OK] {file_path.name} - no changes needed")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix niqqud errors by restoring changed words from backup')
    parser.add_argument('--book', '-b', type=str, default='beit_markovski',
                       help='Book ID (beit_markovski or sadot_rishonim)')
    parser.add_argument('--file', '-f', type=str, default=None,
                       help='Fix specific file only (optional)')
    
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    text_dir = project_root / "books" / args.book / "text"
    
    if not text_dir.exists():
        print(f"Error: Text directory not found: {text_dir}")
        return
    
    print(f"Fixing book: {args.book}")
    print(f"Text directory: {text_dir}")
    print()
    
    # Process files
    if args.file:
        # Process specific file
        file_path = text_dir / args.file
        if file_path.exists():
            fix_file(file_path, args.book)
        else:
            print(f"Error: File not found: {file_path}")
    else:
        # Process all files that have backups
        txt_files = sorted(text_dir.glob("*.txt"))
        
        if not txt_files:
            print("No text files found")
            return
        
        print(f"Found {len(txt_files)} text files")
        print()
        
        fixed = 0
        skipped = 0
        
        for txt_file in txt_files:
            # Skip backup files
            if txt_file.name.endswith('.bak'):
                continue
            
            # Skip if no backup exists
            backup_path = txt_file.with_suffix('.txt.bak')
            if not backup_path.exists():
                skipped += 1
                continue
            
            if fix_file(txt_file, args.book):
                fixed += 1
        
        print()
        print(f"Fixing complete!")
        print(f"  Fixed: {fixed}")
        print(f"  Skipped (no backup): {skipped}")

if __name__ == "__main__":
    main()

