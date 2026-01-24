#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to extract scenes from books for AI movie generation.
Reads text files from sadot_rishonim and beit_markovski books,
identifies scenes, characters, locations, and time periods.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Character names mapping (Hebrew to English IDs)
CHARACTERS = {
    'יוסף': 'yosef',
    'יוסף מרקובסקי': 'yosef',
    'אבא': 'yosef',  # Context-dependent, might need refinement
    'מורייה': 'moriah',
    'מורייה מרקובסקי': 'moriah',
    'אמא': 'moriah',  # Context-dependent
    'יהודה': 'yehuda',
    'יהודה מרקובסקי': 'yehuda',
    'יהודה מור': 'yehuda',
    'רוחמה': 'ruchama',
    'רוחמה שחר': 'ruchama',
    'רוחמה מרקובסקי': 'ruchama',
    'עמנואל': 'emmanuel',
    'עמנואל מרקובסקי': 'emmanuel',
    'תרצה': 'tirza',
    'תרצה מרקובסקי': 'tirza',
    'ואזרח': 'vazrach',
    'ואזרח מרקובסקי': 'vazrach',
}

# Location names mapping
LOCATIONS = {
    'מטולה': 'metula',
    'נהלל': 'nahalal',
    'תל-חי': 'tel_hai',
    'תל חי': 'tel_hai',
    'כפר גלעדי': 'kfar_giladi',
    'יפו': 'jaffa',
    'אודיסה': 'odessa',
    'רוסיה': 'russia',
    'ילץ': 'yelts',
    'יקטרינוסלב': 'ekaterinoslav',
    'עמק יזרעאל': 'emek_yizrael',
    'באר טוביה': 'beer_tuvia',
    'באר-טוביה': 'beer_tuvia',
    'קוסטינה': 'beer_tuvia',  # השם הישן של באר טוביה
    'קסטינה': 'beer_tuvia',  # השם הישן של באר טוביה
    'ראש פינה': 'rosh_pina',
    'ראש-פינה': 'rosh_pina',
}

# Time period patterns
YEAR_PATTERNS = [
    r'(\d{4})',  # Simple year: 1904
    r'שנת (\d{4})',  # "שנת 1904"
    r'ב-(\d{4})',  # "ב-1904"
    r'בשנת (\d{4})',  # "בשנת 1904"
    r'(\d{4})-(\d{4})',  # Range: 1904-1921
]

