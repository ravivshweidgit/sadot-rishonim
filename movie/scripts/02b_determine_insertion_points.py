#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט שקובע insertion points לספר של רוחמה בספר של יהודה.
משתמש ב-API key הקיים ב-python/api_key.txt

הגישה:
1. קורא את התיוגים מ-02_tag_pages_with_gemini.py
2. AI קובע לכל קטע מהספר של רוחמה איפה הוא צריך להיכנס בספר של יהודה
3. שומר את ה-insertion points לקובץ JSON

AI קובע insertion points לפי:
- הקשר כרונולוגי (שנה, חודש)
- הקשר נרטיבי (אירועים, דמויות, מקומות)
- זרימת הסיפור

התוצאה: לכל קטע מהספר של רוחמה יש `insert_after_page` ו-`insert_after_line` בספר של יהודה.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed.")
    print("Install with: pip install google-generativeai")
    sys.exit(1)

def load_api_key():
    """Load API key from python/api_key.txt file"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    api_key_file = project_root / 'python' / 'api_key.txt'
    
    if api_key_file.exists():
        with open(api_key_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
    
    # Fallback: check environment variable
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    raise ValueError(
        f"API key not found!\n"
        f"Please create {api_key_file} and add your Google Gemini API key.\n"
        f"Get your API key from: https://aistudio.google.com/apikey"
    )

def load_tagged_pages():
    """Load pages that were tagged by 02_tag_pages_with_gemini.py"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    tagged_file = project_root / 'movie' / 'output' / 'scripts' / 'pages_tagged_by_ai.json'
    
    if not tagged_file.exists():
        print(f"Error: {tagged_file} not found.")
        print(f"Please run 02_tag_pages_with_gemini.py first to tag pages.")
        return None
    
    with open(tagged_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_text_from_line_range(page, line_start, line_end):
    """Extract text from a specific line range in a page"""
    lines = page.get('lines', [])
    text_lines = []
    
    for line in lines:
        line_num = line.get('line_number', 0)
        if line_start <= line_num <= line_end:
            text_lines.append(line.get('text', ''))
    
    return '\n'.join(text_lines)

def prepare_yehuda_context(tagged_data):
    """Prepare context for AI: Yehuda's book - just the text, no tags needed!"""
    pages = tagged_data.get('pages', [])
    
    # Get only Yehuda's pages
    yehuda_pages = [p for p in pages if p.get('book_id') == 'sadot_rishonim']
    yehuda_pages.sort(key=lambda p: p.get('page_number', 0))
    
    # Build simple context: just page number, chapter, and full text
    # AI can understand chronological context from reading the text itself!
    yehuda_context = []
    for page in yehuda_pages:
        page_num = page.get('page_number')
        chapter = page.get('chapter', '')
        full_text = page.get('full_text', '')
        
        page_summary = {
            'page_number': page_num,
            'chapter': chapter,
            'text': full_text[:500] + '...' if len(full_text) > 500 else full_text  # Preview for context
        }
        
        yehuda_context.append(page_summary)
    
    return yehuda_context, yehuda_pages

def get_ruchama_pages(tagged_data):
    """Get Ruchama's pages (without tags - they will be inserted)"""
    pages = tagged_data.get('pages', [])
    ruchama_pages = [p for p in pages if p.get('book_id') == 'beit_markovski']
    ruchama_pages.sort(key=lambda p: p.get('page_number', 0))
    return ruchama_pages

def determine_insertion_points_for_page(ruchama_page, yehuda_context):
    """Build prompt to determine insertion points for paragraphs in a Ruchama page
    
    AI will:
    1. Divide the Ruchama page into contextually coherent paragraphs
    2. Determine insertion point (page + line) in Yehuda's book for each paragraph
    """
    
    page_num = ruchama_page.get('page_number')
    chapter = ruchama_page.get('chapter', '')
    lines = ruchama_page.get('lines', [])
    
    # Build full text with line numbers for context
    lines_text = "\n".join([f"{line['line_number']:3d}: {line['text']}" for line in lines if not line['is_empty']])
    
    # Build prompt: show Yehuda's book (full text) and ask where to insert this Ruchama page
    # AI can understand chronological context from reading the text - no tags needed!
    prompt = f"""קח את שני הספרים הבאים על החיים במטולה בשנים 1900-1921:

**ספר של יהודה (שדות ראשונים) - הסדר המקורי נשמר:**
{json.dumps(yehuda_context, ensure_ascii=False, indent=2)[:20000]}

**עמוד מהספר של רוחמה (בית מרקובסקי) שצריך להיכנס:**
ספר: בית מרקובסקי
פרק: {chapter}
עמוד: {page_num}

העמוד עם מספרי שורות:
{lines_text}

המטרה שלך:
1. חלק את העמוד הזה מהספר של רוחמה לפסקאות בעלות הקשר (contextually coherent paragraphs)
2. קבע לכל פסקה איפה היא צריכה להיכנס בספר של יהודה

**חשוב:**
- הספר של יהודה נשאר בסדר המקורי שלו
- קרא את הטקסט של הספר של יהודה כדי להבין את ההקשר הכרונולוגי והנרטיבי
- חלק את העמוד לפסקאות לפי הקשר - כל פסקה צריכה להיות בעלת הקשר כרונולוגי/נרטיבי אחיד
- פסקה יכולה להיות שורה אחת, כמה שורות, או חלק מעמוד
- כל פסקה צריכה להיכנס בנקודה המתאימה בספר של יהודה לפי הקשר כרונולוגי ונרטיבי
- השתמש בהבנת הקשר: אם פסקה מתארת אירוע שקרה לפני אירוע בספר של יהודה, הכנס אותה לפני
- אם פסקה מתארת אותו אירוע או אירוע דומה, הכנס אותה ליד אותו מקום
- אם פסקה מתארת אירוע שקרה אחרי, הכנס אותה אחרי
- זהה תאריכים, אירועים היסטוריים, ומקומות מהטקסט כדי להבין את ההקשר הכרונולוגי

תן לי רשימה של insertion points בפורמט JSON:

{{
  "paragraphs": [
    {{
      "source_line_start": <מספר שורה התחלה בספר של רוחמה>,
      "source_line_end": <מספר שורה סוף בספר של רוחמה>,
      "insert_after_page": <מספר עמוד בספר של יהודה אחרי איזה להכניס>,
      "insert_after_line": <מספר שורה בספר של יהודה אחרי איזה להכניס>,
      "insert_reason": <סיבה קצרה למה כאן - לפי הקשר כרונולוגי/נרטיבי>,
      "confidence": <"high"/"medium"/"low">
    }},
    ...
  ]
}}

תן רק את ה-JSON, בלי טקסט נוסף."""
    
    return prompt

def determine_insertion_points_for_pages(ruchama_pages, yehuda_context, genai_model):
    """Determine insertion points for Ruchama pages - AI divides each page into paragraphs and determines insertion points"""
    
    insertion_points = []
    
    # Process each Ruchama page
    for i, ruchama_page in enumerate(ruchama_pages, 1):
        page_num = ruchama_page.get('page_number')
        chapter = ruchama_page.get('chapter', '')
        
        print(f"\n[{i}/{len(ruchama_pages)}] Processing Ruchama page {page_num} ({chapter})...")
        print(f"   AI will divide into paragraphs and determine insertion points for each")
        
        MAX_RETRIES = 3
        RETRY_DELAY = 2
        
        for attempt in range(MAX_RETRIES):
            try:
                # Build prompt
                prompt_text = determine_insertion_points_for_page(ruchama_page, yehuda_context)
                
                response = genai_model.generate_content(prompt_text)
                
                if not response or not response.text:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⚠️  Empty response, retrying ({attempt + 1}/{MAX_RETRIES})...")
                        time.sleep(RETRY_DELAY)
                        continue
                    break
                
                # Extract JSON from response
                response_text = response.text.strip()
                
                # Try to extract JSON if wrapped in markdown code blocks
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                response_text = response_text.strip()
                
                # Parse JSON
                try:
                    result_data = json.loads(response_text)
                    
                    # Extract paragraphs with insertion points
                    paragraphs = result_data.get('paragraphs', [])
                    
                    if paragraphs:
                        for para in paragraphs:
                            source_line_start = para.get('source_line_start')
                            source_line_end = para.get('source_line_end')
                            insert_after_page = para.get('insert_after_page')
                            insert_after_line = para.get('insert_after_line', 0)
                            insert_reason = para.get('insert_reason', '')
                            confidence = para.get('confidence', 'medium')
                            
                            if source_line_start is not None and source_line_end is not None and insert_after_page is not None:
                                ip = {
                                    'source_page': page_num,
                                    'source_chapter': chapter,
                                    'source_line_start': source_line_start,
                                    'source_line_end': source_line_end,
                                    'insert_after_page': insert_after_page,
                                    'insert_after_line': insert_after_line,
                                    'insert_reason': insert_reason,
                                    'confidence': confidence
                                }
                                insertion_points.append(ip)
                        
                        print(f"  ✅ Page {page_num} → divided into {len(paragraphs)} paragraphs")
                        for para in paragraphs[:3]:  # Show first 3
                            print(f"     Lines {para.get('source_line_start')}-{para.get('source_line_end')} → insert after Yehuda page {para.get('insert_after_page')}, line {para.get('insert_after_line')}")
                        if len(paragraphs) > 3:
                            print(f"     ... and {len(paragraphs) - 3} more paragraphs")
                        break  # Success
                    else:
                        print(f"  ⚠️  No paragraphs found in response")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                            continue
                    
                except json.JSONDecodeError as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  ⚠️  JSON parsing error, retrying ({attempt + 1}/{MAX_RETRIES})...")
                        print(f"     Error: {e}")
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        print(f"  ❌ JSON parsing error after {MAX_RETRIES} attempts: {e}")
                        print(f"  Response preview: {response_text[:300]}...")
                        break
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  Error, retrying ({attempt + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"  ❌ Error after {MAX_RETRIES} attempts: {e}")
                    break
        
        # Rate limiting
        if i < len(ruchama_pages):
            time.sleep(0.5)  # 0.5 second delay between pages
    
    return insertion_points

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load API key
    print("Loading Gemini API key...")
    api_key = load_api_key()
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    print("✅ Gemini API configured")
    
    # Load tagged pages
    print("\nLoading tagged pages...")
    tagged_data = load_tagged_pages()
    if not tagged_data:
        return
    
    # Prepare context
    print("Preparing context for AI...")
    yehuda_context, yehuda_pages = prepare_yehuda_context(tagged_data)
    ruchama_pages = get_ruchama_pages(tagged_data)
    
    print(f"✅ Prepared context:")
    print(f"   Yehuda's book: {len(yehuda_context)} pages (AI will read the text to understand chronological context)")
    print(f"   Ruchama's book: {len(ruchama_pages)} pages (to be inserted)")
    print(f"💡 No need to tag Yehuda's book - AI understands chronological context from reading the text!")
    
    # Determine insertion points - AI divides each page into paragraphs and determines insertion points
    print(f"\nDetermining insertion points for Ruchama pages...")
    print(f"💡 AI will:")
    print(f"   1. Divide each Ruchama page into contextually coherent paragraphs")
    print(f"   2. Determine insertion point (page + line) in Yehuda's book for each paragraph")
    insertion_points = determine_insertion_points_for_pages(ruchama_pages, yehuda_context, model)
    
    # Save insertion points
    output_file = output_dir / 'insertion_points.json'
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_ruchama_pages': len(ruchama_pages),
            'insertion_points_found': len(insertion_points),
            'method': 'gemini_api_paragraph_based',
            'model': 'gemini-1.5-flash',
            'description': 'AI divides Ruchama pages into paragraphs and determines insertion points for each paragraph'
        },
        'insertion_points': insertion_points
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Determined {len(insertion_points)} insertion points")
    print(f"✅ Saved to: {output_file}")
    
    if len(insertion_points) < len(ruchama_pages):
        print(f"\n⚠️  Warning: Only {len(insertion_points)}/{len(ruchama_pages)} pages got insertion points")
    
    print(f"\n📝 Next step: Run 03_merge_books_with_ai_tags.py to merge based on insertion points")

if __name__ == "__main__":
    main()
