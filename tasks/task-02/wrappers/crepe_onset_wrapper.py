"""
CREPE + Onset Detection wrapper (alternative to Onsets & Frames)
Uses CREPE for pitch detection and librosa for onset detection
"""

import time
import numpy as np
import librosa
import crepe
from scipy.signal import find_peaks

from base_wrapper import BaseTranscriptionWrapper


class CREPEOnsetWrapper(BaseTranscriptionWrapper):
    """Wrapper combining CREPE pitch detection with onset detection"""
    
    def __init__(self):
        super().__init__("crepe_onset")
        self.hop_length = 512
        self.sr = 22050
        
    def load_model(self):
        """CREPE loads model on demand"""
        pass
        
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe using CREPE + onset detection"""
        print(f"[CREPE+Onset] Transcribing {audio_path}...")
        start_time = time.time()
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        
        # Onset detection
        print("[CREPE+Onset] Detecting onsets...")
        onset_envelope = librosa.onset.onset_strength(
            y=audio, sr=sr, hop_length=self.hop_length
        )
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_envelope,
            sr=sr,
            hop_length=self.hop_length,
            backtrack=True
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=self.hop_length)
        
        # CREPE pitch detection
        print("[CREPE+Onset] Detecting pitches with CREPE...")
        time_stamps, frequency, confidence, activation = crepe.predict(
            audio, sr, viterbi=True, step_size=self.hop_length/sr*1000
        )
        
        # Convert frequency to MIDI
        midi_pitches = librosa.hz_to_midi(frequency)
        
        # Extract notes at onset times
        notes = []
        for onset_idx, onset_time in enumerate(onset_times):
            # Find closest time stamp in CREPE output
            time_idx = np.argmin(np.abs(time_stamps - onset_time))
            
            if confidence[time_idx] > 0.5:  # Confidence threshold
                # Estimate note duration (to next onset or 0.5s default)
                if onset_idx < len(onset_times) - 1:
                    duration = min(onset_times[onset_idx + 1] - onset_time, 2.0)
                else:
                    duration = 0.5
                
                notes.append({
                    "pitch_midi": int(round(midi_pitches[time_idx])),
                    "onset_time_s": float(onset_time),
                    "offset_time_s": float(onset_time + duration),
                    "velocity": 64,  # Default velocity
                    "confidence": float(confidence[time_idx])
                })
        
        # Filter out duplicate/overlapping notes
        filtered_notes = []
        for note in notes:
            is_duplicate = False
            for existing in filtered_notes:
                if (abs(existing["pitch_midi"] - note["pitch_midi"]) <= 1 and
                    abs(existing["onset_time_s"] - note["onset_time_s"]) < 0.05):
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_notes.append(note)
        
        elapsed = time.time() - start_time
        print(f"[CREPE+Onset] Found {len(filtered_notes)} notes in {elapsed:.2f}s")
        
        result = self.to_standard_format(filtered_notes)
        result["metadata"]["inference_time"] = elapsed
        return result