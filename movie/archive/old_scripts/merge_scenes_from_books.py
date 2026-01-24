#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to merge scenes from both books and create enriched scenes with AI prompts.
This script takes scenes from both books, identifies related scenes (same time/place/characters),
and creates merged scenes with comprehensive information for AI video generation.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_scenes():
    """Load scenes from the extracted scenes.json file"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    scenes_file = project_root / 'movie' / 'output' / 'scripts' / 'scenes.json'
    
    with open(scenes_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_related_scenes(scenes):
    """Find scenes that describe the same event/time/place from both books"""
    # Group scenes by year and location
    scenes_by_key = defaultdict(list)
    
    for scene in scenes:
        year = scene.get('year')
        location = scene.get('location')
        characters = tuple(sorted(scene.get('characters', [])))
        
        # Create a key for grouping
        if year and location:
            key = (year, location, characters)
            scenes_by_key[key].append(scene)
        elif year:
            key = (year, None, characters)
            scenes_by_key[key].append(scene)
        elif location:
            key = (None, location, characters)
            scenes_by_key[key].append(scene)
    
    return scenes_by_key

def merge_scenes(scene_list):
    """Merge multiple scenes describing the same event"""
    if len(scene_list) == 1:
        return scene_list[0]
    
    # Sort by book priority (sadot_rishonim first, then beit_markovski)
    book_priority = {'sadot_rishonim': 0, 'beit_markovski': 1}
    scene_list.sort(key=lambda x: book_priority.get(x.get('book_id', ''), 99))
    
    base_scene = scene_list[0].copy()
    
    # Merge information from all scenes
    all_characters = set(base_scene.get('characters', []))
    all_locations = set(base_scene.get('locations_mentioned', []))
    all_years = set(base_scene.get('years_mentioned', []))
    all_texts = [base_scene.get('full_text', '')]
    all_descriptions = [base_scene.get('description', '')]
    source_books = [base_scene.get('book_id')]
    source_pages = [base_scene.get('page_number')]
    
    for scene in scene_list[1:]:
        all_characters.update(scene.get('characters', []))
        all_locations.update(scene.get('locations_mentioned', []))
        all_years.update(scene.get('years_mentioned', []))
        all_texts.append(scene.get('full_text', ''))
        all_descriptions.append(scene.get('description', ''))
        source_books.append(scene.get('book_id'))
        source_pages.append(scene.get('page_number'))
    
    # Update merged scene
    base_scene['id'] = f"merged_{base_scene.get('year', 'unknown')}_{base_scene.get('location', 'unknown')}"
    base_scene['is_merged'] = True
    base_scene['source_scenes'] = [s['id'] for s in scene_list]
    base_scene['characters'] = sorted(list(all_characters))
    base_scene['locations_mentioned'] = sorted(list(all_locations))
    base_scene['years_mentioned'] = sorted(list(all_years))
    base_scene['source_books'] = list(set(source_books))
    base_scene['source_pages'] = source_pages
    
    # Combine texts
    base_scene['full_text'] = '\n\n---\n\n'.join(all_texts)
    base_scene['combined_description'] = '\n\n'.join(all_descriptions)
    
    # Combine narration texts from both books
    narration_texts = []
    for scene in scene_list:
        narration = scene.get('narration_text', scene.get('full_text', ''))
        book_name = scene.get('book_name', scene.get('book_id', ''))
        if narration:
            # Add book attribution for merged scenes
            if len(scene_list) > 1:
                narration_texts.append(f"[מ{book_name}]\n{narration}")
            else:
                narration_texts.append(narration)
    
    # Combine narration texts
    combined_narration = '\n\n'.join(narration_texts)
    base_scene['narration_text'] = combined_narration
    
    # Estimate total narration duration
    total_duration = sum(s.get('narration_duration_estimate', 0) for s in scene_list)
    base_scene['narration_duration_estimate'] = total_duration
    
    # Create enriched visual requirements
    base_scene['visual_requirements'] = create_visual_requirements(base_scene, scene_list)
    
    # Create AI prompt for video generation
    base_scene['ai_prompt'] = create_ai_prompt(base_scene, scene_list)
    
    return base_scene

def create_visual_requirements(base_scene, all_scenes):
    """Create comprehensive visual requirements from merged scenes"""
    year = base_scene.get('year')
    location = base_scene.get('location')
    characters = base_scene.get('characters', [])
    
    # Get location details from config
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    locations_config = project_root / 'movie' / 'config' / 'locations.json'
    
    location_details = {}
    if locations_config.exists():
        with open(locations_config, 'r', encoding='utf-8') as f:
            locations_data = json.load(f)
            if location and location in locations_data.get('locations', {}):
                location_details = locations_data['locations'][location]
    
    # Determine mood from text
    full_text = base_scene.get('full_text', '').lower()
    mood = 'historical'
    if any(word in full_text for word in ['חג', 'שמחה', 'שמח', 'צחוק']):
        mood = 'joyful'
    elif any(word in full_text for word in ['קשה', 'קושי', 'מלחמה', 'פחד']):
        mood = 'tense'
    elif any(word in full_text for word in ['עבודה', 'שדה', 'חריש']):
        mood = 'working'
    elif any(word in full_text for word in ['משפחה', 'בית', 'ארוחה']):
        mood = 'family'
    
    return {
        "setting": location or "unknown",
        "setting_details": location_details.get('key_features', []),
        "characters": characters,
        "character_count": len(characters),
        "mood": mood,
        "time_period": f"{year}s" if year else "unknown",
        "year": year,
        "lighting": "natural" if year and 1900 <= year <= 1921 else "unknown",
        "atmosphere": "historical, early 20th century Palestine",
        "camera_angle": "medium_shot",  # Default, can be customized
        "action": extract_action_from_text(base_scene.get('full_text', ''))
    }

def extract_action_from_text(text):
    """Extract main action/activity from text"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['עלייה', 'עלה', 'הגעה', 'נמל']):
        return "arrival"
    elif any(word in text_lower for word in ['עבודה', 'חריש', 'שדה', 'חקלאות']):
        return "working"
    elif any(word in text_lower for word in ['משפחה', 'בית', 'ארוחה', 'אוכל']):
        return "family_life"
    elif any(word in text_lower for word in ['מלחמה', 'קרב', 'הגנה', 'שומר']):
        return "defense"
    elif any(word in text_lower for word in ['לימוד', 'בית ספר', 'מורה']):
        return "education"
    elif any(word in text_lower for word in ['נסיעה', 'דרך', 'רכיבה']):
        return "travel"
    else:
        return "daily_life"

