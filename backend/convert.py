import os
import tempfile
from typing import Optional

try:
    import ffmpeg
except Exception:
    ffmpeg = None  # tests will catch this and return helpful error


def convert_mp4_to_mp3(file_storage) -> str:
    """Save uploaded file to a temporary MP4, convert to MP3 with ffmpeg-python, and return MP3 path.

    The input temporary file is always removed. The caller is responsible for removing the output MP3 when done.
    Raises RuntimeError on failures with a helpful message.
    """
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python is not available. Please install ffmpeg-python and ensure ffmpeg is on PATH.")

    in_temp = None
    out_path = None
    try:
        # Create a named temp file for the uploaded MP4
        in_temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        in_temp.close()
        # file_storage is a werkzeug FileStorage - it supports save()
        try:
            file_storage.save(in_temp.name)
        except Exception:
            # Fallback: write bytes
            file_storage.stream.seek(0)
            with open(in_temp.name, "wb") as f:
                f.write(file_storage.stream.read())

        # Prepare output temp path
        out_fd, out_path = tempfile.mkstemp(suffix=".mp3")
        os.close(out_fd)

        # Run ffmpeg conversion: prefer libmp3lame if available
        try:
            stream = ffmpeg.input(in_temp.name)
            stream = ffmpeg.output(stream, out_path, format="mp3", acodec="libmp3lame", audio_bitrate="192k")
            # overwrite if exists
            stream = ffmpeg.overwrite_output(stream)
            # run and capture stderr for diagnostics
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        except ffmpeg.Error as e:
            # Clean up output if ffmpeg failed
            if out_path and os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except Exception:
                    pass
            raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)}")

        return out_path
    finally:
        # Always remove input temporary file
        if in_temp and os.path.exists(in_temp.name):
            try:
                os.remove(in_temp.name)
            except Exception:
                pass
