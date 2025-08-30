# Design Document — Piano Video → High-Quality Sheet Music (Local-first, Quality-first)

## Project overview (one line)
A local-first desktop/web app that transcribes piano audio/video into high-quality engraved sheet music (MusicXML), with synced audio/MIDI playback and an interactive editor for manual corrections. Prioritize transcription **accuracy** (onsets/offsets, pedal, dynamics) and a pleasant UX for correction and preview.

---

## Goals & success criteria

### Primary goals
1. Produce the **most accurate** piano transcription feasible using open-source models + post-processing (quality > speed).  
2. Provide a UX where the user can **play the audio and watch the sheet highlight/sync**, and **edit** the transcription easily.  
3. Run locally on a developer laptop (CUDA-capable Legion 7i) for dev/testing; scale to RTX 3090 for higher accuracy and throughput.

### Success criteria (measurable)
- On MAESTRO-style benchmark tests (internal), achieve onset F1 ≥ 90% (practical target) and pedal detection F1 ≥ 75% with fine-tuning/ensemble.  
- For representative YouTube/live piano clips, produce a MusicXML that a pianist can turn into publishable notation with **≤ 20 minutes** manual correction for a 3-minute piece.  
- App provides synced playback with note-follow highlighting and basic in-editor note manipulation (change pitch, duration, tie, delete/add).

---

## High-level architecture

### Layers
1. **UI (frontend)** — web-based local UI (Electron or local web served + browser) with audio upload, job panel, score viewer (Verovio), playback controls, editor, and export.  
2. **Orchestration (backend service, local)** — lightweight REST/CLI orchestrator that runs pipeline steps (separation → transcription → post-process → export) and exposes progress/state for UI.  
3. **Transcription engines (pluggable)** — model wrappers for Basic Pitch, Onsets & Frames, and MT3 / ByteDance high-res model. Ensemble manager merges results.  
4. **Post-processing** — tempo-spline estimation, non-uniform quantization, hand-splitting, pedal inference, noise filtering, notation-level transformer heuristics.  
5. **Storage & caching** — local storage for intermediate artifacts (audio stems, model outputs, MIDI, MusicXML), with checksum-based caching.  
6. **Optional GPU manager** — config to run on laptop GPU or 3090; chunking support to handle long audio.

Diagram (conceptual):  
User UI ⇄ Orchestrator (REST) → [Demucs] → [MT3 / O&F / BasicPitch] → Post-process → MusicXML/MIDI → Verovio + Playback

---

## Components — responsibilities & design

### 1) Frontend (Local web/Electron)
- **Pages / panels**:
  - Project list / File manager
  - Upload/URL input (file or YouTube URL)
  - Job progress view (download → separation → model → post-process → export)
  - Score viewer with synced playback and piano-roll
  - Editor pane: note selection, pitch change, duration change, quantize dropdown, add/delete notes, split/merge hands, pedal toggle
  - Export panel (MusicXML, MIDI, PNG, PDF)
  - Settings (model selection, chunk length, VRAM hints)
- **Key UI behaviors**:
  - On playback, highlight the current note(s) on the score and piano-roll in real time.  
  - Allow “follow mode” (auto-scroll) and manual scroll.  
  - Have an “adjust tempo curve” control: user can tap tempo or edit control points.  
  - Undo/redo stack for editing.  
  - Visual indicators of model confidence for each note (low/medium/high) — allow filter to show only high-confidence notes for quick validation.
- **Rendering**: use **Verovio** for MusicXML → SVG rendering in browser. For local desktop, integrate Verovio in the Electron webview.

### 2) Orchestrator (local service)
- Lightweight REST API (or local CLI) to accept audio/video → start job and return job-id. UI polls or subscribes (websocket) to receive progress updates and intermediate artifacts.  
- Responsibilities: manage download (yt-dlp), audio extraction (ffmpeg), optional separation (Demucs), call transcription wrappers, call postprocesser, export MusicXML, store artifacts.  
- Expose endpoints:
  - POST /jobs (input: file or url + options) → returns job id
  - GET /jobs/{id}/status
  - GET /jobs/{id}/artifact/{type} (midi/musicxml/stem/waveform)
  - POST /jobs/{id}/edit (apply edits programmatically)
- Provide local filesystem persistence under project folder with structure: /projects/{project_id}/inputs, stems, models_out, midi, musicxml, renders.

### 3) Model wrappers (pluggable)
- **Basic requirements**:
  - Unified interface: `transcribe(audio_path, options) → timestamped note events + metadata (confidence per note, pedal events)`.  
  - Implement wrappers for: Basic Pitch (fast baseline), Onsets & Frames (magenta), MT3 (T5-based), ByteDance high-res (if feasible).  
  - Each wrapper must support chunked inference (e.g., windows with overlap) and return onset/offset with time resolution (ms) and velocity if available.
