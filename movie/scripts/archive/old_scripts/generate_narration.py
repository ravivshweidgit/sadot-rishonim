#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to generate narration (TTS) audio files from scene narration texts.
Uses Google TTS API or local TTS engine to create Hebrew voice narration.
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
    """Load merged scenes with narration texts"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    scenes_file = project_root / 'movie' / 'output' / 'scripts' / 'merged_scenes.json'
    
    if not scenes_file.exists():
        print(f"Error: {scenes_file} not found. Run merge_scenes_from_books.py first.")
        return None
    
    with open(scenes_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_tts_google(text, output_path, voice_name='he-IL-Standard-A'):
    """
    Generate TTS using Google Cloud Text-to-Speech API
    Requires: pip install google-cloud-texttospeech
    """
    try:
        from google.cloud import texttospeech
        
        # Initialize client
        client = texttospeech.TextToSpeechClient()
        
        # Configure synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configure voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="he-IL",
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        # Configure audio encoding
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,  # Normal speed
            pitch=0.0,  # Normal pitch
        )
        
        # Perform TTS
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Save audio file
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
        
        return True
        
    except ImportError:
        print("Error: google-cloud-texttospeech not installed.")
        print("Install with: pip install google-cloud-texttospeech")
        return False
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return False

def generate_tts_gtts(text, output_path):
    """
    Generate TTS using gTTS (Google Text-to-Speech) - free, no API key needed
    Requires: pip install gtts
    """
    try:
        from gtts import gTTS
        
        # Create TTS object
        tts = gTTS(text=text, lang='he', slow=False)
        
        # Save to file
        tts.save(str(output_path))
        
        return True
        
    except ImportError:
        print("Error: gtts not installed.")
        print("Install with: pip install gtts")
        return False
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return False

def generate_tts_elevenlabs(text, output_path, api_key=None):
    """
    Generate TTS using ElevenLabs API (high quality, requires API key)
    Requires: pip install elevenlabs
    """
    try:
        from elevenlabs import generate, save
        
        if not api_key:
            api_key = os.getenv('ELEVENLABS_API_KEY')
            if not api_key:
                print("Error: ElevenLabs API key not found.")
                print("Set ELEVENLABS_API_KEY environment variable or pass api_key parameter.")
                return False
        
        # Generate audio
        audio = generate(
            text=text,
            voice="Rachel",  # Hebrew voice (or choose another)
            model="eleven_multilingual_v2"
        )
        
        # Save audio file
        save(audio, str(output_path))
        
        return True
        
    except ImportError:
        print("Error: elevenlabs not installed.")
        print("Install with: pip install elevenlabs")
        return False
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return False

def generate_narration_for_scene(scene, output_dir, tts_method='gtts'):
    """Generate narration audio file for a single scene"""
    scene_id = scene.get('id', 'unknown')
    narration_text = scene.get('narration_text', '')
    
    if not narration_text:
        print(f"  ⚠️  Scene {scene_id}: No narration text")
        return None
    
    # Create output filename
    output_file = output_dir / f"{scene_id}_narration.mp3"
    
    # Generate TTS based on method
    print(f"  Generating narration for {scene_id}...")
    
    success = False
    if tts_method == 'gtts':
        success = generate_tts_gtts(narration_text, output_file)
    elif tts_method == 'google':
        success = generate_tts_google(narration_text, output_file)
    elif tts_method == 'elevenlabs':
        success = generate_tts_elevenlabs(narration_text, output_file)
    else:
        print(f"  ⚠️  Unknown TTS method: {tts_method}")
        return None
    
    if success:
        duration = scene.get('narration_duration_estimate', 0)
        print(f"    ✅ Saved: {output_file} (estimated {duration}s)")
        return {
            'scene_id': scene_id,
            'audio_file': str(output_file),
            'duration_estimate': duration,
            'text_length': len(narration_text)
        }
    else:
        return None

def main():
    """Main function"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / 'movie' / 'output' / 'narration'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load merged scenes
    print("Loading merged scenes...")
    scenes_data = load_merged_scenes()
    if not scenes_data:
        return
    
    scenes = scenes_data.get('scenes', [])
    print(f"Found {len(scenes)} scenes")
    
    # TTS method (can be 'gtts', 'google', or 'elevenlabs')
    tts_method = 'gtts'  # Default: free gTTS
    if len(sys.argv) > 1:
        tts_method = sys.argv[1]
    
    print(f"\nUsing TTS method: {tts_method}")
    print(f"Output directory: {output_dir}\n")
    
    # Generate narration for each scene
    narration_files = []
    for i, scene in enumerate(scenes, 1):
        print(f"[{i}/{len(scenes)}] Processing scene: {scene.get('id', 'unknown')}")
        result = generate_narration_for_scene(scene, output_dir, tts_method)
        if result:
            narration_files.append(result)
    
    # Save narration index
    index_file = output_dir / 'narration_index.json'
    index_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(scenes),
            "narration_files": len(narration_files),
            "tts_method": tts_method
        },
        "narration_files": narration_files
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Generated {len(narration_files)} narration files")
    print(f"✅ Saved index to {index_file}")
    
    # Calculate total duration
    total_duration = sum(f['duration_estimate'] for f in narration_files)
    print(f"📊 Total estimated narration duration: {total_duration}s ({total_duration/60:.1f} minutes)")

if __name__ == "__main__":
    main()
