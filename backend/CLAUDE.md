# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies** (requires uv):
```bash
uv install
```

**Run the server:**
```bash
uv run python app.py
# Runs on http://127.0.0.1:5000
```

**Run tests:**
```bash
uv run pytest tests/test_api.py
# Single test:
uv run pytest tests/test_api.py::TestAnalyzeEndpoint::test_analyze_success -v
```

**System requirement:** `ffmpeg` must be on PATH (`brew install ffmpeg` on macOS).

## Architecture

This is a Flask backend with two POST endpoints:

- **`/convert`** — accepts a multipart `file` field, converts it to MP3 via `convert.py`, returns binary MP3.
- **`/analyze`** — accepts `reference_audio` + `user_audio` multipart files plus optional params (`threshold_db`, `n_fft`, `hop_length`), delegates to `analyze.py`, returns JSON with metrics and base64 visualizations.

### Module responsibilities

**`app.py`** — Route handlers, input validation, error handling. Uses lazy imports for heavy audio libraries to keep startup fast.

**`convert.py`** — MP4→MP3 conversion. Tries `ffmpeg-python` first, falls back to subprocess `ffmpeg` call. Output: 44100 Hz, 192 kbps, libmp3lame.

**`analyze.py`** — Core audio analysis pipeline:
1. Load both audio files with librosa (resampled to 22050 Hz)
2. Compute STFT frames for both
3. Detect spectral peaks per frame via `scipy.signal.find_peaks` above `threshold_db`
4. Match peaks across reference/user using the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`)
5. Compute per-frame frequency error (cents) and amplitude error (dB)
6. Generate 4 matplotlib figures (spectrograms, peak tracks, error timeline, error histogram) encoded as base64 PNG strings

Returned JSON keys: `duration`, `mean_freq_error_cents`, `mean_amp_error_db`, `mean_combined_error`, `figures` (list of 4 base64 strings).