def create_ai_prompt(scene, all_scenes):
    """Create a comprehensive AI prompt for video generation"""
    year = scene.get('year', 'unknown')
    location = scene.get('location', 'unknown')
    characters = scene.get('characters', [])
    full_text = scene.get('full_text', '')
    visual_req = scene.get('visual_requirements', {})
    
    # Load character details
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    characters_config = project_root / 'movie' / 'config' / 'characters.json'
    
    character_details = {}
    if characters_config.exists():
        with open(characters_config, 'r', encoding='utf-8') as f:
            chars_data = json.load(f)
            for char_id in characters:
                if char_id in chars_data.get('characters', {}):
                    char_info = chars_data['characters'][char_id]
                    # Determine age for this year
                    age_range = char_info.get('age_range', {})
                    age = None
                    if year and isinstance(year, int):
                        for age_year, age_label in age_range.items():
                            if int(age_year) <= year:
                                age = age_label
                    
                    character_details[char_id] = {
                        'hebrew_name': char_info.get('hebrew_name', ''),
                        'role': char_info.get('role', ''),
                        'age': age or 'unknown'
                    }
    
    # Build prompt
    prompt_parts = []
    
    # Scene description
    prompt_parts.append(f"Scene: {scene.get('title', 'Untitled')}")
    prompt_parts.append(f"Year: {year}")
    prompt_parts.append(f"Location: {location}")
    prompt_parts.append(f"Mood: {visual_req.get('mood', 'historical')}")
    
    # Characters
    if characters:
        prompt_parts.append("\nCharacters:")
        for char_id in characters:
            char_info = character_details.get(char_id, {})
            prompt_parts.append(f"  - {char_info.get('hebrew_name', char_id)} ({char_info.get('age', 'unknown')}): {char_info.get('role', '')}")
    
    # Visual setting
    prompt_parts.append(f"\nVisual Setting:")
    prompt_parts.append(f"  Location: {location}")
    if visual_req.get('setting_details'):
        prompt_parts.append(f"  Features: {', '.join(visual_req['setting_details'][:5])}")
    prompt_parts.append(f"  Time period: {visual_req.get('time_period', 'unknown')}")
    prompt_parts.append(f"  Atmosphere: {visual_req.get('atmosphere', 'historical')}")
    prompt_parts.append(f"  Action: {visual_req.get('action', 'daily_life')}")
    
    # Source material
    prompt_parts.append(f"\nSource Material (from books):")
    prompt_parts.append(f"  Books: {', '.join(scene.get('source_books', []))}")
    prompt_parts.append(f"  Text excerpt: {full_text[:300]}...")
    
    # Instructions
    prompt_parts.append(f"\nInstructions for AI Video Generation:")
    prompt_parts.append(f"  1. Create a scene showing: {visual_req.get('action', 'daily_life')}")
    prompt_parts.append(f"  2. Include characters: {', '.join(characters)}")
    prompt_parts.append(f"  3. Set in: {location} ({year})")
    prompt_parts.append(f"  4. Mood: {visual_req.get('mood', 'historical')}")
    prompt_parts.append(f"  5. Use historical accuracy for clothing, buildings, and environment")
    prompt_parts.append(f"  6. Reference archive photos for location accuracy")
    prompt_parts.append(f"  7. Use learned face models for character consistency")
    
    return '\n'.join(prompt_parts)

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading scenes from books...")
    scenes_data = load_scenes()
    scenes = scenes_data.get('scenes', [])
    
    print(f"Found {len(scenes)} scenes from books")
    
    # Find related scenes
    print("\nFinding related scenes from both books...")
    scenes_by_key = find_related_scenes(scenes)
    
    # Merge scenes
    merged_scenes = []
    standalone_scenes = []
    
    for key, scene_list in scenes_by_key.items():
        if len(scene_list) > 1:
            # Multiple scenes describe the same event - merge them
            merged = merge_scenes(scene_list)
            merged_scenes.append(merged)
            print(f"  Merged {len(scene_list)} scenes: {key}")
        else:
            # Single scene - keep as is but enrich it
            scene = scene_list[0].copy()
            # Ensure narration_text exists
            if 'narration_text' not in scene:
                scene['narration_text'] = scene.get('full_text', '')
            if 'narration_duration_estimate' not in scene:
                # Estimate duration (150 words/min = 2.5 words/sec)
                words = len(scene['narration_text'].split())
                scene['narration_duration_estimate'] = int((words / 2.5) * 1.2)
            scene['ai_prompt'] = create_ai_prompt(scene, [scene])
            standalone_scenes.append(scene)
    
    # Combine merged and standalone scenes
    all_enriched_scenes = merged_scenes + standalone_scenes
    
    # Sort by year, then by location
    all_enriched_scenes.sort(key=lambda x: (
        x.get('year') or 9999,
        x.get('location') or 'zzz',
        x.get('page_number', 0)
    ))
    
    # Create output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(all_enriched_scenes),
            "merged_scenes": len(merged_scenes),
            "standalone_scenes": len(standalone_scenes),
            "books_processed": ["sadot_rishonim", "beit_markovski"],
            "time_period": "1900-1921",
            "focus_location": "metula"
        },
        "scenes": all_enriched_scenes
    }
    
    # Save merged scenes
    output_file = output_dir / 'merged_scenes.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Created {len(merged_scenes)} merged scenes")
    print(f"✅ Total enriched scenes: {len(all_enriched_scenes)}")
    print(f"✅ Saved to {output_file}")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  Merged scenes (from both books): {len(merged_scenes)}")
    print(f"  Standalone scenes: {len(standalone_scenes)}")
    print(f"  Total scenes with AI prompts: {len(all_enriched_scenes)}")
    
    # Show example merged scene
    if merged_scenes:
        example = merged_scenes[0]
        print(f"\n📝 Example merged scene:")
        print(f"  ID: {example['id']}")
        print(f"  Year: {example.get('year')}")
        print(f"  Location: {example.get('location')}")
        print(f"  Characters: {', '.join(example.get('characters', []))}")
        print(f"  Source books: {', '.join(example.get('source_books', []))}")
        print(f"  AI Prompt length: {len(example.get('ai_prompt', ''))} characters")

if __name__ == "__main__":
    main()
