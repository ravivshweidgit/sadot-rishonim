"""
Fix changed words in niqqud files by restoring from backup and re-adding niqqud at word level
"""

import os
import sys
from pathlib import Path
import unicodedata
import re
import google.generativeai as genai
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure the API key
API_KEY = "AIzaSyDFOH_cK4w2neobchhAWYp1te7b9Aj75jI"
genai.configure(api_key=API_KEY)

# Initialize the model
try:
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        model = genai.GenerativeModel('gemini-pro')

def remove_niqqud(text):
    """
    Remove all Hebrew niqqud (diacritics) from text, keeping only base letters
    """
    normalized = unicodedata.normalize('NFD', text)
    without_niqqud = ''.join(char for char in normalized 
                            if unicodedata.category(char) != 'Mn')
    return without_niqqud

def add_niqqud_to_word(word):
    """
    Add niqqud to a single word using Gemini API
    """
    prompt = """אתה מומחה לניקוד עברי תקני. הוסף ניקוד עברי מדויק למילה הבאה.

⚠️⚠️⚠️ חוק ברזל:
- אל תשנה שום אות! רק הוסף ניקוד מעל/תחת/בתוך האותיות הקיימות.
- המילה היא מדויקת - כל אות נכונה ואין לתקן דבר.
- רק הוסף ניקוד - שום דבר אחר.

המילה:
"""
    
    try:
        # Add delay to avoid rate limiting
        time.sleep(7)  # Wait 7 seconds between requests
        
        response = model.generate_content(
            prompt + word,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                top_p=0.95,
                top_k=40,
            )
        )
        
        niqqud_word = response.text.strip()
        
        # Verify that only niqqud was added
        if remove_niqqud(niqqud_word) == word:
            return niqqud_word
        else:
            print(f"      [WARNING] Word changed: '{word}' -> '{remove_niqqud(niqqud_word)}'")
            return word  # Return original if changed
        
    except Exception as e:
        print(f"      [ERROR] Error adding niqqud to word '{word}': {e}")
        return word

def find_changed_words_in_line(orig_line, niqqud_line):
    """
    Find words that changed between original and niqqud lines
    Returns list of (word, start_pos, end_pos) tuples for changed words
    """
    orig_no_niqqud = remove_niqqud(niqqud_line)
    
    if orig_line == orig_no_niqqud:
        return []
    
    # Find word boundaries and compare
    changed_words = []
    
    # Split into words (keeping punctuation)
    orig_words = re.finditer(r'\S+', orig_line)
    niqqud_words = re.finditer(r'\S+', orig_no_niqqud)
    
    orig_word_list = list(orig_words)
    niqqud_word_list = list(niqqud_words)
    
    # Compare word by word
    for i in range(min(len(orig_word_list), len(niqqud_word_list))):
        orig_match = orig_word_list[i]
        niqqud_match = niqqud_word_list[i]
        
        orig_word = orig_match.group()
        niqqud_word = niqqud_match.group()
        
        if orig_word != niqqud_word:
            changed_words.append((orig_word, orig_match.start(), orig_match.end()))
    
    return changed_words

def fix_file(file_path, book_id='beit_markovski'):
    """
    Fix a file by restoring changed words from backup and re-adding niqqud to those words only
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
    words_fixed = 0
    
    max_lines = max(len(orig_lines), len(niqqud_lines))
    for line_idx in range(max_lines):
        orig_line = orig_lines[line_idx] if line_idx < len(orig_lines) else ""
        niqqud_line = niqqud_lines[line_idx] if line_idx < len(niqqud_lines) else ""
        niqqud_no_niqqud_line = niqqud_no_niqqud_lines[line_idx] if line_idx < len(niqqud_no_niqqud_lines) else ""
        
        if orig_line == niqqud_no_niqqud_line:
            # Line is OK, keep niqqud version
            fixed_lines.append(niqqud_line)
        else:
            # Line has changes - find changed words and fix them
            changed_words = find_changed_words_in_line(orig_line, niqqud_line)
            
            if changed_words:
                # Replace changed words with niqqud versions
                fixed_line = orig_line
                # Process from end to start to preserve positions
                for word, start, end in reversed(changed_words):
                    # Add niqqud to the word from backup
                    niqqud_word = add_niqqud_to_word(word)
                    fixed_line = fixed_line[:start] + niqqud_word + fixed_line[end:]
                    words_fixed += 1
                
                fixed_lines.append(fixed_line)
            else:
                # Keep original line (will be processed by add_niqqud later)
                fixed_lines.append(orig_line)
    
    # Write fixed content
    fixed_content = '\n'.join(fixed_lines)
    
    # Save fixed version
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    if words_fixed > 0:
        print(f"  [FIXED] {file_path.name} - fixed {words_fixed} words")
        return True
    else:
        print(f"  [OK] {file_path.name} - no changes needed")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix changed words in niqqud files')
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
    
    print(f"Fixing changed words in book: {args.book}")
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
        # Process all files that have backups and niqqud
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

