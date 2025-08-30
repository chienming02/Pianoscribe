#!/usr/bin/env python3
"""
Run Basic Pitch transcription on all samples and measure time
"""

import subprocess
import time
import os
from pathlib import Path

def run_basic_pitch(input_file, output_dir):
    """Run Basic Pitch on a single file"""
    start_time = time.time()
    
    # Make sure output dir exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Run Basic Pitch
    cmd = ["basic-pitch", output_dir, input_file]
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    elapsed = time.time() - start_time
    
    # Count notes in MIDI file if it exists
    midi_file = Path(output_dir) / (Path(input_file).stem + "_basic_pitch.mid")
    note_count = "N/A"
    
    if midi_file.exists():
        try:
            import pretty_midi
            midi_data = pretty_midi.PrettyMIDI(str(midi_file))
            note_count = sum(len(inst.notes) for inst in midi_data.instruments)
        except:
            pass
    
    return {
        "file": input_file,
        "time_seconds": elapsed,
        "note_count": note_count,
        "success": result.returncode == 0,
        "stderr": result.stderr if result.stderr else None
    }

def main():
    samples = [
        ("tasks/task-01/samples/sample.mp3", "tasks/task-01/outputs/sample"),
        ("tasks/task-01/samples/live_piano.mp3", "tasks/task-01/outputs/live_piano"),
        ("tasks/task-01/samples/youtube_piano.mp3", "tasks/task-01/outputs/youtube_piano")
    ]
    
    results = []
    
    print("=" * 60)
    print("Running Basic Pitch Transcriptions")
    print("=" * 60)
    
    for i, (input_file, output_dir) in enumerate(samples, 1):
        print(f"\n[{i}/3] Processing: {Path(input_file).name}")
        print("-" * 40)
        
        if not os.path.exists(input_file):
            print(f"WARNING: {input_file} not found, skipping...")
            continue
        
        result = run_basic_pitch(input_file, output_dir)
        results.append(result)
        
        print(f"✓ Time: {result['time_seconds']:.2f}s")
        print(f"✓ Notes detected: {result['note_count']}")
        if result['stderr']:
            print(f"⚠ Warnings: {result['stderr'][:100]}...")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for r in results:
        print(f"\n{Path(r['file']).name}:")
        print(f"  - Time: {r['time_seconds']:.2f}s")
        print(f"  - Notes: {r['note_count']}")
        print(f"  - Success: {'Yes' if r['success'] else 'No'}")
    
    # Save results to JSON
    import json
    with open("tasks/task-01/transcription_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to tasks/task-01/transcription_results.json")

if __name__ == "__main__":
    main()