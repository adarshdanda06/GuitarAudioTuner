import os
from flask import Flask, request, jsonify, send_file, after_this_request
from werkzeug.exceptions import RequestEntityTooLarge

from backend.convert import convert_mp4_to_mp3

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


if __name__ == '__main__':
    # Simple dev server for local testing
    app.run(host='127.0.0.1', port=5000, debug=True)

# Test with curl:
# curl -F "file=@sample.mp4" http://127.0.0.1:5000/convert --output out.mp3