def load_books_config():
    """Load books configuration"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    config_path = project_root / 'books-config.json'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_years(text):
    """Extract years mentioned in text"""
    years = []
    for pattern in YEAR_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                years.extend([int(m) for m in match if m.isdigit()])
            else:
                if match.isdigit():
                    years.append(int(match))
    return sorted(set(years))

def extract_characters(text):
    """Extract character names mentioned in text"""
    found_characters = set()
    text_lower = text.lower()
    
    for hebrew_name, char_id in CHARACTERS.items():
        if hebrew_name in text or hebrew_name.lower() in text_lower:
            found_characters.add(char_id)
    
    return sorted(list(found_characters))

def extract_locations(text, book_id=None, page_num=None, chapter_info=None):
    """Extract location names mentioned in text
    
    Uses chapter names to identify locations when text doesn't explicitly mention them.
    Special handling for beit_markovski based on chapter structure:
    - "בית אבא" (ch 2): Russia
    - "באר־טוביה" (ch 3): Beer Tuvia (also known as קוסטינה/קסטינה - the old name)
    - "ביפו" (ch 4): Jaffa
    - "אנו עולים הגלילה" (ch 5): Journey to Israel (Jaffa/on the way)
    - "מטולה" (ch 6-11): Metula
    - "צאתנו את מטולה" (ch 12): Still Metula (leaving)
    """
    found_locations = set()
    
    # First, extract locations explicitly mentioned in text
    for hebrew_name, loc_id in LOCATIONS.items():
        if hebrew_name in text:
            found_locations.add(loc_id)
    
    # Use chapter names to identify locations (especially for beit_markovski)
    if chapter_info and book_id == 'beit_markovski':
        chapter_name = chapter_info.get('name', '')
        
        if 'בית אבא' in chapter_name:
            found_locations.add('russia')
        elif 'באר־טוביה' in chapter_name or 'באר טוביה' in chapter_name:
            found_locations.add('beer_tuvia')
        elif 'ביפו' in chapter_name or 'יפו' in chapter_name:
            found_locations.add('jaffa')
        elif 'מטולה' in chapter_name:
            found_locations.add('metula')
        elif 'אנו עולים' in chapter_name or 'הגלילה' in chapter_name:
            # Journey to Israel - could be Jaffa or on the way
            found_locations.add('jaffa')
    
    # Fallback: if no location found and it's beit_markovski, use page ranges
    if not found_locations and book_id == 'beit_markovski' and page_num is not None:
        if 27 <= page_num <= 99:  # From "מטולה" chapter to "צאתנו את מטולה"
            found_locations.add('metula')
        elif 14 <= page_num < 27:  # באר טוביה to מטולה
            found_locations.add('beer_tuvia')
        elif 18 <= page_num < 23:  # ביפו
            found_locations.add('jaffa')
        elif 9 <= page_num < 14:  # בית אבא
            found_locations.add('russia')
    
    return sorted(list(found_locations))

def determine_time_period(years, page_num, chapter_info, book_id=None):
    """Determine the time period for a scene
    
    Uses chapter names and book structure to estimate time periods:
    - beit_markovski: "בית אבא" (Russia, ~1900-1904), "באר־טוביה" (~1904), 
      "ביפו" (~1904), "מטולה" (1905-1920), "מלחמת העולם" (1914-1918)
    - sadot_rishonim: "ראשית" (~1904), "מטולה" (1905-1920), etc.
    """
    if years:
        # Use the earliest year mentioned
        year = min(years)
        if 1900 <= year <= 1921:
            return year
    
    # Fallback: estimate from chapter/page
    if chapter_info:
        chapter_name = chapter_info.get('name', '')
        
        # beit_markovski specific chapters
        if book_id == 'beit_markovski':
            if 'בית אבא' in chapter_name:
                return 1900  # Russia, before immigration
            elif 'באר־טוביה' in chapter_name or 'באר טוביה' in chapter_name:
                return 1904  # Beer Tuvia period
            elif 'ביפו' in chapter_name or 'יפו' in chapter_name:
                return 1904  # Jaffa period
            elif 'אנו עולים' in chapter_name or 'הגלילה' in chapter_name:
                return 1904  # Journey to Israel
            elif 'מטולה' in chapter_name:
                # Metula period - estimate based on page number within chapter
                if page_num < 86:  # Before WWI chapter
                    return 1905
                elif page_num < 96:  # During/after WWI
                    return 1918
                else:
                    return 1920  # End of Metula period
            elif 'מלחמת העולם' in chapter_name:
                return 1914
            elif 'צאתנו את מטולה' in chapter_name:
                return 1920  # Leaving Metula
        
        # sadot_rishonim chapters
        elif book_id == 'sadot_rishonim':
            if 'ראשית' in chapter_name or 'יפו' in chapter_name:
                return 1904
            elif 'מטולה' in chapter_name:
                return 1905
            elif 'מלחמת העולם' in chapter_name:
                return 1914
            elif 'תל-חי' in chapter_name:
                return 1920
            elif 'נהלל' in chapter_name:
                return 1921
    
    return None

def prepare_narration_text(text, book_id):
    """Prepare text for narration - clean and format for TTS"""
    # Remove page headers and numbers
    lines = text.split('\n')
    narration_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip page headers like "ראשית ● 9" or "מטולה ● 27"
        if '●' in line and len(line) < 30:
            continue
        # Skip page numbers at end of line
        if line.isdigit() and len(line) < 4:
            continue
        # Skip empty lines (but keep paragraph breaks)
        if line:
            narration_lines.append(line)
    
    # Join lines, preserving paragraph breaks
    narration = '\n'.join(narration_lines)
    
    # Add book attribution if needed (for merged scenes)
    # This will be handled in merge_scenes_from_books.py
    
    return narration

def estimate_narration_duration(text):
    """Estimate narration duration in seconds (Hebrew reading speed ~150 words/min)"""
    # Count words (Hebrew words separated by spaces)
    words = len(text.split())
    # Hebrew reading speed: ~150 words per minute = 2.5 words per second
    duration = words / 2.5
    # Add some buffer for pauses
    return int(duration * 1.2)  # 20% buffer

def read_text_file(file_path):
    """Read text file and return content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def process_book(book_id, book_config, project_root):
    """Process a single book and extract scenes"""
    print(f"\nProcessing book: {book_config['name']} ({book_id})")
    
    text_dir = project_root / 'books' / book_id / 'text'
    if not text_dir.exists():
        print(f"  Text directory not found: {text_dir}")
        return []
    
    scenes = []
    chapters = book_config.get('chapters', [])
    max_page = book_config.get('maxPage', 0)
    
    # Create chapter lookup
    chapter_lookup = {}
    for chapter in chapters:
        start_page = chapter['page']
        chapter_lookup[start_page] = chapter
    
    # Process each text file
    for page_num in range(max_page + 1):
        page_file = text_dir / f"{page_num:03d}.txt"
        
        if not page_file.exists():
            continue
        
        text = read_text_file(page_file)
        if not text:
            continue
        
        # Skip header lines (usually first 1-2 lines)
        lines = text.split('\n')
        content_lines = []
        for line in lines:
            line = line.strip()
            # Skip page headers like "ראשית ● 9" or "מטולה ● 27"
            if '●' in line and len(line) < 30:
                continue
            if line:
                content_lines.append(line)
        
        if not content_lines:
            continue
        
        content = '\n'.join(content_lines)
        
        # Find which chapter this page belongs to
        chapter_info = None
        for start_page in sorted(chapter_lookup.keys(), reverse=True):
            if page_num >= start_page:
                chapter_info = chapter_lookup[start_page]
                break
        
        # Extract information
        years = extract_years(content)
        characters = extract_characters(content)
        locations = extract_locations(content, book_id, page_num, chapter_info)  # Pass chapter_info for better location detection
        time_period = determine_time_period(years, page_num, chapter_info, book_id)  # Pass book_id for better time estimation
        
        # Prepare narration text (cleaned text for TTS)
        narration_text = prepare_narration_text(content, book_id)
        
        # Determine primary location
        # Special case: beit_markovski pages 1-107 are about Metula
        primary_location = locations[0] if locations else None
        if not primary_location and book_id == 'beit_markovski' and 1 <= page_num <= 107:
            primary_location = 'metula'
            if 'metula' not in locations:
                locations.append('metula')
        
        # Create scene
        scene = {
            "id": f"{book_id}_page_{page_num:03d}",
            "book_id": book_id,
            "book_name": book_config['name'],
            "page_number": page_num,
            "chapter": chapter_info['name'] if chapter_info else None,
            "chapter_number": chapter_info['number'] if chapter_info else None,
            "title": chapter_info['name'] if chapter_info else f"עמוד {page_num}",
            "year": time_period,
            "years_mentioned": years,
            "location": primary_location,
            "locations_mentioned": locations,
            "characters": characters,
            "description": content[:200] + "..." if len(content) > 200 else content,
            "full_text": content,
            "narration_text": narration_text,  # Text for voice narration
            "narration_duration_estimate": estimate_narration_duration(narration_text),  # Estimated seconds
            "source_text": content[:500],  # First 500 chars for reference
            "source_book": book_id,
            "source_page": page_num,
            "visual_requirements": {
                "setting": locations[0] if locations else "unknown",
                "characters": characters,
                "mood": "historical",
                "time_period": f"{time_period}s" if time_period else "unknown"
            }
        }
        
        scenes.append(scene)
        print(f"  Page {page_num:03d}: {len(characters)} characters, {len(locations)} locations, year: {time_period}")
    
    return scenes

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load books configuration
    books_config = load_books_config()
    
    all_scenes = []
    
    # Process each book
    for book_id, book_config in books_config['books'].items():
        # Focus on books relevant to Metula 1900-1921
        if book_id in ['sadot_rishonim', 'beit_markovski']:
            scenes = process_book(book_id, book_config, project_root)
            all_scenes.extend(scenes)
    
    # Filter scenes by time period (1900-1921)
    relevant_scenes = []
    for scene in all_scenes:
        year = scene.get('year')
        if year and 1900 <= year <= 1921:
            relevant_scenes.append(scene)
        elif scene.get('locations_mentioned') and 'metula' in scene['locations_mentioned']:
            # Include Metula scenes even if year is unclear
            relevant_scenes.append(scene)
    
    # Sort scenes by year, then by page
    relevant_scenes.sort(key=lambda x: (x.get('year') or 9999, x.get('page_number', 0)))
    
    # Create output structure
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(relevant_scenes),
            "books_processed": ['sadot_rishonim', 'beit_markovski'],
            "time_period": "1900-1921",
            "focus_location": "metula"
        },
        "scenes": relevant_scenes
    }
    
    # Save to JSON
    output_file = output_dir / 'scenes.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Extracted {len(relevant_scenes)} scenes")
    print(f"✅ Saved to {output_file}")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  Total scenes: {len(relevant_scenes)}")
    
    # Count by location
    location_counts = {}
    for scene in relevant_scenes:
        loc = scene.get('location') or 'unknown'
        location_counts[loc] = location_counts.get(loc, 0) + 1
    
    print(f"\n  Scenes by location:")
    for loc, count in sorted(location_counts.items(), key=lambda x: -x[1]):
        print(f"    {loc}: {count}")
    
    # Count by character
    character_counts = {}
    for scene in relevant_scenes:
        for char in scene.get('characters', []):
            character_counts[char] = character_counts.get(char, 0) + 1
    
    print(f"\n  Character appearances:")
    for char, count in sorted(character_counts.items(), key=lambda x: -x[1]):
        print(f"    {char}: {count}")

if __name__ == "__main__":
    main()
