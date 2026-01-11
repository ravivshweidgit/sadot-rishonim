"""Test niqqud addition on a single file"""
import sys
import os
from pathlib import Path
sys.path.insert(0, 'python')
import google.generativeai as genai
import unicodedata

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure the API key - read from local file (not committed to git)

def load_api_key():
    """Load API key from api_key.txt file"""
    script_dir = Path(__file__).parent
    api_key_file = script_dir / "api_key.txt"
    
    if api_key_file.exists():
        with open(api_key_file, 'r', encoding='utf-8') as f:
            # Read the file and get the first non-empty, non-comment line
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
    
    # Fallback: check environment variable
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    # If no key found, raise an error with helpful message
    raise ValueError(
        f"API key not found!\n"
        f"Please create {api_key_file} and add your Google Gemini API key.\n"
        f"Get your API key from: https://aistudio.google.com/apikey"
    )

API_KEY = load_api_key()
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
    """Remove all Hebrew niqqud (diacritics) from text"""
    normalized = unicodedata.normalize('NFD', text)
    without_niqqud = ''.join(char for char in normalized 
                            if unicodedata.category(char) != 'Mn')
    return without_niqqud

# Read the file
with open('books/beit_markovski/text/000.txt', 'r', encoding='utf-8') as f:
    original_text = f.read()

print("Original text:")
print(repr(original_text))
print("\nDisplay:")
print(original_text)
print("\n" + "="*50 + "\n")

# Try to add niqqud
prompt = """אתה מומחה לניקוד עברי תקני. הוסף ניקוד עברי מדויק לטקסט הבא.

⚠️⚠️⚠️ חוק ברזל:
- אל תשנה שום אות! רק הוסף ניקוד מעל/תחת/בתוך האותיות הקיימות.
- הטקסט הוא מדויק - כל אות נכונה ואין לתקן דבר.
- רק הוסף ניקוד - שום דבר אחר.

הטקסט:
"""

try:
    response = model.generate_content(
        prompt + original_text,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
            top_p=0.95,
            top_k=40,
        )
    )
    
    result_text = response.text.strip()
    
    print("Result text:")
    print(repr(result_text))
    print("\nDisplay:")
    print(result_text)
    print("\n" + "="*50 + "\n")
    
    # Compare
    original_no_niqqud = remove_niqqud(original_text)
    result_no_niqqud = remove_niqqud(result_text)
    
    print("Original (no niqqud):")
    print(repr(original_no_niqqud))
    print("\nResult (no niqqud):")
    print(repr(result_no_niqqud))
    print("\nMatch:", original_no_niqqud == result_no_niqqud)
    
    if original_no_niqqud != result_no_niqqud:
        print("\nDifferences found!")
        # Show character by character
        for i, (orig_char, result_char) in enumerate(zip(original_no_niqqud, result_no_niqqud)):
            if orig_char != result_char:
                print(f"Position {i}: '{orig_char}' (U+{ord(orig_char):04X}) != '{result_char}' (U+{ord(result_char):04X})")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
