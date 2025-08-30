#!/usr/bin/env python3
"""
Simplified model comparison script for Task 2
Compares Basic Pitch with alternative approaches
"""

import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Import Basic Pitch
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict
import librosa
import crepe


def run_basic_pitch(audio_path):
    """Run Basic Pitch transcription"""
    print(f"  [Basic Pitch] Processing...")
    start = time.time()
    
    audio, sr = librosa.load(audio_path, sr=22050, mono=True)
    model_output, midi_data, note_events = predict(
        audio, sr,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        onset_threshold=0.5,
        frame_threshold=0.3
    )
    
    notes = []
    for note in note_events:
        notes.append({
            "pitch_midi": int(note[0]),
            "onset_time_s": float(note[1]),
            "offset_time_s": float(note[2]),
            "velocity": int(note[3] * 127) if len(note) > 3 else 64,
            "confidence": float(note[4]) if len(note) > 4 else 0.8
        })
    
    elapsed = time.time() - start
    return notes, elapsed


def run_crepe_onset(audio_path):
    """Run CREPE + onset detection"""
    print(f"  [CREPE+Onset] Processing...")
    start = time.time()
    
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    
    # Onset detection
    onset_envelope = librosa.onset.onset_strength(y=audio, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_envelope, sr=sr, backtrack=True
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    # CREPE pitch detection
    time_stamps, frequency, confidence, _ = crepe.predict(
        audio, sr, viterbi=True, step_size=10
    )
    
    # Convert to MIDI
    midi_pitches = librosa.hz_to_midi(frequency)
    
    notes = []
    for onset_time in onset_times:
        # Find closest time in CREPE
        idx = np.argmin(np.abs(time_stamps - onset_time))
        if confidence[idx] > 0.5:
            notes.append({
                "pitch_midi": int(round(midi_pitches[idx])),
                "onset_time_s": float(onset_time),
                "offset_time_s": float(onset_time + 0.5),
                "velocity": 64,
                "confidence": float(confidence[idx])
            })
    
    elapsed = time.time() - start
    return notes, elapsed


def run_spectral_analysis(audio_path):
    """Run spectral analysis method (simple baseline)"""
    print(f"  [Spectral] Processing...")
    start = time.time()
    
    audio, sr = librosa.load(audio_path, sr=22050, mono=True)
    
    # Onset detection
    onset_envelope = librosa.onset.onset_strength(y=audio, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_envelope, sr=sr
    )
    
    # Compute CQT for pitch
    C = np.abs(librosa.cqt(audio, sr=sr, fmin=librosa.note_to_hz('A0')))
    
    notes = []
    for onset_frame in onset_frames:
        if onset_frame < C.shape[1]:
            # Find peaks in spectrum
            spectrum = C[:, onset_frame]
            peaks = np.where(spectrum > np.max(spectrum) * 0.3)[0]
            
            for peak in peaks[:5]:  # Top 5 peaks (polyphony)
                midi_note = 21 + peak  # A0 = 21
                onset_time = librosa.frames_to_time(onset_frame, sr=sr)
                
                notes.append({
                    "pitch_midi": int(midi_note),
                    "onset_time_s": float(onset_time),
                    "offset_time_s": float(onset_time + 0.5),
                    "velocity": 64,
                    "confidence": 0.5
                })
    
    elapsed = time.time() - start
    return notes, elapsed


def compare_models(samples_dir="../task-01/samples"):
    """Run all models and compare"""
    
    samples_path = Path(samples_dir)
    sample_files = list(samples_path.glob("*.mp3"))
    
    results = []
    all_outputs = {}
    
    for sample_file in sample_files:
        sample_name = sample_file.stem
        print(f"\n{'='*50}")
        print(f"Processing: {sample_name}")
        print(f"{'='*50}")
        
        all_outputs[sample_name] = {}
        
        # Run each model
        models = {
            "basic_pitch": run_basic_pitch,
            "crepe_onset": run_crepe_onset,
            "spectral": run_spectral_analysis
        }
        
        for model_name, model_func in models.items():
            try:
                notes, elapsed = model_func(str(sample_file))
                
                # Save output
                output_dir = Path("outputs") / model_name
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_data = {
                    "model": model_name,
                    "sample": sample_name,
                    "notes": notes,
                    "metadata": {
                        "inference_time": elapsed,
                        "num_notes": len(notes)
                    }
                }
                
                with open(output_dir / f"{sample_name}.json", "w") as f:
                    json.dump(output_data, f, indent=2)
                
                all_outputs[sample_name][model_name] = notes
                
                results.append({
                    "sample": sample_name,
                    "model": model_name,
                    "num_notes": len(notes),
                    "time": elapsed,
                    "avg_confidence": np.mean([n["confidence"] for n in notes]) if notes else 0
                })
                
                print(f"    {model_name}: {len(notes)} notes in {elapsed:.2f}s")
                
            except Exception as e:
                print(f"    {model_name}: ERROR - {e}")
                results.append({
                    "sample": sample_name,
                    "model": model_name,
                    "num_notes": 0,
                    "time": 0,
                    "avg_confidence": 0
                })
    
    return pd.DataFrame(results), all_outputs


def calculate_agreement(all_outputs):
    """Calculate agreement between models"""
    
    agreement_results = []
    
    for sample_name, models in all_outputs.items():
        model_names = list(models.keys())
        
        for i, model1 in enumerate(model_names):
            for model2 in model_names[i+1:]:
                notes1 = models[model1]
                notes2 = models[model2]
                
                # Count matching notes (within 50ms and 1 semitone)
                matches = 0
                for n1 in notes1:
                    for n2 in notes2:
                        if (abs(n1["pitch_midi"] - n2["pitch_midi"]) <= 1 and
                            abs(n1["onset_time_s"] - n2["onset_time_s"]) <= 0.05):
                            matches += 1
                            break
                
                total = max(len(notes1), len(notes2))
                agreement = matches / total if total > 0 else 0
                
                agreement_results.append({
                    "sample": sample_name,
                    "model1": model1,
                    "model2": model2,
                    "agreement": agreement,
                    "matches": matches,
                    "total": total
                })
    
    return pd.DataFrame(agreement_results)


def create_plots(results_df, agreement_df):
    """Create comparison visualizations"""
    
    output_dir = Path("outputs/comparisons")
    output_dir.mkdir(exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Notes detected by model
    ax = axes[0, 0]
    sns.barplot(data=results_df, x="model", y="num_notes", hue="sample", ax=ax)
    ax.set_title("Notes Detected by Model")
    ax.set_ylabel("Number of Notes")
    
    # 2. Inference time
    ax = axes[0, 1]
    model_avg = results_df.groupby("model")["time"].mean().reset_index()
    sns.barplot(data=model_avg, x="model", y="time", ax=ax)
    ax.set_title("Average Inference Time")
    ax.set_ylabel("Time (seconds)")
    
    # 3. Confidence scores
    ax = axes[1, 0]
    sns.boxplot(data=results_df, x="model", y="avg_confidence", ax=ax)
    ax.set_title("Confidence Distribution")
    ax.set_ylabel("Average Confidence")
    
    # 4. Model agreement
    ax = axes[1, 1]
    if not agreement_df.empty:
        agreement_pivot = agreement_df.groupby(["model1", "model2"])["agreement"].mean().reset_index()
        agreement_matrix = agreement_pivot.pivot(index="model1", columns="model2", values="agreement")
        sns.heatmap(agreement_matrix, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax, vmin=0, vmax=1)
        ax.set_title("Model Agreement (% matching notes)")
    
    plt.tight_layout()
    plt.savefig(output_dir / "model_comparison.png", dpi=150)
    plt.show()
    
    print(f"\nPlots saved to {output_dir}")


def main():
    print("="*60)
    print("TASK 2: Model Comparison")
    print("="*60)
    
    # Run comparison
    results_df, all_outputs = compare_models()
    
    # Calculate agreement
    agreement_df = calculate_agreement(all_outputs)
    
    # Save results
    results_df.to_csv("outputs/comparison_results.csv", index=False)
    agreement_df.to_csv("outputs/model_agreement.csv", index=False)
    
    # Create visualizations
    create_plots(results_df, agreement_df)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\nAverage performance by model:")
    print(results_df.groupby("model")[["num_notes", "time", "avg_confidence"]].mean())
    
    print("\nModel agreement (average):")
    if not agreement_df.empty:
        for _, row in agreement_df.groupby(["model1", "model2"])["agreement"].mean().items():
            print(f"  {_[0]} vs {_[1]}: {row:.2%}")
    
    print("\n✓ Task 2 complete!")


if __name__ == "__main__":
    main()