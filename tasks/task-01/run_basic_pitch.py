#!/usr/bin/env python3
"""
Direct Basic Pitch transcription without subprocess
"""

import time
import json
from pathlib import Path

# Import Basic Pitch directly
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict_and_save

def transcribe_file(audio_path, output_directory):
    """Transcribe a single audio file"""
    print(f"Transcribing: {audio_path}")
    start_time = time.time()
    
    # Create output directory
    Path(output_directory).mkdir(parents=True, exist_ok=True)
    
    # Run Basic Pitch
    predict_and_save(
        [audio_path],
        output_directory,
        save_midi=True,
        save_model_outputs=True,
        save_notes=True
    )
    
    elapsed = time.time() - start_time
    
    # Count notes in the output
    midi_file = Path(output_directory) / f"{Path(audio_path).stem}_basic_pitch.mid"
    note_count = 0
    
    if midi_file.exists():
        try:
            import pretty_midi
            midi_data = pretty_midi.PrettyMIDI(str(midi_file))
            note_count = sum(len(inst.notes) for inst in midi_data.instruments)
        except Exception as e:
            print(f"Error counting notes: {e}")
    
    return {
        "file": str(audio_path),
        "time_seconds": elapsed,
        "note_count": note_count,
        "output_dir": str(output_directory)
    }

def main():
    samples = [
        ("tasks/task-01/samples/sample.mp3", "tasks/task-01/outputs/sample"),
        ("tasks/task-01/samples/live_piano.mp3", "tasks/task-01/outputs/live_piano"),
        ("tasks/task-01/samples/youtube_piano.mp3", "tasks/task-01/outputs/youtube_piano")
    ]
    
    results = []
    
    print("=" * 60)
    print("Basic Pitch Transcription - Task 1")
    print("=" * 60)
    
    for i, (input_file, output_dir) in enumerate(samples, 1):
        print(f"\n[{i}/3] {Path(input_file).name}")
        print("-" * 40)
        
        if not Path(input_file).exists():
            print(f"WARNING: {input_file} not found, skipping...")
            continue
        
        try:
            result = transcribe_file(input_file, output_dir)
            results.append(result)
            print(f"✓ Time: {result['time_seconds']:.2f}s")
            print(f"✓ Notes detected: {result['note_count']}")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "file": input_file,
                "error": str(e),
                "time_seconds": 0,
                "note_count": 0
            })
    
    # Save results
    with open("tasks/task-01/transcription_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"\n{Path(r['file']).name}:")
        print(f"  Time: {r['time_seconds']:.2f}s")
        print(f"  Notes: {r['note_count']}")
        if 'error' in r:
            print(f"  Error: {r['error']}")
    
    print("\n✓ Results saved to tasks/task-01/transcription_results.json")

if __name__ == "__main__":
    main()