You are an engineering assistant. I will hand you a design document (already saved in repo as `piano_transcription_design_doc.md`). Your job is to implement this piano-transcription project locally in a sequence of Tasks. **Work sequentially**: execute Task 1, produce the requested artifacts and a short report, then STOP. Do not automatically start Task 2. Wait for my explicit instruction to "Proceed to Task 2" (or similar). For each Task you must:

- Run the experiments / commands, produce artifacts (code, logs, output files), and a concise report (summary, key numbers, and any failures).  
- Commit code and artifacts to the repo under a clear path (`/tasks/task-01/`, `/tasks/task-02/`, etc.).  
- Provide exact commands I can run locally to reproduce your steps (one-line commands or small scripts).  
- If you encounter missing permissions, missing files, or environment constraints (GPU unavailable, missing dataset), STOP and report the exact missing item and how I can provide it.

Work with the following project constraints and goals: local-first development (Legion 7i; CUDA GPU available), later scale to RTX 3090 for heavy runs. Prioritize **accuracy over speed**. All processing should be local unless I explicitly ask for cloud. Use the design doc as normative.

---

## TASK 1 — Environment detection & baseline setup (mandatory)
**Goal:** establish a reproducible local environment and run a **baseline transcription** using Basic Pitch, to validate the pipeline end-to-end.

**Steps (execute now):**
1. Detect the system environment: OS, GPU model & driver, CUDA, Python version. Save the output to `tasks/task-01/env.json`.
2. Create a reproducible environment spec (conda or venv) and list of pip dependencies. Save as `tasks/task-01/requirements.txt` and `tasks/task-01/environment.yml` (if conda).
3. Choose or fetch 3 short test audio clips (≈20–60s each):
   - One clean studio piano recording,
   - One live piano clip (room/crowd noise),
   - One YouTube clip that contains piano (download with `yt-dlp`).
   Save them under `tasks/task-01/samples/`.
4. Run Basic Pitch transcription on the three clips (CPU or GPU if available). For each clip, produce:
   - MIDI file
   - MusicXML (or MusicXML-compatible export)
   - The raw note-event JSON with onset/offset/velocity/confidence
   Save outputs under `tasks/task-01/outputs/<clip-name>/`.
5. Produce a short report `tasks/task-01/report.md` containing:
   - System environment summary.
   - For each clip: run time, notes detected, any obvious failures (noise, false notes).
   - A short qualitative judgment: is Basic Pitch usable as a baseline? Where does it fail?
   - Attach (or point to) the generated files.
6. Commit all artifacts to git.

**Deliverables for Task 1:**
- `tasks/task-01/env.json`
- `tasks/task-01/requirements.txt`
- `tasks/task-01/samples/*`
- `tasks/task-01/outputs/*` (MIDI, MusicXML, note JSON)
- `tasks/task-01/report.md`
- Git commit + brief message

Stop after producing the above and output a concise summary (< 12 lines) and the git commit hash. Wait for my explicit confirmation to proceed to Task 2.

---

## TASK 2 — Compare candidate models (Basic Pitch vs Onsets & Frames vs MT3)
**Goal:** determine which model (or ensemble) gives the best accuracy on both MAESTRO and our representative clips.

**Do NOT start Task 2 until I say to proceed. When you do proceed, perform the following:**

**Steps:**
1. Implement lightweight wrapper scripts for Onsets & Frames and MT3 that produce the same standardized note-event JSON as Task 1.
2. Run all three models (Basic Pitch, O&F, MT3) on:
   - MAESTRO dev subset (if internet/download allowed) OR a local small labeled dataset (if provided).
   - The 3 sample clips from Task 1 (and 2–3 additional YouTube clips if helpful).
3. Compute metrics (for MAESTRO): onset F1, note-with-offset F1, pedal F1 (if model outputs pedal). Save evaluation CSVs under `tasks/task-02/eval/`.
4. For the YouTube/local clips (no ground truth), produce side-by-side MIDI+rendered MusicXML comparisons and a short qualitative summary per clip. Save under `tasks/task-02/comparisons/`.
5. Summarize tradeoffs: accuracy, speed, failure modes. Recommend which single model or ensemble to adopt for Phase 2.
6. Commit code, wrappers, and evaluation artifacts.

**Deliverables:**
- `tasks/task-02/wrappers/` (scripts)
- `tasks/task-02/eval/*.csv`
- `tasks/task-02/comparisons/*` (rendered PDFs or SVGs)
- `tasks/task-02/report.md` with recommendation and rationale.

Stop when done and present a concise summary and git commit hash. Wait for my instruction to proceed.

---

## TASK 3 — Implement ensemble and post-processing (tempo spline, non-uniform quantize, pedal inference, hand-splitting)
**Goal:** build the post-processing stack and an ensemble-merging strategy to improve final notation quality.

**(Run only when instructed to proceed)**

**Steps:**
1. Implement an ensemble merger that ingests multiple model JSON outputs and produces a merged note-event JSON with confidence scores and provenance.
2. Implement tempo-spline estimation and non-uniform quantization. Provide a script that takes note events + raw audio and outputs quantized note events and a tempo curve.
3. Implement pedal inference (heuristic + optional model) and hand-splitting (DP). Integrate into the post-processing pipeline.
4. Run this pipeline on the earlier test clips and produce MusicXML + rendered scores. Save under `tasks/task-03/outputs/`.
5. Produce a before/after report with metrics (if MAESTRO) and qualitative comparisons for YouTube clips.
6. Commit code and artifacts.

**Deliverables:** code, scripts, outputs, `tasks/task-03/report.md`.

Stop and report summary + commit hash.

---

## TASK 4 — Local interactive UI prototype (Verovio + audio sync + editor basics)
**Goal:** deliver a localhost web UI where a user can upload audio, run the chosen pipeline, view the rendered MusicXML with Verovio, playback audio with synchronized highlighting, and make simple edits (delete/change pitch/duration).

**(Run only when instructed to proceed)**

**Requirements:**
- UI served locally (Gradio/Electron/Flask + static front-end allowed). No public hosting required.
- The UI should call the orchestrator endpoints (from earlier) and display job progress.
- Provide an editor that can apply simple edits stored as deltas and re-render the MusicXML.
- Save a short demo video (screen capture) showing upload → transcribe → play → edit → export. Store under `tasks/task-04/`.

Stop and report summary + commit hash.

---

## TASK 5 — 3090 tuning & optional fine-tuning plan
**Goal:** prepare scripts and documentation to move heavy inference / fine-tuning to an RTX 3090, and, if desired, fine-tune MT3 or ByteDance model on augmented MAESTRO.

**(Run only when instructed to proceed)**

**Steps:**
1. Provide exact command-line options and config changes to enable FP16, batch size, and chunking optimized for 3090. Save under `tasks/task-05/3090-config/`.
2. If fine-tuning is desired, provide a detailed training recipe: dataset splits, augmentations, hyperparams, expected GPU hours, and checkpoints. Do NOT start long runs without my explicit go-ahead.
3. Provide scripts to run mixed-precision inference and a sample benchmark harness to compare laptop vs 3090 runtime.

Deliverables: config files, training recipe markdown, benchmark scripts. Stop and report summary.

---

## Additional constraints & notes for the agent
- Keep everything local by default. Document any internet downloads and require confirmation if internet access is needed to fetch datasets.  \n- Prefer accuracy: where tradeoffs exist, choose the path that improves transcription quality.  \n- Keep outputs human-readable. Provide a short README per task explaining how to reproduce results locally (commands to run).  \n- After each Task, pause and wait for my explicit instruction to continue.\n\nProceed: start Task 1 now.\n```

---
