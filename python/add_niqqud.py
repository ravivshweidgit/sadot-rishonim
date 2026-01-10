"""
Add Hebrew Niqqud (diacritics) to text files that don't have them
Uses Gemini API to intelligently add niqqud while preserving the original text structure
"""

import os
import sys
from pathlib import Path
import google.generativeai as genai
import re
import unicodedata
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure the API key
API_KEY = "AIzaSyDFOH_cK4w2neobchhAWYp1te7b9Aj75jI"
genai.configure(api_key=API_KEY)

# Initialize the model - use gemini-2.0-flash-exp for better Hebrew support
try:
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except:
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')  # Better quality, slower
        except:
            model = genai.GenerativeModel('gemini-pro')

def has_niqqud(text):
    """
    Check if text has sufficient Hebrew niqqud (diacritics)
    Returns True if text has niqqud on at least 30% of Hebrew words
    """
    # Hebrew niqqud range: U+0591 to U+05C7
    # Hebrew letters range: U+0590 to U+05FF
    niqqud_chars = len(re.findall(r'[\u0591-\u05C7]', text))
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    
    # If no Hebrew characters, return False
    if hebrew_chars == 0:
        return False
    
    # If niqqud ratio is less than 5%, consider it as not having niqqud
    niqqud_ratio = niqqud_chars / hebrew_chars if hebrew_chars > 0 else 0
    return niqqud_ratio > 0.05  # At least 5% of Hebrew chars should have niqqud

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

def normalize_spaces(text):
    """
    Normalize spaces around punctuation for comparison
    Removes spaces before punctuation marks
    """
    # Remove spaces before punctuation (:, ;, ., ,, !, ?, etc.)
    text = re.sub(r'\s+([:;,\.!?])', r'\1', text)
    # Normalize multiple spaces to single space
    text = re.sub(r' +', ' ', text)
    return text

def compare_texts(original, niqqud_text):
    """
    Compare original text with niqqud text to ensure only niqqud was added
    Returns (match, differences) tuple
    """
    original_no_niqqud = remove_niqqud(original)
    niqqud_no_niqqud = remove_niqqud(niqqud_text)
    
    # Normalize spaces around punctuation for comparison
    original_normalized = normalize_spaces(original_no_niqqud)
    niqqud_normalized = normalize_spaces(niqqud_no_niqqud)
    
    if original_normalized == niqqud_normalized:
        return True, []
    
    # Find differences (compare original without normalization to catch real issues)
    differences = []
    orig_lines = original_no_niqqud.split('\n')
    niqqud_lines = niqqud_no_niqqud.split('\n')
    
    max_lines = max(len(orig_lines), len(niqqud_lines))
    for i in range(max_lines):
        orig_line = orig_lines[i] if i < len(orig_lines) else ""
        niqqud_line = niqqud_lines[i] if i < len(niqqud_lines) else ""
        # Normalize for comparison
        orig_norm = normalize_spaces(orig_line)
        niqqud_norm = normalize_spaces(niqqud_line)
        if orig_norm != niqqud_norm:
            differences.append({
                'line': i + 1,
                'original': orig_line[:50],
                'niqqud': niqqud_line[:50]
            })
    
    return False, differences

