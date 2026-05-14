import os
from flask import Flask, request, jsonify, send_file, after_this_request
from werkzeug.exceptions import RequestEntityTooLarge

from backend.convert import convert_mp4_to_mp3
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
# 50 MB limit
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    return jsonify({"error": "File too large. Max size is 50 MB."}), 413


@app.route('/convert', methods=['POST'])
def convert_route():
    if 'file' not in request.files:
        return jsonify({"error": "Missing 'file' in form data."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    try:
        out_path = convert_mp4_to_mp3(file)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Ensure output file is removed after response
    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        return response

    # Use mimetype audio/mpeg and send as attachment
    try:
        return send_file(out_path, mimetype='audio/mpeg', as_attachment=True, download_name=os.path.basename(out_path))
    except TypeError:
        # Older Flask versions use attachment_filename
        return send_file(out_path, mimetype='audio/mpeg', as_attachment=True, attachment_filename=os.path.basename(out_path))


@app.after_request
def add_cors_headers(response):
    # Enable simple CORS for cross-origin requests
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response


@app.route('/analyze', methods=['POST'])
def analyze_route():
    # Expect multipart form fields 'reference_audio' and 'user_audio'
    if 'reference_audio' not in request.files or 'user_audio' not in request.files:
        return jsonify({"error": "Both 'reference_audio' and 'user_audio' files are required."}), 400

    ref_file = request.files['reference_audio']
    user_file = request.files['user_audio']
    if ref_file.filename == '' or user_file.filename == '':
        return jsonify({"error": "Empty filename provided for one of the files."}), 400

    # Parse optional numeric params with defaults
    def _parse_float(name, default):
        v = request.form.get(name)
        if v is None:
            return default, None
        try:
            return float(v), None
        except ValueError:
            return None, f"Parameter {name} must be a float."

    def _parse_int(name, default):
        v = request.form.get(name)
        if v is None:
            return default, None
        try:
            return int(v), None
        except ValueError:
            return None, f"Parameter {name} must be an integer."

    threshold_db, err = _parse_float('threshold_db', -60.0)
    if err:
        return jsonify({"error": err}), 400
    n_fft, err = _parse_int('n_fft', 2048)
    if err:
        return jsonify({"error": err}), 400
    hop_length, err = _parse_int('hop_length', 512)
    if err:
        return jsonify({"error": err}), 400

    # Basic validation
    if not (-120.0 <= threshold_db <= 0.0):
        return jsonify({"error": "threshold_db out of range [-120, 0]"}), 400
    if n_fft < 256 or n_fft > 16384:
        return jsonify({"error": "n_fft out of range [256, 16384]"}), 400
    if hop_length <= 0 or hop_length > n_fft:
        return jsonify({"error": "hop_length must be > 0 and <= n_fft"}), 400

    # Save incoming files to a temporary directory and call analyze_files
    try:
        with tempfile.TemporaryDirectory() as td:
            ref_path = os.path.join(td, secure_filename(ref_file.filename))
            user_path = os.path.join(td, secure_filename(user_file.filename))
            ref_file.save(ref_path)
            user_file.save(user_path)

            # Import analyze_files lazily to avoid heavy imports at module import time
            from backend.analyze import analyze_files
            result = analyze_files(ref_path, user_path, threshold_db, n_fft, hop_length)
            return jsonify(result), 200
    except RequestEntityTooLarge:
        # Let Flask's error handler deal with this
        raise
    except Exception as e:
        # Do not expose internal traceback; return a safe error message
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


if __name__ == '__main__':
    # Simple dev server for local testing
    app.run(host='127.0.0.1', port=5000, debug=True)

# Test with curl:
# Convert endpoint:
# curl -F "file=@sample.mp4" http://127.0.0.1:5000/convert --output out.mp3
# Analyze endpoint example (with defaults):
# curl -X POST -F "reference_audio=@ref.mp3" -F "user_audio=@user.mp3" http://127.0.0.1:5000/analyze
# With optional params:
# curl -X POST -F "reference_audio=@ref.mp3" -F "user_audio=@user.mp3" -F "threshold_db=-50" -F "n_fft=2048" -F "hop_length=512" http://127.0.0.1:5000/analyze
