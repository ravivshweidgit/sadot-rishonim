#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט שמתייג טווחי שורות בתוך עמודים אוטומטית באמצעות Gemini API.
משתמש ב-API key הקיים ב-python/api_key.txt

הגישה החדשה:
1. AI מתייג כל עמוד עם זמן ומקום (כמו קודם)
2. AI קובע insertion points: לכל קטע מהספר של רוחמה, AI קובע איפה הוא צריך להיכנס בספר של יהודה
3. Python ממזג לפי insertion points (שומר על הסדר המקורי של הספר של יהודה)

זה מאפשר ל-AI להבין את ההקשר הכרונולוגי בין שני הספרים ולקבוע איפה כל קטע מתאים.
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

def load_tagging_template():
    """Load the tagging template created by tag_pages_with_ai.py"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    template_file = project_root / 'movie' / 'output' / 'scripts' / 'pages_for_ai_tagging.json'
    
    if not template_file.exists():
        print(f"Error: {template_file} not found.")
        print(f"Please run 01_tag_pages_with_ai.py first to create the template.")
        return None
    
    with open(template_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def tag_page_lines_with_gemini(page, genai_model, all_pages_context=None):
    """Tag line ranges within a page using Gemini API
    
    Args:
        page: The page to tag
        genai_model: The Gemini model to use
        all_pages_context: Optional context from all pages (for better chronological understanding)
    """
    
    lines = page.get('lines', [])
    lines_text = "\n".join([f"{line['line_number']:3d}: {line['text']}" for line in lines if not line['is_empty']])
    
    # Build context from other pages if available
    context_note = ""
    if all_pages_context:
        # Add a note about chronological context
        context_note = "\n\n**הקשר כרונולוגי:**\n"
        context_note += "יש לך גישה לשני ספרים על החיים במטולה בשנים 1900-1921:\n"
        context_note += "- ספר של יהודה (שדות ראשונים) - מספר את הסיפור מנקודת מבטו\n"
        context_note += "- ספר של רוחמה (בית מרקובסקי) - מספר את הסיפור מנקודת מבטה\n"
        context_note += "השתמש בהבנת הקשר הכרונולוגי בין שני הספרים כדי לזהות תאריכים גם אם הם לא מפורשים בעמוד הזה.\n"
        context_note += "לדוגמה: אם בספר של רוחמה עמוד 5 מתאר הגעה ליפו ב-1904, ועמוד 9 בספר של יהודה מתאר ילדות ברוסיה, אז עמוד 9 קרה לפני 1904.\n"
    
    prompt = f"""קח את העמוד הבא משני ספרים על החיים במטולה בשנים 1900-1921.
{context_note}
ספר: {page.get('book_name', '')}
פרק: {page.get('chapter', '')}
עמוד: {page.get('page_number', '')}
סה"כ שורות: {len(lines)}

העמוד עם מספרי שורות:
{lines_text}

המטרה שלך: תייג טווחי שורות (line ranges) בתוך העמוד הזה.
כל טווח שורות צריך להיות מתוייג לפי שנה, חודש, מיקום.

**חשוב:** השתמש בהבנת הקשר הכרונולוגי בין שני הספרים כדי לזהות תאריכים גם אם הם לא מפורשים בעמוד הזה.

תן לי רשימה של תיוגים בפורמט JSON:

{{
  "line_tags": [
    {{
      "line_start": <מספר שורה התחלה>,
      "line_end": <מספר שורה סוף>,
      "year": <מספר או null> - השנה (1900-1921), אם יש תאריך מפורש השתמש בו, אם לא נסה להעריך לפי הקשר
      "month": <מחרוזת או null> - החודש (אם ניתן לזהות), דוגמאות: "ינואר", "פברואר", "ניסן"
      "location": <מחרוזת או null> - המיקום הגיאוגרפי הראשי, דוגמאות: "metula", "jaffa", "beer_tuvia", "russia", "tel_hai"
      "locations": [<רשימה>] - כל המיקומים המוזכרים בטווח השורות הזה
      "characters": [<רשימה>] - הדמויות המוזכרות, דוגמאות: ["yehuda", "yosef", "moriah"]
      "confidence": <"high"/"medium"/"low"> - רמת ביטחון בתיוג
    }},
    ...
  ]
}}

