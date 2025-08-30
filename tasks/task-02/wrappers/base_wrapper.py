"""
Base wrapper class for all transcription models
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


class BaseTranscriptionWrapper:
    """Base class for transcription model wrappers"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        
    def load_model(self):
        """Load the model (to be implemented by subclasses)"""
        raise NotImplementedError
        
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio file to standardized note event format
        
        Returns:
            Dict with keys:
                - notes: List of note events
                - pedals: List of pedal events (if available)
                - tempo_curve: Tempo information (if available)
                - metadata: Model-specific metadata
        """
        raise NotImplementedError
        
    def to_standard_format(self, notes: List, pedals: Optional[List] = None) -> Dict:
        """Convert to standardized JSON format"""
        return {
            "model": self.model_name,
            "notes": [
                {
                    "id": f"{self.model_name}_{i}",
                    "pitch_midi": note.get("pitch_midi", note.get("pitch", 0)),
                    "onset_time_s": float(note.get("onset_time_s", note.get("start", 0))),
                    "offset_time_s": float(note.get("offset_time_s", note.get("end", 0))),
                    "velocity": int(note.get("velocity", 64)),
                    "confidence": float(note.get("confidence", 0.5)),
                    "model_provenance": [self.model_name]
                }
                for i, note in enumerate(notes)
            ],
            "pedals": pedals or [],
            "tempo_curve": [],
            "metadata": {
                "model": self.model_name,
                "timestamp": time.time()
            }
        }
    
    def save_output(self, transcription: Dict, output_path: str):
        """Save transcription to JSON file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(transcription, f, indent=2)
            
    def evaluate_against_ground_truth(self, predicted: Dict, ground_truth: Dict) -> Dict:
        """Compute evaluation metrics"""
        # Simple onset F1 calculation
        pred_onsets = {(n["pitch_midi"], round(n["onset_time_s"], 2)) 
                      for n in predicted["notes"]}
        true_onsets = {(n["pitch_midi"], round(n["onset_time_s"], 2)) 
                      for n in ground_truth["notes"]}
        
        tp = len(pred_onsets & true_onsets)
        fp = len(pred_onsets - true_onsets)
        fn = len(true_onsets - pred_onsets)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "onset_precision": precision,
            "onset_recall": recall,
            "onset_f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn
        }