- **Ensemble manager**:
  - Accept outputs from multiple models and merge by rules:
    - Onset matching window (±30–50 ms) for voting.
    - If multiple models agree → adopt averaged onset/offset and high confidence.
    - Keep track of model provenance for each note for debugging.

### 4) Post-processing / Notation pipeline
- **Components**:
  - Tempo estimation: beat tracker → fit tempo spline (control points). Output tempo curve for non-uniform quantization.
  - Non-uniform quantization: quantize onsets to subdivisions given tempo curve; allow variable grid (e.g., 12/16/24/32 divisions).
  - Pedal inference: detect pedal via spectral/resonance heuristics and model output; produce sustain control events.
  - Hand-splitting: dynamic programming to assign notes to left/right hands minimizing implausible crossings and respecting ranges.
  - Merge/clean: remove spurious notes below duration/velocity threshold; merge near-duplicate notes; resolve overlapping same-pitch events into ties.
  - Notation transformer (optional higher-end): a model or deterministic heuristic that converts clean MIDI into notation-level tokens (beaming groups, stem directions, grace vs regular) to produce nicer engravings automatically.
- **Output**: high-quality MusicXML plus intermediate MIDI and JSON of note events for UI.

### 5) Playback & sync engine
- Accept both original audio and generated MIDI/oversampled MIDI with tempo-curves.  
- Provide sample-accurate mapping: for each note event in MusicXML, map to audio time (using model onset times and tempo curve) so UI can highlight correctly.  
- Support audio-only sync if user prefers (align MIDI to audio via cross-correlation).

### 6) Editor & persistence
- User edits are stored as patches on top of base MusicXML (delta-edit model) so original transcription remains available.  
- Provide export of final MusicXML and MIDI.  
- Undo/redo and export history.

---

## Models & algorithmic choices (quality-first)

### Priority stack (recommended)
1. **MT3** (primary quality model) — Transformer seq2seq that performs well on polyphony. Use as main engine in final version (3090).  
2. **ByteDance high-resolution piano model** (if accessible) — excellent for onset/offset precision and pedal. Use to improve pedal detection and micro-timing.  
3. **Onsets & Frames** — secondary baseline, good note-level baseline and useful to ensemble.  
4. **Basic Pitch** — fast baseline for quick tests and fallback.

### Ensemble & voting
- Ensemble MT3 + O&F + BasicPitch. Voting rules:
  - If MT3 provides a note and at least one other model agrees within ±30ms → accept with high confidence.  
  - If only BasicPitch has a note → label medium-low confidence and filterable.
- Average onset/offset times of agreeing notes to improve timing accuracy.

### Fine-tuning / domain adaptation
- Fine-tune MT3 or ByteDance model on MAESTRO v3 augmented with simulated YouTube-like conditions:
  - Reverb (IR), compression, background noise (crowd), phone ringtone overlays.  
- Use data augmentation pipeline during fine-tune: random SNR, tempo warps, pitch-shifts small ±1-2%.

### Post-process heuristics (must-haves)
- Tempo spline estimation prior to quantize.  
- Pedal detection and mapping to ties (sustain) vs played note lengths.  
- Hand-splitting via DP or heuristic.  
- Confidence thresholds and note filtering.

---

## UX specification (detailed)

### Primary UX flows
1. **Quick test (one-button)**: Upload → Transcribe → View score → Play original audio + highlight.  
2. **Iterative editing**: Play → pause at selection → choose note(s) → edit pitch/duration/tie/pedal → preview locally.  
3. **Model compare**: show alternative transcriptions (MT3 vs O&F vs Basic Pitch), toggle layers, and allow choosing notes from one to adopt into final.  
4. **Export**: final MusicXML, MIDI, and PNG/PDF. Option to open in MuseScore automatically.

### Editor features (must-have)
- Select note(s) → change pitch (up/down semitone), duration (choose quantization), delete/add note, split/merge voices, change staff (LH/RH), add pedal events.  
- Drag-to-quantize: drag a note horizontally to snap to grid or tempo curve.  
- Confidence overlay: color notes by confidence; ability to hide low-confidence notes.  
- Snapshots: versioning of manual edits.

### Visualization
- Score (main): rendered by Verovio, vertical scroll, auto-zoom.  
- Piano-roll (secondary): shows original model onsets/offsets and MIDI. Click a region to jump.  
- Waveform: audio waveform with markers for detected onsets; click to play.  
- A small “model info” panel: list of models used, processing times, and raw metrics (note counts, avg confidence).

### Performance expectations for UI
- Transcription is asynchronous: provide progress bars and estimated remaining (based on step latencies).  
- For 2–3 minute clips on a laptop GPU: expect 30–120s transcribe times depending on model. On 3090: expect 10–30s. (These are estimates; show as approximations in the UI.)

---

## Data formats & schemas