חשוב:
- תייג טווחי שורות (לא כל שורה בנפרד, אלא קבוצות שורות עם אותו הקשר)
- כל טווח צריך להיות רציף (line_start עד line_end)
- טווחים יכולים להיות שורה אחת (line_start == line_end) או כמה שורות
- השתמש בהבנת הקשר כדי לזהות תאריכים ומיקומים גם אם הם לא מפורשים
- אם יש אירוע היסטורי מוזכר (כמו "מלחמת העולם הראשונה"), השתמש בו
- שמור על דיוק - אל תמציא תאריכים אם אתה לא בטוח
- ודא שכל השורות בעמוד מכוסות (או לפחות השורות הלא-ריקות)

תן רק את ה-JSON, בלי טקסט נוסף."""

    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    for attempt in range(MAX_RETRIES):
        try:
            response = genai_model.generate_content(prompt)
            
            if not response or not response.text:
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  Empty response, retrying ({attempt + 1}/{MAX_RETRIES})...")
                    time.sleep(RETRY_DELAY)
                    continue
                return []
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            # Remove any leading/trailing whitespace and newlines
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                tag_data = json.loads(response_text)
                # Extract line_tags from response
                line_tags = tag_data.get('line_tags', [])
                
                # Validate line_tags structure
                if not isinstance(line_tags, list):
                    print(f"  ⚠️  line_tags is not a list, got: {type(line_tags)}")
                    return []
                
                # Validate each tag
                valid_tags = []
                for i, tag in enumerate(line_tags):
                    if not isinstance(tag, dict):
                        print(f"  ⚠️  Tag {i} is not a dict, skipping")
                        continue
                    
                    line_start = tag.get('line_start')
                    line_end = tag.get('line_end')
                    
                    if not isinstance(line_start, int) or not isinstance(line_end, int):
                        print(f"  ⚠️  Tag {i} has invalid line numbers, skipping")
                        continue
                    
                    if line_start < 1 or line_end < 1:
                        print(f"  ⚠️  Tag {i} has line numbers < 1, skipping")
                        continue
                    
                    if line_start > line_end:
                        print(f"  ⚠️  Tag {i} has line_start > line_end, skipping")
                        continue
                    
                    valid_tags.append(tag)
                
                if len(valid_tags) < len(line_tags):
                    print(f"  ⚠️  Filtered {len(line_tags) - len(valid_tags)} invalid tags")
                
                return valid_tags
                
            except json.JSONDecodeError as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  JSON parsing error, retrying ({attempt + 1}/{MAX_RETRIES})...")
                    print(f"     Error: {e}")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"  ❌ JSON parsing error after {MAX_RETRIES} attempts: {e}")
                    print(f"  Response preview: {response_text[:300]}...")
                    return []
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠️  Error tagging page {page.get('id')}, retrying ({attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print(f"  ❌ Error tagging page {page.get('id')} after {MAX_RETRIES} attempts: {e}")
                return []
    
    return []

def tag_all_pages_with_gemini():
    """Tag line ranges in all pages using Gemini API"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load API key
    print("Loading Gemini API key...")
    api_key = load_api_key()
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')  # Using flash for speed
    
    print("✅ Gemini API configured")
    
    # Load tagging template
    print("\nLoading tagging template...")
    template_data = load_tagging_template()
    if not template_data:
        return
    
    pages = template_data.get('pages', [])
    
    # Note: We don't need to tag Yehuda's book anymore!
    # AI can understand chronological context from reading the text itself
    print(f"Found {len(pages)} total pages")
    print(f"💡 Note: No need to tag Yehuda's book - AI will understand chronological context from reading the text")
    print(f"   All pages will be saved, but only Ruchama's pages will need insertion points determined")
    
    # Actually, we don't need to tag anything!
    # Just save all pages as-is - AI will determine insertion points by reading the text
    print(f"\n💡 Skipping tagging - AI will understand chronological context from reading the text")
    print(f"   All {len(pages)} pages will be saved without tags")
    print(f"   Insertion points will be determined in the next step (02b_determine_insertion_points.py)")
    
    tagged_pages = []
    for page in pages:
        # No tags needed - AI will read the text to understand context
        page['line_tags'] = []  # Empty tags - not needed!
        tagged_pages.append(page)
        
        # Add line_tags to page
        page['line_tags'] = line_tags
        tagged_pages.append(page)
        
        # Show result
        if line_tags:
            print(f"  ✅ Created {len(line_tags)} line range tags")
            first_tag = line_tags[0]
            print(f"     Example: lines {first_tag.get('line_start')}-{first_tag.get('line_end')}, "
                  f"Year: {first_tag.get('year')}, Location: {first_tag.get('location')}")
            
            # Check coverage
            total_lines = len(page.get('lines', []))
            if total_lines > 0:
                covered_lines = set()
                for tag in line_tags:
                    covered_lines.update(range(tag.get('line_start', 0), tag.get('line_end', 0) + 1))
                coverage_pct = (len(covered_lines) / total_lines) * 100
                print(f"     Coverage: {len(covered_lines)}/{total_lines} lines ({coverage_pct:.1f}%)")
        else:
            print(f"  ⚠️  No tags created for this page")
        
        # Rate limiting - small delay to avoid hitting API limits
        if i < len(pages):
            time.sleep(0.5)  # 0.5 second delay between requests
    
    # Create output
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(tagged_pages),
            'books': ['sadot_rishonim', 'beit_markovski'],
            'method': 'gemini_api_automatic',
            'model': 'gemini-1.5-flash',
            'tagging_granularity': 'line_ranges'
        },
        'pages': tagged_pages
    }
    
    # Save tagged pages
    output_file = output_dir / 'pages_tagged_by_ai.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Tagged {len(tagged_pages)} pages")
    print(f"✅ Saved to: {output_file}")
    
    # Print detailed summary
    print("\n📊 Summary:")
    print(f"  Total pages tagged: {len(tagged_pages)}")
    
    # Count total line tags
    total_line_tags = sum(len(page.get('line_tags', [])) for page in tagged_pages)
    print(f"  Total line range tags: {total_line_tags}")
    
    # Count pages with/without tags
    pages_with_tags = sum(1 for page in tagged_pages if page.get('line_tags'))
    pages_without_tags = len(tagged_pages) - pages_with_tags
    print(f"  Pages with tags: {pages_with_tags}")
    if pages_without_tags > 0:
        print(f"  ⚠️  Pages without tags: {pages_without_tags}")
    
    # Count by year
    year_counts = {}
    for page in tagged_pages:
        for tag in page.get('line_tags', []):
            year = tag.get('year')
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1
    
    if year_counts:
        print(f"\n  Line ranges by year:")
        for year in sorted([y for y in year_counts.keys() if isinstance(y, int) and y != 9999]):
            print(f"    {year}: {year_counts[year]} line ranges")
        if 9999 in year_counts:
            print(f"    Unknown: {year_counts[9999]} line ranges")
    
    # Count by confidence
    confidence_counts = {}
    for page in tagged_pages:
        for tag in page.get('line_tags', []):
            conf = tag.get('confidence', 'unknown')
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
    
    if confidence_counts:
        print(f"\n  Line ranges by confidence:")
        for conf, count in sorted(confidence_counts.items()):
            print(f"    {conf}: {count} line ranges")
    
    print(f"\n📝 Next step: Run 03_merge_books_with_ai_tags.py to merge based on tags")

if __name__ == "__main__":
    tag_all_pages_with_gemini()
