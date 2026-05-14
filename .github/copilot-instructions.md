# Copilot instructions for GuitarAudioTune

This file gives repository-specific guidance for future Copilot CLI sessions and AI assistants. Keep it concise and focused on commands, architecture, and repo conventions.

---

## Build, test, and lint commands

Backend (Flask, Python)
- Use Poetry for dependency management and running commands:
  - cd backend
  - poetry install                # installs from pyproject.toml
  - To add a dependency: `poetry add <dependency-name>`
  - To run a one-off command in the virtualenv: `poetry run <command>`
- Common commands (using Poetry):
  - Install dependencies: poetry install
  - Add a package: poetry add flask-cors
  - Run dev server: poetry run python app.py
  - Run a single test: poetry run pytest tests/test_some_module.py -q
  - Run all tests: poetry run pytest -q
  (If you prefer a dedicated venv: python -m venv .venv && source .venv/bin/activate)


Frontend (Vite + React)
- Install dependencies and run dev server:
  - cd frontend && npm install
  - npm run dev
- Build:
  - cd frontend && npm run build
- Run a single frontend test (if added):
  - Use the test runner configured (not present by default). Add Jest/Playwright as needed.

Notes
- The backend requires the ffmpeg binary on PATH for conversions. Install via Homebrew (macOS) or apt (Linux).
- The Flask app enforces a 50 MB upload limit (app.config['MAX_CONTENT_LENGTH']).

---

## High-level architecture

- Monorepo layout:
  - backend/: Flask API that handles conversion and analysis
  - frontend/: Vite + React UI (WaveSurfer.js used for waveforms)

- Backend responsibilities:
  - POST /convert: Accepts an uploaded file (MP4), converts to MP3 using ffmpeg-python (falls back to system ffmpeg), returns MP3 as audio/mpeg attachment. Uses tempfile for input/output and removes input temp files; caller is responsible for removing the output file after send_file return handler.
  - POST /analyze: Accepts two audio files (reference_audio, user_audio) and optional params (threshold_db, n_fft, hop_length). Saves to a temp dir, calls analyze_files(ref_path, user_path, threshold_db, n_fft, hop_length) and returns a JSON payload containing summary stats and base64-encoded PNG figures.
  - Analysis pipeline (backend/analyze.py): librosa loads audio (SR=44100 by default), computes STFT → amplitude to dB → per-frame peak detection (scipy.signal.find_peaks) above threshold_db → match peaks using scipy.optimize.linear_sum_assignment on a cents-distance cost matrix → compute per-frame and aggregate metrics (mean freq error in cents, mean amplitude error in dB, combined error) → generate 4 matplotlib figures serialized to base64 strings.
  - CORS is enabled via simple after_request headers (flask-cors is also in pyproject dependencies).

- Frontend responsibilities:
  - AudioPanel: left side user audio (record via MediaRecorder OR upload MP3/MP4); if MP4 is uploaded, upload to /convert then use returned MP3; WaveSurfer.js previews for both user and reference audio.
  - ResultsPanel: renders 4 graphs (img tags) from base64 PNG strings returned from /analyze and a summary stats card.
  - App: manages state and orchestrates convert → analyze flow, handles loading states and disables Analyze until both files are ready.

---

## Key conventions and repo-specific patterns

- Sample rate constant: backend/analyze.py uses SR = 44100. Treat this as canonical unless changing it project-wide.
- Default threshold: the current Flask route default is threshold_db = -60.0; the earlier spec mentioned -40. Confirm before changing defaults.
- Parameter names accepted by /analyze: threshold_db (float), n_fft (int), hop_length (int).
- Figures in /analyze result are under `figures` with keys f1..f4 as base64 PNG strings. Frontend expects this exact structure.
- Temporary files and cleanup:
  - convert_mp4_to_mp3 saves the upload to a NamedTemporaryFile and deletes it after conversion; output MP3 is returned and the Flask route removes it after send_file via after_this_request hook.
  - analyze route writes both uploaded files to a TemporaryDirectory and removes the directory automatically on exit.
- Error handling:
  - The backend returns safe errors (e.g., 400 for validation errors, 413 for large files, 500 for internal errors with a general message).
- Dev server entrypoints:
  - Backend: python app.py (dev only). pyproject.toml includes a `start` script referencing backend.app:run_app — verify if a run_app helper exists before using it in production.
  - Frontend: npm run dev (Vite)

---

## Files that matter most for Copilot sessions
- backend/app.py — routes, param parsing, CORS, upload handling
- backend/convert.py — MP4→MP3 conversion logic and fallbacks
- backend/analyze.py — full analysis pipeline and figure generation
- frontend/src/api.js — fetch wrappers used by UI
- frontend/src/components/* — AudioPanel, ResultsPanel, App wiring

---

## AI/assistant config discovered
- No CLAUDE.md, .cursorrules, AGENTS.md, .windsurfrules, CONVENTIONS.md, AIDER_CONVENTIONS.md, or .clinerules found. If adding rules for other assistants, put them at the repo's .github/ folder as appropriate.

---

If you want, I can:
- Add a short checklist for PR reviewers (unit tests required, behavior to verify for /analyze),
- Configure a simple GitHub Actions workflow for running backend tests,
- Or add MCP server recommendations (e.g., Playwright) — would you like that?

Created .github/copilot-instructions.md. Adjustments or additions required?