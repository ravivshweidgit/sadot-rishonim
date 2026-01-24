#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to create a chronological timeline movie from both books.
Merges scenes from both books by timeline, creating a continuous narrative
that combines narration from both books in chronological order.
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

def load_merged_scenes():
    """Load merged scenes"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    scenes_file = project_root / 'movie' / 'output' / 'scripts' / 'merged_scenes.json'
    
    if not scenes_file.exists():
        print(f"Error: {scenes_file} not found. Run merge_scenes_from_books.py first.")
        return None
    
    with open(scenes_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def group_scenes_by_timeline(scenes):
    """Group scenes by year and month (if available) for chronological ordering"""
    timeline_groups = defaultdict(list)
    
    for scene in scenes:
        year = scene.get('year')
        if not year:
            # Try to estimate year from other clues
            years_mentioned = scene.get('years_mentioned', [])
            if years_mentioned:
                year = min([y for y in years_mentioned if 1900 <= y <= 1921] or [9999])
            else:
                year = 9999  # Unknown year goes to end
        
        # Create timeline key (year, month if available)
        timeline_key = (year, scene.get('page_number', 0))
        timeline_groups[timeline_key].append(scene)
    
    return timeline_groups

def merge_scenes_by_timeline(scene_list):
    """Merge multiple scenes from the same time period"""
    if len(scene_list) == 1:
        return scene_list[0]
    
    # Sort by book priority and page
    book_priority = {'sadot_rishonim': 0, 'beit_markovski': 1}
    scene_list.sort(key=lambda x: (
        book_priority.get(x.get('book_id', ''), 99),
        x.get('page_number', 0)
    ))
    
    base_scene = scene_list[0].copy()
    
    # Merge information
    all_characters = set(base_scene.get('characters', []))
    all_locations = set(base_scene.get('locations_mentioned', []))
    all_years = set(base_scene.get('years_mentioned', []))
    all_texts = [base_scene.get('full_text', '')]
    narration_texts = []
    source_books = [base_scene.get('book_id')]
    source_pages = [base_scene.get('page_number')]
    
    for scene in scene_list[1:]:
        all_characters.update(scene.get('characters', []))
        all_locations.update(scene.get('locations_mentioned', []))
        all_years.update(scene.get('years_mentioned', []))
        all_texts.append(scene.get('full_text', ''))
        
        # Collect narration texts with book attribution
        narration = scene.get('narration_text', scene.get('full_text', ''))
        book_name = scene.get('book_name', scene.get('book_id', ''))
        if narration:
            narration_texts.append(f"[מ{book_name}]\n{narration}")
        
        source_books.append(scene.get('book_id'))
        source_pages.append(scene.get('page_number'))
    
    # Add base scene narration
    base_narration = base_scene.get('narration_text', base_scene.get('full_text', ''))
    base_book_name = base_scene.get('book_name', base_scene.get('book_id', ''))
    if len(scene_list) > 1:
        narration_texts.insert(0, f"[מ{base_book_name}]\n{base_narration}")
    else:
        narration_texts.insert(0, base_narration)
    
    # Update merged scene
    base_scene['id'] = f"timeline_{base_scene.get('year', 'unknown')}_{len(scene_list)}books"
    base_scene['is_timeline_merged'] = True
    base_scene['source_scenes'] = [s['id'] for s in scene_list]
    base_scene['characters'] = sorted(list(all_characters))
    base_scene['locations_mentioned'] = sorted(list(all_locations))
    base_scene['years_mentioned'] = sorted(list(all_years))
    base_scene['source_books'] = list(set(source_books))
    base_scene['source_pages'] = source_pages
    
    # Combine texts
    base_scene['full_text'] = '\n\n---\n\n'.join(all_texts)
    
    # Create combined narration from both books
    base_scene['narration_text'] = '\n\n'.join(narration_texts)
    
    # Estimate duration
    words = len(base_scene['narration_text'].split())
    base_scene['narration_duration_estimate'] = int((words / 2.5) * 1.2)
    
    # Update visual requirements
    if 'visual_requirements' not in base_scene:
        base_scene['visual_requirements'] = {}
    base_scene['visual_requirements']['characters'] = sorted(list(all_characters))
    base_scene['visual_requirements']['setting'] = base_scene.get('location') or 'unknown'
    
    return base_scene

def create_timeline_movie(scenes):
    """Create a chronological timeline movie from scenes"""
    print("Creating chronological timeline from both books...")
    
    # Group scenes by timeline
    timeline_groups = group_scenes_by_timeline(scenes)
    
    # Sort timeline groups chronologically
    sorted_timeline = sorted(timeline_groups.items(), key=lambda x: (x[0][0], x[0][1]))
    
    timeline_scenes = []
    
    for (year, page_num), scene_list in sorted_timeline:
        if len(scene_list) > 1:
            # Multiple scenes from same time period - merge them
            merged = merge_scenes_by_timeline(scene_list)
            timeline_scenes.append(merged)
            print(f"  Timeline {year}: Merged {len(scene_list)} scenes from both books")
        else:
            # Single scene - keep as is
            scene = scene_list[0].copy()
            # Ensure narration has book attribution
            if 'narration_text' not in scene:
                scene['narration_text'] = scene.get('full_text', '')
            book_name = scene.get('book_name', scene.get('book_id', ''))
            if book_name and not scene['narration_text'].startswith('['):
                scene['narration_text'] = f"[מ{book_name}]\n{scene['narration_text']}"
            timeline_scenes.append(scene)
            print(f"  Timeline {year}: Scene from {scene.get('book_id')}")
    
    return timeline_scenes

def add_transitions(timeline_scenes):
    """Add transition information between scenes"""
    for i in range(len(timeline_scenes) - 1):
        current = timeline_scenes[i]
        next_scene = timeline_scenes[i + 1]
        
        current_year = current.get('year', 0)
        next_year = next_scene.get('year', 0)
        
        # Add transition info
        if 'transition' not in current:
            current['transition'] = {}
        
        if next_year > current_year:
            # Time jump forward
            years_passed = next_year - current_year
            current['transition']['type'] = 'time_jump_forward'
            current['transition']['years'] = years_passed
            current['transition']['text'] = f"[{years_passed} שנים חלפו]"
        elif next_year < current_year:
            # Time jump backward (shouldn't happen in chronological order)
            current['transition']['type'] = 'time_jump_backward'
        else:
            # Same year - smooth transition
            current['transition']['type'] = 'smooth'
            current['transition']['text'] = "[המשך]"
    
    return timeline_scenes

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scripts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load merged scenes
    print("Loading merged scenes...")
    scenes_data = load_merged_scenes()
    if not scenes_data:
        return
    
    scenes = scenes_data.get('scenes', [])
    print(f"Found {len(scenes)} scenes")
    
    # Create chronological timeline
    timeline_scenes = create_timeline_movie(scenes)
    
    # Add transitions
    timeline_scenes = add_transitions(timeline_scenes)
    
    # Create output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(timeline_scenes),
            "books_processed": ["sadot_rishonim", "beit_markovski"],
            "time_period": "1900-1921",
            "focus_location": "metula",
            "structure": "chronological_timeline",
            "description": "Chronological timeline movie combining both books"
        },
        "timeline": timeline_scenes
    }
    
    # Save timeline
    output_file = output_dir / 'timeline_movie.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Created chronological timeline with {len(timeline_scenes)} scenes")
    print(f"✅ Saved to {output_file}")
    
    # Print timeline summary
    print("\n📅 Timeline Summary:")
    year_counts = defaultdict(int)
    book_counts = defaultdict(int)
    
    for scene in timeline_scenes:
        year = scene.get('year', 'unknown')
        year_counts[year] += 1
        for book in scene.get('source_books', [scene.get('book_id')]):
            book_counts[book] += 1
    
    print(f"\n  Scenes by year:")
    for year in sorted([y for y in year_counts.keys() if isinstance(y, int)]):
        print(f"    {year}: {year_counts[year]} scenes")
    
    print(f"\n  Scenes by book:")
    for book, count in sorted(book_counts.items()):
        book_name = "שדות ראשונים" if book == "sadot_rishonim" else "בית מרקובסקי"
        print(f"    {book_name}: {count} scenes")
    
    # Calculate total duration
    total_duration = sum(s.get('narration_duration_estimate', 0) for s in timeline_scenes)
    print(f"\n  📊 Total estimated duration: {total_duration}s ({total_duration/60:.1f} minutes)")

if __name__ == "__main__":
    main()
