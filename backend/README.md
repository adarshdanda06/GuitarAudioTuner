# Backend (Flask)

Requirements
- Python 3.8+
- pip
- ffmpeg (binary) on PATH

Install ffmpeg
- macOS (Homebrew): brew install ffmpeg
- Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y ffmpeg

Python dependencies (example)

cd backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask numpy librosa scipy matplotlib ffmpeg-python werkzeug

Run (development)
cd backend
python app.py
# server will listen on http://127.0.0.1:5000

API
- POST /convert
  - Form field: file (binary file - e.g., MP4)
  - Returns: audio/mpeg attachment (MP3)

  Example:
  curl -F "file=@sample.mp4" http://127.0.0.1:5000/convert --output out.mp3

- POST /analyze
  - Form fields: reference_audio (file), user_audio (file)
  - Optional form fields (scalars): threshold_db (float, default -60.0), n_fft (int, default 2048), hop_length (int, default 512)
  - Returns: JSON with duration, mean_freq_error_cents, mean_amp_error_db, mean_combined_error, and figures (base64 PNG strings).

  Example (defaults):
  curl -X POST -F "reference_audio=@ref.mp3" -F "user_audio=@user.mp3" http://127.0.0.1:5000/analyze

  Example (with params):
  curl -X POST \
    -F "reference_audio=@ref.mp3" \
    -F "user_audio=@user.mp3" \
    -F "threshold_db=-50" \
    -F "n_fft=2048" \
    -F "hop_length=512" \
    http://127.0.0.1:5000/analyze

Notes
- The conversion uses ffmpeg-python which requires the ffmpeg binary on PATH. If you see an error about ffmpeg not found, install ffmpeg as shown above.
- The Flask app includes a 50 MB upload limit (app.config['MAX_CONTENT_LENGTH']).