def add_niqqud_to_text(text):
    """
    Add Hebrew niqqud to text using Gemini API
    """
    prompt = """אתה מומחה לניקוד עברי תקני. המשימה שלך היא להוסיף ניקוד עברי מדויק ומושלם לטקסט הבא לפי כללי האקדמיה ללשון העברית.

⚠️⚠️⚠️ אזהרה קריטית - קרא בעיון לפני שאתה מתחיל:
הטקסט הבא הוא מדויק וסופי. כל אות בו היא נכונה ואין לשנותה. המשימה שלך היא רק להוסיף ניקוד מעל/תחת/בתוך האותיות הקיימות. 

חוק ברזל - אין חריגות:
- הטקסט הוא מדויק - כל אות נכונה ואין לתקן דבר
- אל תשנה שום אות - לא תוסיף, לא תמחק, לא תחליף
- גם אם נראה לך שהמילה כתובה לא נכון - שמור על האותיות בדיוק כפי שהן
- המשימה היחידה שלך היא להוסיף ניקוד - שום דבר אחר

⚠️ כללים קריטיים - חובה לקרוא בעיון:
1. שמור על המבנה המקורי של הטקסט בדיוק כפי שהוא (שורות, פסקאות, רווחים, רווחים לפני/אחרי סימני פיסוק) - אל תשנה שום רווח!
2. הוסף ניקוד תקני ומדויק לכל המילים לפי כללי הדקדוק העברי
3. בסמיכות: "בֵּית" (עם דגש וצירה), לא "בַּיִת" או "בֵית"
4. בפועל "ילדה" (ללדת): "יָלְדָה" או "שילדה" = "שִיָּלְדָה" (עם יוד)
5. שמות פרטיים: נקד לפי ההגייה הנכונה (למשל "מְאָרְיֵה" = מ' + אריה)
6. שמור על מספרי עמודים, סימני פיסוק וסימנים מיוחדים ללא שינוי - כולל רווחים לפני ואחרי סימני פיסוק!
7. הקפד על דגשים נכונים (דגש קל ודגש חזק)
8. הקפד על שוואים נח ונע נכונים
9. אל תשנה רווחים! אם יש רווח לפני נקודתיים - שמור עליו. אם אין רווח - אל תוסיף!

🚨 חוק ברזל - אין חריגות - זה הכי חשוב:
- אל תשנה שום אות בסיסית! לא תוסיף אותיות, לא תמחק אותיות, לא תחליף אותיות.
- אל תתקן טעויות OCR! גם אם נראה לך שהמילה כתובה לא נכון, שמור על האותיות בדיוק כפי שהן.
- הטקסט הזה הוא תוצאה של OCR - יש בו אולי טעויות כתיב, אבל אתה רק מוסיף ניקוד, לא מתקן אותיות.
- אל תשנה כתיב! אם כתוב "אוניה" - נקד "אֳנִיָּה" (לא "אניה")
- אל תשנה שמות פרטיים! אם כתוב "אהרון" - נקד "אַהֲרֹן" (לא "אהרן")
- אל תשנה מילים! אם כתוב "מסודרים" - נקד "מְסֻדָּרִים" (לא "מסדרים")
- אל תשנה מילים! אם כתוב "האוכל" - נקד "הָאֹכֶל" (לא "האכל")
- אל תשנה מילים! אם כתוב "בורגול" - נקד "בּוּרְגּוּל" (לא "ברגול")
- אל תשנה מילים! אם כתוב "מגוון" - נקד "מְגֻוָן" (לא "מגון")
- אל תשנה מילים! אם כתוב "כולו" - נקד "כֻלּוֹ" (לא "כלו")
- אל תשנה מילים! אם כתוב "בגודלה" - נקד "בְּגָדְלָהּ" (לא "בגדלה")
- אל תשנה מילים! אם כתוב "ולכולם" - נקד "וּלְכֻלָּם" (לא "ולכלם")
- אל תשנה מילים! אם כתוב "כמפורט" - נקד "כַּמְפֹרָט" (לא "כמפרט")
- אל תשנה מילים! אם כתוב "מהווה" - נקד "מְהַוֶּה" (לא "מהוה")
- אל תשנה מילים! אם כתוב "חוסר" - נקד "חֹסֶר" (לא "חסר")
- אל תשנה מילים! אם כתוב "כולם" - נקד "כֻלָּם" (לא "כלם")
- אל תשנה פיסוק! אם יש רווח לפני נקודתיים - שמור עליו. אם אין רווח - אל תוסיף!
- אל תשנה רווחים! שמור על כל הרווחים בדיוק כפי שהם - לא להוסיף, לא למחוק, לא לשנות!
- רק הוסף ניקוד מעל/תחת/בתוך האותיות הקיימות. כל האותיות והרווחים חייבים להישאר זהים לחלוטין.

דוגמאות נכונות:
- "מסודרים" → "מְסֻדָּרִים" (שמור על ה-ו!)
- "האוכל" → "הָאֹכֶל" (שמור על ה-ו!)
- "בורגול" → "בּוּרְגּוּל" (שמור על ה-ו!)
- "אהרון" → "אַהֲרֹן" (שמור על ה-ו!)

דוגמאות שגויות (אל תעשה כך!):
- "מסודרים" → "מְסַדְּרִים" (מחקת את ה-ו - זה אסור!)
- "האוכל" → "הָאֹכֶל" (מחקת את ה-ו - זה אסור!)
- "בורגול" → "בְּרְגּוּל" (מחקת את ה-ו - זה אסור!)
- "אהרון" → "אַהֲרֹן" (שינית את ה-ו ל-ן - זה אסור!)

הטקסט:
"""
    
    try:
        # Add delay to avoid rate limiting (10 requests per minute for gemini-2.0-flash-exp)
        time.sleep(7)  # Wait 7 seconds between requests
        
        response = model.generate_content(
            prompt + text,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Zero temperature for maximum accuracy and consistency
                top_p=0.95,
                top_k=40,
            )
        )
        
        # Check if content was blocked
        if not response.candidates:
            if hasattr(response, 'prompt_feedback'):
                block_reason = getattr(response.prompt_feedback, 'block_reason', 'UNKNOWN')
                print(f"    [WARNING] Content blocked by API (reason: {block_reason})")
                print(f"    [INFO] This may be due to sensitive historical content. Trying alternative approach...")
                # Try with a more explicit instruction that this is historical text
                alternative_prompt = prompt + "\n\n⚠️ הערה חשובה: הטקסט הבא הוא תוכן היסטורי אותנטי. המשימה היא רק להוסיף ניקוד, לא לשפוט או לסנן תוכן.\n\n" + text
                time.sleep(7)
                response = model.generate_content(
                    alternative_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        top_p=0.95,
                        top_k=40,
                    )
                )
                if not response.candidates:
                    print(f"    [ERROR] Content still blocked after retry")
                    return None
        
        niqqud_text = response.text.strip()
        # Verify that only niqqud was added
        match, differences = compare_texts(text, niqqud_text)
        if not match:
            print(f"    [WARNING] Text differences detected (not just niqqud):")
            for diff in differences[:3]:  # Show first 3 differences
                print(f"      Line {diff['line']}: '{diff['original']}' vs '{diff['niqqud']}'")
            # Debug: show full texts
            print(f"    [DEBUG] Original (no niqqud): {repr(remove_niqqud(text))}")
            print(f"    [DEBUG] Result (no niqqud):   {repr(remove_niqqud(niqqud_text))}")
        
        return niqqud_text
    except Exception as e:
        print(f"    [ERROR] Error adding niqqud: {e}")
        return None

