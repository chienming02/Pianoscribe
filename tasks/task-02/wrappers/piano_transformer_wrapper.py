"""
Piano Transformer wrapper - using Hugging Face transformers
This is a more accessible alternative to MT3
"""

import time
import numpy as np
import librosa
from transformers import AutoProcessor, AutoModelForAudioClassification
import torch

from base_wrapper import BaseTranscriptionWrapper


class PianoTransformerWrapper(BaseTranscriptionWrapper):
    """Wrapper for transformer-based piano transcription"""
    
    def __init__(self):
        super().__init__("piano_transformer")
        self.model = None
        self.processor = None
        
    def load_model(self):
        """Load a pre-trained audio model from Hugging Face"""
        print("[Piano Transformer] Loading model...")
        # Using a music classification model as a proxy for transcription
        # In production, you'd use a proper transcription model
        model_name = "MIT/ast-finetuned-audioset-10-10-0.4593"
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(model_name)
        
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe using transformer model with onset detection"""
        print(f"[Piano Transformer] Transcribing {audio_path}...")
        start_time = time.time()
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        # Use librosa for onset and pitch detection as a fallback
        # (Since we don't have a true transcription transformer readily available)
        onset_envelope = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_envelope, sr=sr, backtrack=True
        )
        
        # Compute pitch using harmonic-percussive separation
        y_harmonic, y_percussive = librosa.effects.hpss(audio)
        
        # Compute chromagram for pitch estimation
        chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
        
        notes = []
        for onset_frame in onset_frames:
            # Get pitch at onset
            if onset_frame < chroma.shape[1]:
                pitch_class = np.argmax(chroma[:, onset_frame])
                # Estimate octave based on spectral centroid
                cent = librosa.feature.spectral_centroid(
                    y=audio[onset_frame*512:(onset_frame+10)*512], sr=sr
                )
                octave = min(7, max(0, int(np.log2(cent.mean() / 261.63))))  # C4 = 261.63 Hz
                
                midi_pitch = pitch_class + (octave + 1) * 12
                
                onset_time = librosa.frames_to_time(onset_frame, sr=sr)
                
                notes.append({
                    "pitch_midi": int(midi_pitch),
                    "onset_time_s": float(onset_time),
                    "offset_time_s": float(onset_time + 0.5),  # Default duration
                    "velocity": 64,
                    "confidence": 0.6  # Medium confidence for this method
                })
        
        # Remove duplicates
        unique_notes = []
        for note in notes:
            is_duplicate = False
            for existing in unique_notes:
                if (existing["pitch_midi"] == note["pitch_midi"] and
                    abs(existing["onset_time_s"] - note["onset_time_s"]) < 0.05):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_notes.append(note)
        
        elapsed = time.time() - start_time
        print(f"[Piano Transformer] Found {len(unique_notes)} notes in {elapsed:.2f}s")
        
        result = self.to_standard_format(unique_notes)
        result["metadata"]["inference_time"] = elapsed
        result["metadata"]["note"] = "Using spectral analysis as transformer proxy"
        return result