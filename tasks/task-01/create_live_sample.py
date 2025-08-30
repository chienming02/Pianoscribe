#!/usr/bin/env python3
"""
Create a 'live' piano sample by adding room noise and reverb to existing sample
"""

import numpy as np
import librosa
import soundfile as sf
from scipy import signal
import os

def add_room_noise_and_reverb(input_file, output_file):
    """Add reverb and background noise to simulate live recording"""
    print(f"Loading {input_file}...")
    y, sr = librosa.load(input_file, sr=None)
    
    # Generate room noise (pink noise)
    print("Generating room noise...")
    noise_level = 0.005  # Low level background noise
    pink_noise = np.random.randn(len(y))
    # Apply 1/f filter for pink noise
    b, a = signal.butter(1, 100.0 / (sr/2), btype='low')
    pink_noise = signal.filtfilt(b, a, pink_noise)
    pink_noise = pink_noise * noise_level
    
    # Add subtle crowd/room sounds (very low frequency rumble)
    rumble = np.sin(2 * np.pi * 50 * np.arange(len(y)) / sr) * 0.001
    
    # Create simple reverb using delays
    print("Adding reverb...")
    reverb = np.zeros_like(y)
    delays = [int(0.02 * sr), int(0.05 * sr), int(0.1 * sr)]  # Early reflections
    gains = [0.3, 0.2, 0.1]
    
    for delay, gain in zip(delays, gains):
        if delay < len(y):
            reverb[delay:] += y[:-delay] * gain
    
    # Mix everything
    print("Mixing audio...")
    output = y + reverb + pink_noise + rumble
    
    # Add slight compression to simulate room acoustics
    output = np.tanh(output * 0.8) / 0.8
    
    # Normalize
    output = output / np.max(np.abs(output)) * 0.95
    
    print(f"Saving to {output_file}...")
    sf.write(output_file, output, sr)
    print("Done!")
    
    return output_file

def trim_youtube_sample(input_file, output_file, start_sec=60, duration=30):
    """Trim the YouTube sample to a shorter clip"""
    print(f"Loading {input_file}...")
    y, sr = librosa.load(input_file, sr=None, offset=start_sec, duration=duration)
    
    print(f"Saving trimmed version to {output_file}...")
    sf.write(output_file, y, sr)
    return output_file

if __name__ == "__main__":
    # Create live sample from existing clean sample
    clean_sample = "tasks/task-01/samples/sample.mp3"
    live_output = "tasks/task-01/samples/live_piano.mp3"
    
    if os.path.exists(clean_sample):
        add_room_noise_and_reverb(clean_sample, live_output)
    
    # Process YouTube sample if it exists
    youtube_webm = "tasks/task-01/samples/youtube_piano.webm"
    if os.path.exists(youtube_webm):
        print("\nProcessing YouTube sample...")
        # Convert webm to wav first
        y, sr = librosa.load(youtube_webm, sr=None)
        youtube_output = "tasks/task-01/samples/youtube_piano.mp3"
        # Take 30 seconds from the middle
        start = min(60, len(y) // sr // 2)
        y_trimmed = y[start*sr:(start+30)*sr]
        sf.write(youtube_output, y_trimmed, sr)
        print(f"YouTube sample saved to {youtube_output}")