### Internal canonical note event (JSON)
```json
{
  "notes": [
    {
      "id": "uuid",
      "pitch_midi": 60,
      "onset_time_s": 12.345,
      "offset_time_s": 12.789,
      "velocity": 78,
      "confidence": 0.92,
      "model_provenance": ["mt3", "onsets_frames"]
    }
  ],
  "pedals": [
    {
      "type": "sustain",
      "start_time_s": 11.9,
      "end_time_s": 14.2,
      "confidence": 0.87
    }
  ],
  "tempo_curve": [
    { "time_s": 0.0, "bpm": 78.0 },
    { "time_s": 30.0, "bpm": 82.0 }
  ]
}
```

### Files produced
- Raw audio (wav)
- Piano stem (wav) if separation used
- MIDI (standard)
- MusicXML (primary deliverable)
- Note-events JSON (above)
- Render SVG/PNG for preview

---

## Dev plan & milestones (delivery-ready tasks)

### Phase 0 — Prep & environment
- Install/verify GPU drivers, Python env, FFmpeg, yt-dlp, MuseScore.  
- Create project skeleton and storage layout.  
- Implement orchestrator skeleton and simple UI scaffold.

### Phase 1 — MVP: Basic pipeline + UI (local)
- Implement ingestion (file + YouTube).  
- Implement Basic Pitch wrapper → produce MIDI → export MusicXML.  
- Integrate Verovio to display MusicXML and add audio playback + highlight by mapping MIDI times.  
- Implement simple editor: note deletion + pitch change + save/export.  
**Acceptance**: can upload 30s piano clip, transcribe, see score, play audio with cursor and perform basic edits.

### Phase 2 — Quality improvements & models
- Add Onsets & Frames wrapper.  
- Add MT3 wrapper (inference-only).  
- Implement ensemble manager and confidence voting.  
- Implement post-processing: tempo spline, quantize, hand-split, pedal inference.  
**Acceptance**: MT3 output plus ensemble produces visibly better transcription than Basic Pitch on benchmark clips.

### Phase 3 — UX polish & editing features
- Full editor (duration change, quantize, ties, pedals).  
- Undo/redo, versioning, snapshots.  
- Model compare toggle and "adopt from X model" feature.  
**Acceptance**: user can edit and produce final MusicXML with workflow time under target.

### Phase 4 — Testing, benchmarking & 3090 readiness
- Evaluate on MAESTRO / local clips and report metrics.  
- Add chunking and mixed precision options for 3090.  
- Document hardware configs & runtime expectations.  
**Acceptance**: documented performance numbers on laptop vs 3090.

### Phase 5 — Packaging & showcase
- Create README, example clips, and a Hugging Face Space demo (CPU-limited) or GitHub repo with instructions to run locally.  
**Acceptance**: repo contains runnable local demo and documentation.

---

## Testing & evaluation

### Quantitative
- Use MAESTRO dev/test for onset F1, note-with-offset F1, pedal F1, velocity correlation.  
- Provide a small set (5–10) of representative YouTube/live piano clips to measure end-user performance.

### Qualitative
- Blind pianists A/B test: give original audio + two transcriptions (A and B) without saying which model, ask which requires less editing for publishable score.

### UX testing
- Time-to-finish tasks: transcribe + fix a 1-min clip → target under 20 minutes for a reasonably difficult piece.

---

## Non-functional requirements

### Performance
- Configurable pipelines: quality vs speed toggle (e.g., “Fast”, “Accurate”, “Research”).  
- Chunking for long audio + stitch with overlap.

### Security & privacy
- All processing local by default (no cloud calls without explicit opt-in).  
- Clear storage folder per project; option to purge caches.

### Licensing & legal
- Use and redistribute only models under compatible OSS licenses. Document licenses.  
- Respect copyright: warn users when uploading copyrighted content and suggest local-only option.

---

## Operational notes & tips for the engineer/agent

- **Start with Basic Pitch** to get UI feedback quickly — it’s fast, reliable and helps the UX evolve while heavier models are integrated.  
- Make the system modular so different model wrappers can be swapped without UI changes.  
- Keep intermediate outputs and provenance to enable “adopt note from model X” in the editor.  
- Pedal is a big differentiator—invest time in pedal inference and visualization. Even a heuristic pedal detector (resonance + long notes) improves sheet readability enormously.  
- For tempo/rubato heavy music, prefer non-uniform tempo spline quantization before final notation conversion — avoid global fixed-grid quantization.

---

## Deliverables to hand off to Claude/Gemini CLI
- This design doc (the one above).  
- Example dataset: 5–10 representative piano clips (clean studio, live with crowd, youtube solo, noisy livestream).  
- Environment spec (Python version, condas, GPU driver versions).  
- Acceptance test list (MVP acceptance + quality acceptance above).

---

If you want me to also generate a task-by-task step list or a developer README tuned to your laptop/hardware, say so and I will produce it next.