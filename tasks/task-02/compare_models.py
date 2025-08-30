#!/usr/bin/env python3
"""
Compare different piano transcription models on test samples
"""

import sys
import json
import time
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Add wrappers to path
sys.path.append(str(Path(__file__).parent / "wrappers"))

from basic_pitch_wrapper import BasicPitchWrapper
from crepe_onset_wrapper import CREPEOnsetWrapper
from piano_transformer_wrapper import PianoTransformerWrapper


def run_model_comparison(samples_dir="../task-01/samples", output_dir="outputs"):
    """Run all models on all samples and compare results"""
    
    # Initialize models
    models = {
        "basic_pitch": BasicPitchWrapper(),
        "crepe_onset": CREPEOnsetWrapper(),
        "piano_transformer": PianoTransformerWrapper()
    }
    
    # Load models that need initialization
    for name, model in models.items():
        if name == "piano_transformer":
            try:
                model.load_model()
            except Exception as e:
                print(f"Warning: Could not load {name}: {e}")
    
    # Get sample files
    samples_path = Path(samples_dir)
    sample_files = list(samples_path.glob("*.mp3"))
    
    print(f"Found {len(sample_files)} samples to process")
    
    # Results storage
    results = []
    
    # Process each sample with each model
    for sample_file in sample_files:
        sample_name = sample_file.stem
        print(f"\n{'='*60}")
        print(f"Processing: {sample_name}")
        print(f"{'='*60}")
        
        for model_name, model in models.items():
            try:
                # Run transcription
                transcription = model.transcribe(str(sample_file))
                
                # Save output
                output_path = Path(output_dir) / model_name / f"{sample_name}.json"
                model.save_output(transcription, str(output_path))
                
                # Store results
                results.append({
                    "sample": sample_name,
                    "model": model_name,
                    "num_notes": len(transcription["notes"]),
                    "inference_time": transcription["metadata"].get("inference_time", 0),
                    "avg_confidence": np.mean([n["confidence"] for n in transcription["notes"]]) 
                                     if transcription["notes"] else 0
                })
                
                print(f"  [{model_name}] Notes: {len(transcription['notes'])}, "
                      f"Time: {transcription['metadata'].get('inference_time', 0):.2f}s")
                
            except Exception as e:
                print(f"  [{model_name}] ERROR: {e}")
                results.append({
                    "sample": sample_name,
                    "model": model_name,
                    "num_notes": 0,
                    "inference_time": 0,
                    "avg_confidence": 0,
                    "error": str(e)
                })
    
    # Create results DataFrame
    df = pd.DataFrame(results)
    
    # Save results
    df.to_csv(Path(output_dir) / "comparison_results.csv", index=False)
    
    # Generate comparison plots
    create_comparison_plots(df, output_dir)
    
    return df


def create_comparison_plots(df, output_dir):
    """Create visualization comparing models"""
    
    output_path = Path(output_dir) / "comparisons"
    output_path.mkdir(exist_ok=True)
    
    # Set style
    sns.set_style("whitegrid")
    
    # 1. Note count comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Notes detected per model
    ax = axes[0]
    sns.barplot(data=df, x="model", y="num_notes", hue="sample", ax=ax)
    ax.set_title("Notes Detected by Model")
    ax.set_ylabel("Number of Notes")
    ax.tick_params(axis='x', rotation=45)
    
    # Inference time comparison
    ax = axes[1]
    sns.barplot(data=df, x="model", y="inference_time", ax=ax)
    ax.set_title("Inference Time by Model")
    ax.set_ylabel("Time (seconds)")
    ax.tick_params(axis='x', rotation=45)
    
    # Average confidence
    ax = axes[2]
    sns.barplot(data=df, x="model", y="avg_confidence", ax=ax)
    ax.set_title("Average Confidence by Model")
    ax.set_ylabel("Confidence Score")
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path / "model_comparison.png", dpi=150)
    plt.close()
    
    # 2. Sample-wise comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot_df = df.pivot(index="sample", columns="model", values="num_notes")
    pivot_df.plot(kind="bar", ax=ax)
    ax.set_title("Notes Detected per Sample")
    ax.set_ylabel("Number of Notes")
    ax.set_xlabel("Sample")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path / "sample_comparison.png", dpi=150)
    plt.close()
    
    print(f"\nPlots saved to {output_path}")


def analyze_model_agreement(output_dir="outputs"):
    """Analyze agreement between models on note detection"""
    
    output_path = Path(output_dir)
    samples = ["sample", "live_piano", "youtube_piano"]
    models = ["basic_pitch", "crepe_onset", "piano_transformer"]
    
    agreement_results = []
    
    for sample in samples:
        # Load all model outputs for this sample
        model_outputs = {}
        for model in models:
            json_path = output_path / model / f"{sample}.json"
            if json_path.exists():
                with open(json_path) as f:
                    model_outputs[model] = json.load(f)
        
        if len(model_outputs) < 2:
            continue
            
        # Compare note onsets between models (within 50ms window)
        for model1 in models:
            for model2 in models:
                if model1 >= model2 or model1 not in model_outputs or model2 not in model_outputs:
                    continue
                
                notes1 = model_outputs[model1]["notes"]
                notes2 = model_outputs[model2]["notes"]
                
                # Count matching notes
                matches = 0
                for n1 in notes1:
                    for n2 in notes2:
                        if (abs(n1["pitch_midi"] - n2["pitch_midi"]) <= 1 and
                            abs(n1["onset_time_s"] - n2["onset_time_s"]) <= 0.05):
                            matches += 1
                            break
                
                agreement = matches / max(len(notes1), len(notes2)) if notes1 or notes2 else 0
                
                agreement_results.append({
                    "sample": sample,
                    "model_pair": f"{model1}-{model2}",
                    "agreement": agreement,
                    "matching_notes": matches,
                    "total_notes_avg": (len(notes1) + len(notes2)) / 2
                })
    
    agreement_df = pd.DataFrame(agreement_results)
    agreement_df.to_csv(output_path / "model_agreement.csv", index=False)
    
    return agreement_df


def main():
    """Main execution"""
    print("="*60)
    print("Task 2: Model Comparison")
    print("="*60)
    
    # Run comparison
    results_df = run_model_comparison()
    
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(results_df.groupby("model")[["num_notes", "inference_time", "avg_confidence"]].mean())
    
    # Analyze agreement
    print("\n" + "="*60)
    print("MODEL AGREEMENT ANALYSIS")
    print("="*60)
    agreement_df = analyze_model_agreement()
    if not agreement_df.empty:
        print(agreement_df.groupby("model_pair")["agreement"].mean())
    
    print("\n✓ Task 2 comparison complete!")
    print("  Results saved to tasks/task-02/outputs/")
    print("  Plots saved to tasks/task-02/outputs/comparisons/")


if __name__ == "__main__":
    main()