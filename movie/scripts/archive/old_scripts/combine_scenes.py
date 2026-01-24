#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to combine all scene videos and narrations into final movie.
Creates a continuous movie with synchronized narration from both books.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def load_video_index():
    """Load video index"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    index_file = project_root / 'movie' / 'output' / 'scenes' / 'video_index.json'
    
    if not index_file.exists():
        print(f"Error: {index_file} not found. Run generate_video.py first.")
        return None
    
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_timeline_movie():
    """Load timeline movie (preferred - chronological order)"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    timeline_file = project_root / 'movie' / 'output' / 'scripts' / 'timeline_movie.json'
    
    if timeline_file.exists():
        with open(timeline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_merged_scenes():
    """Load merged scenes as fallback"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    scenes_file = project_root / 'movie' / 'output' / 'scripts' / 'merged_scenes.json'
    
    if scenes_file.exists():
        with open(scenes_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_narration_index():
    """Load narration index"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    index_file = project_root / 'movie' / 'output' / 'narration' / 'narration_index.json'
    
    if not index_file.exists():
        print(f"Error: {index_file} not found. Run generate_narration.py first.")
        return None
    
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def combine_videos(video_files, output_file, transitions=True):
    """Combine multiple video files into one"""
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        clips = []
        for video_file in video_files:
            if not Path(video_file).exists():
                print(f"  ⚠️  Video file not found: {video_file}")
                continue
            
            clip = VideoFileClip(str(video_file))
            clips.append(clip)
        
        if not clips:
            print("Error: No video clips to combine")
            return False
        
        # Concatenate clips
        if transitions:
            # Add crossfade transitions between clips
            final_clip = concatenate_videoclips(clips, method="compose")
        else:
            final_clip = concatenate_videoclips(clips)
        
        # Write final video
        final_clip.write_videofile(
            str(output_file),
            codec='libx264',
            audio_codec='aac',
            fps=24
        )
        
        # Cleanup
        for clip in clips:
            clip.close()
        final_clip.close()
        
        return True
        
    except ImportError:
        print("Error: moviepy not installed. Install with: pip install moviepy")
        return False
    except Exception as e:
        print(f"Error combining videos: {e}")
        return False

def combine_audio(audio_files, output_file):
    """Combine multiple audio files into one"""
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        
        clips = []
        for audio_file in audio_files:
            if not Path(audio_file).exists():
                print(f"  ⚠️  Audio file not found: {audio_file}")
                continue
            
            clip = AudioFileClip(str(audio_file))
            clips.append(clip)
        
        if not clips:
            print("Error: No audio clips to combine")
            return False
        
        # Concatenate clips
        final_audio = concatenate_audioclips(clips)
        
        # Write final audio
        final_audio.write_audiofile(str(output_file))
        
        # Cleanup
        for clip in clips:
            clip.close()
        final_audio.close()
        
        return True
        
    except ImportError:
        print("Error: moviepy not installed. Install with: pip install moviepy")
        return False
    except Exception as e:
        print(f"Error combining audio: {e}")
        return False

def combine_final_movie(video_file, audio_file, output_file):
    """Combine final video with narration audio"""
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        
        # Load video and audio
        video = VideoFileClip(str(video_file))
        audio = AudioFileClip(str(audio_file))
        
        # Ensure durations match
        if video.duration != audio.duration:
            print(f"  ⚠️  Duration mismatch: video={video.duration}s, audio={audio.duration}s")
            # Use shorter duration
            min_duration = min(video.duration, audio.duration)
            video = video.subclip(0, min_duration)
            audio = audio.subclip(0, min_duration)
        
        # Combine
        final_video = video.set_audio(audio)
        
        # Write final movie
        final_video.write_videofile(
            str(output_file),
            codec='libx264',
            audio_codec='aac',
            fps=24
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
        print(f"Error creating final movie: {e}")
        return False

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'final'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to load timeline movie first (chronological order)
    print("Loading timeline movie (chronological order)...")
    timeline_data = load_timeline_movie()
    
    if timeline_data:
        print("✅ Using chronological timeline from both books")
        scenes_order = timeline_data.get('timeline', [])
        use_timeline = True
    else:
        print("⚠️  Timeline not found, using merged scenes order")
        # Fallback to merged scenes
        scenes_data = load_merged_scenes()
        if scenes_data:
            scenes_order = scenes_data.get('scenes', [])
            use_timeline = False
        else:
            print("Error: No scene data found")
            return
    
    # Load indices
    print("Loading video and narration indices...")
    video_index = load_video_index()
    narration_index = load_narration_index()
    
    if not video_index or not narration_index:
        return
    
    # Create lookups
    video_lookup = {item['scene_id']: item for item in video_index.get('video_files', [])}
    narration_lookup = {item['scene_id']: item for item in narration_index.get('narration_files', [])}
    
    # Get file paths in chronological order
    video_files = []
    audio_files = []
    
    for scene in scenes_order:
        scene_id = scene.get('id', 'unknown')
        video_info = video_lookup.get(scene_id)
        narration_info = narration_lookup.get(scene_id)
        
        # Get video file
        if video_info and video_info.get('video_file'):
            video_file = video_info['video_file']
            if Path(video_file).exists():
                video_files.append(video_file)
            else:
                print(f"  ⚠️  Video file not found for scene: {scene_id}")
        else:
            print(f"  ⚠️  Video info not found for scene: {scene_id}")
        
        # Get audio file
        if narration_info and narration_info.get('audio_file'):
            audio_file = narration_info['audio_file']
            if Path(audio_file).exists():
                audio_files.append(audio_file)
            else:
                print(f"  ⚠️  Audio file not found for scene: {scene_id}")
        else:
            print(f"  ⚠️  Narration info not found for scene: {scene_id}")
    
    print(f"\n📹 Found {len(video_files)} video files")
    print(f"🔊 Found {len(audio_files)} audio files")
    
    if not video_files or not audio_files:
        print("Error: Need both video and audio files to create movie")
        return
    
    # Step 1: Combine all videos
    print("\n🎬 Step 1: Combining video scenes...")
    combined_video = output_dir / 'combined_video.mp4'
    if combine_videos(video_files, combined_video):
        print(f"  ✅ Combined video saved: {combined_video}")
    else:
        print("  ❌ Failed to combine videos")
        return
    
    # Step 2: Combine all narrations
    print("\n🔊 Step 2: Combining narration audio...")
    combined_audio = output_dir / 'combined_narration.mp3'
    if combine_audio(audio_files, combined_audio):
        print(f"  ✅ Combined audio saved: {combined_audio}")
    else:
        print("  ❌ Failed to combine audio")
        return
    
    # Step 3: Combine video and audio into final movie
    print("\n🎞️  Step 3: Creating final movie...")
    final_movie = output_dir / 'movie_metula_1900_1921.mp4'
    if combine_final_movie(combined_video, combined_audio, final_movie):
        print(f"\n✅ Final movie created: {final_movie}")
        
        # Get duration
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(str(final_movie))
            duration = clip.duration
            clip.close()
            print(f"📊 Movie duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
        except:
            pass
    else:
        print("  ❌ Failed to create final movie")

if __name__ == "__main__":
    main()
