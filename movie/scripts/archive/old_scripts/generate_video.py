#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to generate video scenes synchronized with narration.
This script creates video for each scene that matches the narration duration exactly.
The narration drives the video - video duration = narration duration.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_merged_scenes():
    """Load merged scenes with narration"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    scenes_file = project_root / 'movie' / 'output' / 'scripts' / 'merged_scenes.json'
    
    if not scenes_file.exists():
        print(f"Error: {scenes_file} not found. Run merge_scenes_from_books.py first.")
        return None
    
    with open(scenes_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_narration_index():
    """Load narration index to get audio file paths and durations"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    index_file = project_root / 'movie' / 'output' / 'narration' / 'narration_index.json'
    
    if not index_file.exists():
        print(f"Warning: {index_file} not found. Run generate_narration.py first.")
        return {}
    
    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Create lookup by scene_id
        lookup = {}
        for item in data.get('narration_files', []):
            lookup[item['scene_id']] = item
        return lookup

def get_audio_duration(audio_file):
    """Get duration of audio file in seconds"""
    try:
        import mutagen
        audio = mutagen.File(audio_file)
        if audio:
            return int(audio.info.length)
    except ImportError:
        print("Warning: mutagen not installed. Install with: pip install mutagen")
    except Exception:
        pass
    
    # Fallback: use estimate from scene
    return None

def select_background_image(location, year, project_root):
    """Select appropriate background image from archive photos"""
    locations_dir = project_root / 'movie' / 'data' / 'locations' / location
    
    if not locations_dir.exists():
        print(f"  ⚠️  Location images not found: {locations_dir}")
        return None
    
    # Look for images matching the year
    images = list(locations_dir.glob("*.jpg")) + list(locations_dir.glob("*.png"))
    
    if not images:
        print(f"  ⚠️  No images found for location: {location}")
        return None
    
    # Return first available image (can be improved with year matching)
    return images[0]

def load_character_faces(characters, project_root):
    """Load face images for characters"""
    faces = {}
    
    for char_id in characters:
        faces_dir = project_root / 'movie' / 'data' / 'faces' / char_id
        
        if not faces_dir.exists():
            print(f"  ⚠️  Face images not found for: {char_id}")
            continue
        
        # Get first available face image
        face_images = list(faces_dir.glob("*.jpg")) + list(faces_dir.glob("*.png"))
        if face_images:
            faces[char_id] = str(face_images[0])
    
    return faces

def generate_video_scene(scene, narration_info, project_root, output_dir):
    """
    Generate video scene synchronized with narration.
    
    Args:
        scene: Scene data from merged_scenes.json
        narration_info: Narration file info (path, duration)
        project_root: Project root directory
        output_dir: Output directory for video files
    
    Returns:
        dict with video file info
    """
    scene_id = scene.get('id', 'unknown')
    visual_req = scene.get('visual_requirements', {})
    
    print(f"\n🎬 Generating video for scene: {scene_id}")
    
    # Get narration duration
    narration_duration = narration_info.get('duration_estimate', 0)
    if narration_info.get('audio_file'):
        actual_duration = get_audio_duration(narration_info['audio_file'])
        if actual_duration:
            narration_duration = actual_duration
    
    if narration_duration == 0:
        print(f"  ⚠️  No narration duration found, using estimate from scene")
        narration_duration = scene.get('narration_duration_estimate', 30)
    
    print(f"  📏 Narration duration: {narration_duration} seconds")
    
    # Select background image
    location = visual_req.get('setting', 'unknown')
    year = scene.get('year')
    background_image = select_background_image(location, year, project_root)
    
    if background_image:
        print(f"  🖼️  Background: {background_image.name}")
    else:
        print(f"  ⚠️  No background image, will use generated background")
    
    # Load character faces
    characters = visual_req.get('characters', [])
    character_faces = load_character_faces(characters, project_root)
    
    if character_faces:
        print(f"  👤 Characters: {', '.join(character_faces.keys())}")
    else:
        print(f"  ⚠️  No character faces found")
    
    # Create video (placeholder - actual implementation depends on video generation tool)
    # This is a template for integration with video generation APIs
    
    video_file = output_dir / f"{scene_id}.mp4"
    
    print(f"  🎥 Video will be created: {video_file}")
    print(f"  ⏱️  Duration: {narration_duration} seconds (synchronized with narration)")
    
    # TODO: Actual video generation
    # Options:
    # 1. Runway Gen-3 API
    # 2. Stable Video Diffusion
    # 3. AnimateDiff
    # 4. Other video generation tools
    
    return {
        'scene_id': scene_id,
        'video_file': str(video_file),
        'duration': narration_duration,
        'background_image': str(background_image) if background_image else None,
        'characters': list(character_faces.keys()),
        'status': 'pending'  # Will be 'completed' after actual generation
    }

def combine_scene_audio_video(scene_id, video_file, audio_file, output_file):
    """Combine video and narration audio into final scene"""
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        
        # Load video and audio
        video = VideoFileClip(str(video_file))
        audio = AudioFileClip(str(audio_file))
        
        # Ensure video matches audio duration
        if video.duration > audio.duration:
            # Trim video to match audio
            video = video.subclip(0, audio.duration)
        elif video.duration < audio.duration:
            # Extend video (loop or freeze last frame)
            # For now, just trim audio (not ideal)
            audio = audio.subclip(0, video.duration)
        
        # Combine
        final_video = video.set_audio(audio)
        
        # Save
        final_video.write_videofile(
            str(output_file),
            codec='libx264',
            audio_codec='aac'
        )
        
        # Cleanup
        video.close()
        audio.close()
        final_video.close()
        
        return True
        
    except ImportError:
        print("Error: moviepy not installed. Install with: pip install moviepy")
        return False
    except Exception as e:
        print(f"Error combining audio/video: {e}")
        return False

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'scenes'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scenes and narration index
    print("Loading scenes and narration...")
    scenes_data = load_merged_scenes()
    if not scenes_data:
        return
    
    narration_index = load_narration_index()
    scenes = scenes_data.get('scenes', [])
    
    print(f"Found {len(scenes)} scenes")
    print(f"Found {len(narration_index)} narration files")
    
    # Generate video for each scene
    video_files = []
    
    for i, scene in enumerate(scenes, 1):
        scene_id = scene.get('id', 'unknown')
        narration_info = narration_index.get(scene_id, {})
        
        if not narration_info.get('audio_file'):
            print(f"\n[{i}/{len(scenes)}] ⚠️  Scene {scene_id}: No narration file found")
            continue
        
        print(f"\n[{i}/{len(scenes)}] Processing scene: {scene_id}")
        
        # Generate video scene
        video_info = generate_video_scene(scene, narration_info, project_root, output_dir)
        video_files.append(video_info)
        
        # TODO: Actual video generation would happen here
        # For now, this is a template
    
    # Save video index
    index_file = output_dir / 'video_index.json'
    index_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(scenes),
            "video_files": len(video_files)
        },
        "video_files": video_files
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Processed {len(video_files)} scenes")
    print(f"✅ Saved index to {index_file}")
    print(f"\n📝 Next steps:")
    print(f"   1. Implement actual video generation (Runway/Stable Video/etc.)")
    print(f"   2. Run combine_scenes.py to create final movie")

if __name__ == "__main__":
    main()
