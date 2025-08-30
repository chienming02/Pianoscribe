#!/usr/bin/env python3
"""
Simple piano transcription using librosa (fallback for Basic Pitch)
Since Basic Pitch has Python 3.12 compatibility issues with TensorFlow
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import librosa
import numpy as np
import pretty_midi
import soundfile as sf
from music21 import stream, note, tempo, metadata, meter
from scipy.signal import find_peaks


class SimplePianoTranscriber:
    def __init__(self, sample_rate=22050, hop_length=512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.frame_rate = sample_rate / hop_length
        
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio file to note events"""
        print(f"Loading audio from {audio_path}...")
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Compute CQT (Constant-Q Transform) for better frequency resolution
        print("Computing CQT...")
        C = np.abs(librosa.cqt(y, sr=sr, hop_length=self.hop_length, 
                               fmin=librosa.note_to_hz('A0'),
                               n_bins=88, bins_per_octave=12))
        
        # Convert to dB scale
        C_db = librosa.amplitude_to_db(C, ref=np.max)
        
        # Onset detection
        print("Detecting onsets...")
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, 
                                                  sr=sr, 
                                                  hop_length=self.hop_length,
                                                  units='frames')
        
        # Extract notes using peak picking on CQT
        notes = []
        for onset_frame in onset_frames:
            if onset_frame < C_db.shape[1]:
                # Get spectrum at onset
                spectrum = C_db[:, onset_frame]
                
                # Find peaks (potential notes)
                peaks, properties = find_peaks(spectrum, 
                                              height=-40,  # Minimum dB level
                                              distance=2)  # Minimum distance between peaks
                
                for peak_idx in peaks:
                    # Convert bin to MIDI note
                    midi_note = 21 + peak_idx  # A0 = 21
                    
                    # Estimate velocity from peak height
                    velocity = int(min(127, max(1, (properties['peak_heights'][list(peaks).index(peak_idx)] + 60) * 2)))
                    
                    # Estimate note duration (simple heuristic)
                    offset_frame = onset_frame + int(self.frame_rate * 0.5)  # Default 0.5s duration
                    
                    # Look for actual note offset
                    for check_frame in range(onset_frame + 1, min(onset_frame + int(self.frame_rate * 2), C_db.shape[1])):
                        if C_db[peak_idx, check_frame] < -50:  # Note has decayed
                            offset_frame = check_frame
                            break
                    
                    onset_time = librosa.frames_to_time(onset_frame, sr=sr, hop_length=self.hop_length)
                    offset_time = librosa.frames_to_time(offset_frame, sr=sr, hop_length=self.hop_length)
                    
                    notes.append({
                        'pitch_midi': int(midi_note),
                        'onset_time_s': float(onset_time),
                        'offset_time_s': float(offset_time),
                        'velocity': velocity,
                        'confidence': 0.5  # Fixed confidence for simple method
                    })
        
        # Sort by onset time
        notes.sort(key=lambda x: x['onset_time_s'])
        
        # Filter out overlapping notes on same pitch
        filtered_notes = []
        for note in notes:
            # Check if this note overlaps with existing notes
            overlap = False
            for existing in filtered_notes:
                if (existing['pitch_midi'] == note['pitch_midi'] and 
                    existing['onset_time_s'] <= note['onset_time_s'] < existing['offset_time_s']):
                    overlap = True
                    break
            if not overlap:
                filtered_notes.append(note)
        
        return {
            'notes': filtered_notes,
            'sample_rate': sr,
            'hop_length': self.hop_length
        }
    
    def to_midi(self, transcription: Dict, output_path: str):
        """Convert transcription to MIDI file"""
        midi = pretty_midi.PrettyMIDI()
        piano = pretty_midi.Instrument(program=0)  # Acoustic Grand Piano
        
        for note_event in transcription['notes']:
            note = pretty_midi.Note(
                velocity=note_event['velocity'],
                pitch=note_event['pitch_midi'],
                start=note_event['onset_time_s'],
                end=note_event['offset_time_s']
            )
            piano.notes.append(note)
        
        midi.instruments.append(piano)
        midi.write(output_path)
        print(f"MIDI saved to {output_path}")
    
    def to_musicxml(self, transcription: Dict, output_path: str):
        """Convert transcription to MusicXML file"""
        # Create a music21 stream
        s = stream.Stream()
        
        # Add metadata
        s.metadata = metadata.Metadata()
        s.metadata.title = "Piano Transcription"
        s.metadata.composer = "Auto-transcribed"
        
        # Add tempo marking
        s.append(tempo.MetronomeMark(number=120))
        s.append(meter.TimeSignature('4/4'))
        
        # Add notes
        for note_event in transcription['notes']:
            n = note.Note(midi=note_event['pitch_midi'])
            n.quarterLength = (note_event['offset_time_s'] - note_event['onset_time_s']) * 2  # Approximate
            n.offset = note_event['onset_time_s'] * 2  # Approximate offset in quarter notes
            n.volume.velocity = note_event['velocity']
            s.append(n)
        
        # Write to MusicXML
        s.write('musicxml', fp=output_path)
        print(f"MusicXML saved to {output_path}")
    
    def to_json(self, transcription: Dict, output_path: str):
        """Save transcription as JSON"""
        with open(output_path, 'w') as f:
            json.dump(transcription, f, indent=2)
        print(f"JSON saved to {output_path}")


def main():
    """Test the transcriber"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_transcriber.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_dir = Path(audio_file).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    base_name = Path(audio_file).stem
    
    # Create transcriber
    transcriber = SimplePianoTranscriber()
    
    # Transcribe
    print(f"Transcribing {audio_file}...")
    transcription = transcriber.transcribe(audio_file)
    print(f"Found {len(transcription['notes'])} notes")
    
    # Save outputs
    transcriber.to_midi(transcription, str(output_dir / f"{base_name}.mid"))
    transcriber.to_musicxml(transcription, str(output_dir / f"{base_name}.xml"))
    transcriber.to_json(transcription, str(output_dir / f"{base_name}.json"))
    
    print("Transcription complete!")


if __name__ == "__main__":
    main()