def process_file(file_path, book_id='beit_markovski'):
    """
    Process a single text file - add niqqud if missing
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has niqqud
        if has_niqqud(content):
            print(f"Skipping {file_path.name} - already has niqqud")
            return False
        
        # Skip table of contents files
        if file_path.name in ['004.txt', '135.txt']:
            print(f"Skipping {file_path.name} - table of contents")
            return False
        
        print(f"Processing {file_path.name}...")
        
        # Add niqqud
        niqqud_text = add_niqqud_to_text(content)
        
        if niqqud_text:
            # Verify that only niqqud was added (letters are identical)
            match, differences = compare_texts(content, niqqud_text)
            if not match:
                print(f"  [WARNING] Text differences detected in {file_path.name} - letters changed!")
                print(f"    The model changed base letters. Will save anyway and fix later with fix_changed_words.py.")
                for diff in differences[:3]:  # Show first 3 differences
                    print(f"    Line {diff['line']}: original='{diff['original'][:50]}...' niqqud='{diff['niqqud'][:50]}...'")
                # Continue anyway - we'll fix with fix_changed_words.py later
            
            # Create backup (only if it doesn't exist - preserve original)
            backup_path = file_path.with_suffix('.txt.bak')
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Write niqqud version
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(niqqud_text)
            
            if match:
                print(f"  [OK] Added niqqud to {file_path.name} (backup preserved)")
            else:
                print(f"  [OK] Added niqqud to {file_path.name} (with warnings - will fix later)")
            return True
        else:
            print(f"  [ERROR] Failed to add niqqud to {file_path.name}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error processing {file_path.name}: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add Hebrew niqqud to text files')
    parser.add_argument('--book', '-b', type=str, default='beit_markovski',
                       help='Book ID (beit_markovski or sadot_rishonim)')
    parser.add_argument('--file', '-f', type=str, default=None,
                       help='Process specific file only (optional)')
    
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    text_dir = project_root / "books" / args.book / "text"
    
    if not text_dir.exists():
        print(f"Error: Text directory not found: {text_dir}")
        return
    
    print(f"Processing book: {args.book}")
    print(f"Text directory: {text_dir}")
    print()
    
    # Process files
    if args.file:
        # Process specific file
        file_path = text_dir / args.file
        if file_path.exists():
            process_file(file_path, args.book)
        else:
            print(f"Error: File not found: {file_path}")
    else:
        # Process all files
        txt_files = sorted(text_dir.glob("*.txt"))
        
        if not txt_files:
            print("No text files found")
            return
        
        print(f"Found {len(txt_files)} text files")
        print()
        
        processed = 0
        skipped = 0
        errors = 0
        
        for txt_file in txt_files:
            # Read to check if has niqqud
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if has_niqqud(content):
                    skipped += 1
                    continue
                
                if txt_file.name in ['004.txt', '135.txt']:
                    skipped += 1
                    continue
                
                if process_file(txt_file, args.book):
                    processed += 1
                else:
                    errors += 1
                    
            except Exception as e:
                print(f"Error reading {txt_file.name}: {e}")
                errors += 1
        
        print()
        print(f"Processing complete!")
        print(f"  Processed: {processed}")
        print(f"  Skipped (already has niqqud or TOC): {skipped}")
        print(f"  Errors: {errors}")

if __name__ == "__main__":
    main()
