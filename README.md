# Guitar Audio Tuner

This repository contains a small web app for converting and analyzing audio recordings to help tune and compare guitar playing.

- backend/: Flask API that converts uploads (MP4 -> MP3) and analyzes two audio files.
- frontend/: Vite + React UI that uploads audio and displays results.

Backend setup (uses uv):

- Install dependencies:

  cd backend && uv install

- Run dev server:

  cd backend && uv run python app.py

- Run tests:

  cd backend && uv run pytest -q

Notes:
- The backend requires the `ffmpeg` binary on PATH for conversions (e.g., `brew install ffmpeg` on macOS).
- The Flask app enforces a 50 MB upload limit (app.config['MAX_CONTENT_LENGTH']).

See backend/README.md and frontend/README.md for more details and API examples.
