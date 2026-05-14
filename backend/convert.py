import os
import tempfile
import subprocess
import shlex
from typing import Optional

try:
    import ffmpeg  # type: ignore
except Exception:
    ffmpeg = None  # fallback to subprocess if available


def _run_subprocess_ffmpeg(in_path: str, out_path: str) -> None:
    """Run system ffmpeg as a subprocess to convert input to mp3."""
    # Build a safe command list
    cmd = [
        'ffmpeg',
        '-y',
        '-i', in_path,
        '-vn',  # no video
        '-acodec', 'libmp3lame',
        '-ar', '44100',
        '-ab', '192k',
        out_path,
    ]
    try:
        completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        raise RuntimeError(f"ffmpeg (subprocess) failed: {stderr}")


def convert_mp4_to_mp3(file_storage) -> str:
    """Save uploaded file to a temporary MP4, convert to MP3, and return MP3 path.

    Tries ffmpeg-python first; if unavailable, falls back to calling the ffmpeg binary via subprocess.
    The input temporary file is always removed. The caller is responsible for removing the output MP3 when done.
    Raises RuntimeError on failures with a helpful message.
    """
    in_temp = None
    out_path = None
    try:
        # Save upload to a temp file
        in_temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        in_temp.close()
        try:
            file_storage.save(in_temp.name)
        except Exception:
            # Fallback: read bytes from stream
            file_storage.stream.seek(0)
            with open(in_temp.name, 'wb') as f:
                f.write(file_storage.stream.read())

        # Prepare output temp file
        out_fd, out_path = tempfile.mkstemp(suffix='.mp3')
        os.close(out_fd)

        # Try ffmpeg-python if available
        if ffmpeg is not None:
            try:
                stream = ffmpeg.input(in_temp.name)
                stream = ffmpeg.output(stream, out_path, format='mp3', acodec='libmp3lame', audio_bitrate='192k')
                stream = ffmpeg.overwrite_output(stream)
                ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
                return out_path
            except Exception as e:
                # cleanup and fall through to subprocess fallback
                if out_path and os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
                last_error = str(e)
        else:
            last_error = 'ffmpeg-python not installed'

        # Fallback to system ffmpeg binary
        try:
            _run_subprocess_ffmpeg(in_temp.name, out_path)
            return out_path
        except Exception as e:
            # ensure output removed
            if out_path and os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except Exception:
                    pass
            raise RuntimeError(f"Conversion failed ({last_error}); subprocess fallback error: {e}")

    finally:
        # Always attempt to remove input temp file
        if in_temp and os.path.exists(in_temp.name):
            try:
                os.remove(in_temp.name)
            except Exception:
                pass
