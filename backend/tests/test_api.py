import io
import os
import tempfile

import pytest

# Skip entire module if core audio libs are missing
np = pytest.importorskip("numpy")
py_soundfile = pytest.importorskip("soundfile")
pytest.importorskip("librosa")

from flask import Flask, request, jsonify

import backend.analyze as analyze
import backend.convert as convert_mod
import backend.app as app_mod


SR = 44100


def make_wav_bytes(freq=440.0, duration=0.5, sr=SR):
    """Generate a short sine wave and return a BytesIO WAV file."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * freq * t)
    buf = io.BytesIO()
    # soundfile.write accepts a file-like object
    py_soundfile.write(buf, y.astype('float32'), sr, format='WAV')
    buf.seek(0)
    return buf


def test_analyze_endpoint():
    # Create a small Flask app exposing /analyze that calls analyze_files
    app = Flask(__name__)

    @app.route('/analyze', methods=['POST'])
    def analyze_route():
        if 'ref' not in request.files or 'user' not in request.files:
            return jsonify({'error': "missing files"}), 400
        ref = request.files['ref']
        user = request.files['user']
        ref_tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        user_tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        try:
            ref.save(ref_tmp.name)
            user.save(user_tmp.name)
            result = analyze.analyze_files(ref_tmp.name, user_tmp.name, threshold_db=-60, n_fft=1024, hop_length=512)
            return jsonify(result)
        finally:
            try:
                os.remove(ref_tmp.name)
            except Exception:
                pass
            try:
                os.remove(user_tmp.name)
            except Exception:
                pass

    client = app.test_client()

    data = {
        'ref': (make_wav_bytes(440.0), 'ref.wav'),
        'user': (make_wav_bytes(442.0), 'user.wav'),
    }
    resp = client.post('/analyze', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    j = resp.get_json()
    # Basic sanity checks
    assert 'duration' in j
    assert 'mean_freq_error_cents' in j
    assert 'mean_amp_error_db' in j
    assert 'mean_combined_error' in j
    assert 'figures' in j and isinstance(j['figures'], dict)


def test_convert_endpoint_monkeypatched(monkeypatch):
    # If ffmpeg-python is not available, we mock convert_mp4_to_mp3 to avoid heavy ffmpeg dependency.
    def fake_convert(file_storage):
        tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        tmp.write(b'FAKEMP3DATA')
        tmp.close()
        return tmp.name

    monkeypatch.setattr(convert_mod, 'convert_mp4_to_mp3', fake_convert)

    client = app_mod.app.test_client()

    # Send a small "mp4" payload (content doesn't need to be a valid MP4 because conversion is mocked)
    data = {'file': (io.BytesIO(b'testdata'), 'in.mp4')}
    resp = client.post('/convert', data=data, content_type='multipart/form-data')

    assert resp.status_code == 200
    # Response should be an audio/mpeg attachment
    ct = resp.headers.get('Content-Type', '')
    assert 'audio' in ct or 'mpeg' in ct
    cd = resp.headers.get('Content-Disposition', '')
    assert 'attachment' in cd

    # Clean up any temp files that fake_convert may have left
    # The app attempts to remove the returned file after sending, but be defensive
    # Try to read filename from Content-Disposition
    try:
        # parse filename=...
        if 'filename=' in cd:
            fn = cd.split('filename=')[-1].strip('"')
            if os.path.exists(fn):
                os.remove(fn)
    except Exception:
        pass
