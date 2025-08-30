#!/usr/bin/env python3
"""
Play MIDI file or convert to audio
"""

import sys
from pathlib import Path
import pretty_midi
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play

def midi_to_audio(midi_path, output_path=None):
    """Convert MIDI to audio using pretty_midi's synthesize"""
    print(f"Loading MIDI: {midi_path}")
    midi_data = pretty_midi.PrettyMIDI(midi_path)
    
    # Synthesize audio at 44.1kHz
    print("Synthesizing audio...")
    audio = midi_data.synthesize(fs=44100)
    
    # Normalize audio
    audio = audio / np.abs(audio).max()
    
    if output_path:
        print(f"Saving audio to: {output_path}")
        sf.write(output_path, audio, 44100)
    
    return audio

def play_midi_file(midi_path):
    """Play MIDI file by converting to audio first"""
    # Convert to temp WAV
    temp_wav = Path(midi_path).parent / "temp_playback.wav"
    audio = midi_to_audio(midi_path, str(temp_wav))
    
    # Play using pydub
    print("Playing audio...")
    audio_segment = AudioSegment.from_wav(str(temp_wav))
    play(audio_segment)
    
    # Clean up
    temp_wav.unlink()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_midi.py <midi_file> [output_wav]")
        sys.exit(1)
    
    midi_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Convert to audio file
        output_file = sys.argv[2]
        midi_to_audio(midi_file, output_file)
        print(f"Audio saved to: {output_file}")
    else:
        # Just play it
        play_midi_file(midi_file)