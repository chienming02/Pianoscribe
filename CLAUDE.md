# Pianoscribe Project Memory

## Project Goal
Local-first, quality-first piano transcription system converting piano audio/video to high-quality sheet music (MusicXML).

## Task 1 Progress Summary

### ✅ Completed Steps:
1. **Environment Setup**
   - Detected: Windows 10/11, RTX 4060 (8GB), Python 3.12.7
   - Initial issue: Python 3.12 incompatible with TensorFlow <2.15 (needed by Basic Pitch)
   - **RESOLVED**: Created conda environment with Python 3.11 (`pianoscribe`)
   - Successfully installed Basic Pitch in conda env

2. **Sample Preparation**
   - Clean studio: `sample.mp3` (user provided)
   - Live with noise: `live_piano.mp3` (created by adding reverb/noise to clean sample)
   - YouTube: `youtube_piano.mp3` (La Campanella, 30s excerpt)
   - All samples in `tasks/task-01/samples/`

3. **Basic Pitch Transcription**
   - Successfully ran on `sample.mp3` → MIDI created
   - User noted: "The MIDI extracted is kinda horrible" (EXPECTED - needs MT3 + post-processing)
   - Created scripts for batch processing all samples

### 🔧 Technical Resolutions:
- **Python compatibility**: Solved with conda env (Python 3.11)
- **ffmpeg missing**: User installed to C:\ffmpeg, added to PATH
- **Basic Pitch access**: Works via conda environment activation

### 📊 Quality Assessment:
- Basic Pitch alone: ~70-80% accuracy (poor polyphony, no pedal)
- Target: 90%+ accuracy (requires MT3 ensemble in Task 2)
- Current output issues:
  - Missing/ghost notes
  - Poor timing
  - No pedal detection
  - Bad polyphonic separation

### 📝 Next Steps (Task 1 completion):
1. Run Basic Pitch on remaining samples (live, YouTube)
2. Generate MusicXML exports
3. Write comprehensive report
4. Commit all artifacts

### 🚀 Future Tasks Preview:
- **Task 2**: Add MT3 + Onsets&Frames (dramatic quality improvement)
- **Task 3**: Post-processing (tempo correction, quantization, pedal)
- **Task 4**: Interactive UI with Verovio
- **Task 5**: RTX 3090 optimization

## Key Commands:
```bash
# Activate environment
conda activate pianoscribe

# Run Basic Pitch
basic-pitch tasks/task-01/outputs/[sample_name] tasks/task-01/samples/[sample].mp3

# Or use Python script
python tasks/task-01/run_basic_pitch.py
```

## Important Files:
- Environment info: `tasks/task-01/env.json`
- Transcription scripts: `tasks/task-01/run_basic_pitch.py`
- Samples: `tasks/task-01/samples/*.mp3`
- Outputs: `tasks/task-01/outputs/*/`
