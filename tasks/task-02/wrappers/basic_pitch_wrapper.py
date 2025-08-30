"""
Basic Pitch wrapper for standardized transcription
"""

import time
from pathlib import Path
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict
import numpy as np
import librosa

from base_wrapper import BaseTranscriptionWrapper


class BasicPitchWrapper(BaseTranscriptionWrapper):
    """Wrapper for Spotify's Basic Pitch model"""
    
    def __init__(self):
        super().__init__("basic_pitch")
        self.model_path = ICASSP_2022_MODEL_PATH
        
    def load_model(self):
        """Basic Pitch loads model on demand"""
        pass
        
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe using Basic Pitch"""
        print(f"[Basic Pitch] Transcribing {audio_path}...")
        start_time = time.time()
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=22050, mono=True)
        
        # Run Basic Pitch inference
        model_output, midi_data, note_events = predict(
            audio,
            sr,
            model_or_model_path=self.model_path,
            onset_threshold=0.5,
            frame_threshold=0.3,
            minimum_note_length=127.70,  # ~58ms at 22050 Hz
            minimum_frequency=27.5,  # A0
            maximum_frequency=4186.0,  # C8
        )
        
        # Convert note events to our format
        notes = []
        for note in note_events:
            notes.append({
                "pitch_midi": int(note[0]),
                "onset_time_s": float(note[1]),
                "offset_time_s": float(note[2]),
                "velocity": int(note[3] * 127) if len(note) > 3 else 64,
                "confidence": float(note[4]) if len(note) > 4 else 0.8
            })
        
        elapsed = time.time() - start_time
        print(f"[Basic Pitch] Found {len(notes)} notes in {elapsed:.2f}s")
        
        result = self.to_standard_format(notes)
        result["metadata"]["inference_time"] = elapsed
        return result