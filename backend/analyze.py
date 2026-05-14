"""backend.analyze

Small, test-friendly helpers to analyze two audio files (reference and user)
and compute spectral peak matching errors.

Primary function:
    analyze_files(ref_path, user_path, threshold_db, n_fft, hop_length)

Returns a JSON-serializable dict with duration (s), mean_freq_error_cents,
mean_amp_error_db, mean_combined_error, and figures f1..f4 as base64 PNG strings.

Notes:
- Uses sr=44100, librosa.load(..., sr=44100, mono=True)
- Computes STFT magnitude with given n_fft and hop_length
- Converts amplitude to dB via librosa.amplitude_to_db
- Per-frame peak finding uses scipy.signal.find_peaks above threshold_db
- Peak matching uses scipy.optimize.linear_sum_assignment on cost matrix
  where cost = abs(1200*log2(f_user / f_ref))
- Silent frames (both columns max < threshold_db) are excluded
- Robust to edge cases: no peaks, zero frequencies, mismatched shapes

"""
from typing import Dict, Any, Tuple, List
import io
import base64
import math

import numpy as np
import librosa
import librosa.display
from scipy.signal import find_peaks
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SR = 44100  # sample rate constant used internally


def _stft_db(y: np.ndarray, n_fft: int, hop_length: int) -> Tuple[np.ndarray, np.ndarray]:
    """Compute magnitude STFT and convert to dB. Returns (mag_db, freqs).

    mag_db shape: (n_freq_bins, n_frames)
    freqs shape: (n_freq_bins,)
    """
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    # avoid all-zero S when empty
    if S.size == 0:
        return np.zeros((0, 0)), np.array([])
    mag_db = librosa.amplitude_to_db(S, ref=np.max)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=n_fft)
    return mag_db, freqs


def _frame_peaks(mag_db_col: np.ndarray, freqs: np.ndarray, threshold_db: float) -> Tuple[np.ndarray, np.ndarray]:
    """Find peaks in a single spectral frame (column of mag_db) above threshold_db.

    Returns (peak_freqs, peak_amps_db). Both are 1D arrays.
    """
    if mag_db_col.size == 0:
        return np.array([]), np.array([])
    # find_peaks works on 1D array
    peaks, props = find_peaks(mag_db_col, height=threshold_db)
    if peaks.size == 0:
        return np.array([]), np.array([])
    peak_freqs = freqs[peaks]
    peak_amps_db = props["peak_heights"]
    # Exclude non-positive freqs (e.g., DC)
    mask = peak_freqs > 0
    return peak_freqs[mask], peak_amps_db[mask]


def _match_peaks(freqs_user: np.ndarray, freqs_ref: np.ndarray) -> List[Tuple[int, int, float]]:
    """Match peaks between user and ref. Returns list of tuples (i, j, cents_error).

    If either input is empty, returns empty list.
    """
    if freqs_user.size == 0 or freqs_ref.size == 0:
        return []
    # Build cost matrix: absolute cents difference
    # Avoid division by zero - filter freqs <= 0
    fu = freqs_user
    fr = freqs_ref
    # construct cost matrix of shape (len(fu), len(fr))
    # cost = abs(1200 * log2(fu / fr))
    # Use outer to compute pairwise
    # protect zeros by setting cost to large value when either freq <=0
    with np.errstate(divide='ignore', invalid='ignore'):
        cost = np.abs(1200.0 * np.log2(np.divide(fu[:, None], fr[None, :], where=(fr[None, :] > 0))))
    # Where fr==0 (invalid), set cost large
    cost = np.where(np.isfinite(cost), cost, 1e6)
    # Hungarian algorithm: works with rectangular matrices
    try:
        row_ind, col_ind = linear_sum_assignment(cost)
    except Exception:
        return []
    matches = []
    for i, j in zip(row_ind, col_ind):
        c = cost[i, j]
        # ignore artificially large matches
        if c >= 1e5:
            continue
        matches.append((int(i), int(j), float(c)))
    return matches


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('ascii')


def analyze_files(ref_path: str, user_path: str, threshold_db: float, n_fft: int, hop_length: int) -> Dict[str, Any]:
    """Analyze two audio files and compute spectral peak matching errors.

    Parameters
    ----------
    ref_path, user_path: str
        Paths to reference and user audio files (e.g., mp3). Loaded with sr=44100, mono=True.
    threshold_db: float
        dB threshold above which spectral peaks are considered (e.g., -60)
    n_fft, hop_length: int
        STFT parameters

    Returns
    -------
    dict with keys: duration, mean_freq_error_cents, mean_amp_error_db, mean_combined_error,
    figures: {f1..f4}
    """
    # Load audio
    y_ref, _ = librosa.load(ref_path, sr=SR, mono=True)
    y_user, _ = librosa.load(user_path, sr=SR, mono=True)

    duration = max(len(y_ref), len(y_user)) / float(SR)

    mag_db_ref, freqs_ref = _stft_db(y_ref, n_fft=n_fft, hop_length=hop_length)
    mag_db_user, freqs_user = _stft_db(y_user, n_fft=n_fft, hop_length=hop_length)

    # Align frames: number of frames may differ due to length differences; use min frames
    n_frames = min(mag_db_ref.shape[1] if mag_db_ref.size else 0, mag_db_user.shape[1] if mag_db_user.size else 0)

    freq_errors_all = []
    amp_errors_all = []
    frame_mean_freq_errors = []

    # For figure data: collect peak freqs over time
    times = np.arange(n_frames) * hop_length / float(SR)
    peak_times_ref = []
    peak_freqs_ref = []
    peak_times_user = []
    peak_freqs_user = []

    for frame in range(n_frames):
        col_ref = mag_db_ref[:, frame]
        col_user = mag_db_user[:, frame]
        # Exclude silent frames where both columns max < threshold_db
        max_ref = np.max(col_ref) if col_ref.size else -np.inf
        max_user = np.max(col_user) if col_user.size else -np.inf
        if max_ref < threshold_db and max_user < threshold_db:
            # silent frame
            frame_mean_freq_errors.append(np.nan)
            continue
        # find peaks
        pf_ref, pa_ref = _frame_peaks(col_ref, freqs_ref, threshold_db)
        pf_user, pa_user = _frame_peaks(col_user, freqs_user, threshold_db)

        # collect for plotting
        if pf_ref.size:
            peak_times_ref.extend([times[frame]] * len(pf_ref))
            peak_freqs_ref.extend(pf_ref.tolist())
        if pf_user.size:
            peak_times_user.extend([times[frame]] * len(pf_user))
            peak_freqs_user.extend(pf_user.tolist())

        if pf_ref.size == 0 or pf_user.size == 0:
            frame_mean_freq_errors.append(np.nan)
            continue

        matches = _match_peaks(pf_user, pf_ref)
        if len(matches) == 0:
            frame_mean_freq_errors.append(np.nan)
            continue

        frame_freq_errs = []
        frame_amp_errs = []
        for i_idx, j_idx, cents in matches:
            # cents already positive absolute
            frame_freq_errs.append(cents)
            # amplitude: need to map amps arrays
            amp_u = pa_user[i_idx] if i_idx < len(pa_user) else None
            amp_r = pa_ref[j_idx] if j_idx < len(pa_ref) else None
            if amp_u is None or amp_r is None:
                continue
            frame_amp_errs.append(abs(float(amp_u) - float(amp_r)))

        if frame_freq_errs:
            frame_mean = float(np.mean(frame_freq_errs))
            freq_errors_all.extend(frame_freq_errs)
            frame_mean_freq_errors.append(frame_mean)
        else:
            frame_mean_freq_errors.append(np.nan)
        if frame_amp_errs:
            amp_errors_all.extend(frame_amp_errs)

    # compute aggregates
    mean_freq_error_cents = float(np.nanmean(freq_errors_all)) if len(freq_errors_all) else float('nan')
    mean_amp_error_db = float(np.nanmean(amp_errors_all)) if len(amp_errors_all) else float('nan')
    if math.isnan(mean_freq_error_cents):
        mean_combined_error = float('nan')
    else:
        # combined error = sqrt((mean_freq_err/100)^2 + (mean_amp_err/20)^2)
        amp_term = 0.0 if math.isnan(mean_amp_error_db) else (mean_amp_error_db / 20.0)
        mean_combined_error = math.sqrt((mean_freq_error_cents / 100.0) ** 2 + amp_term ** 2)

    # Create figures
    figures: Dict[str, str] = {}

    # Figure 1: Spectrograms side-by-side
    fig1 = plt.figure(figsize=(10, 6))
    ax1 = fig1.add_subplot(2, 1, 1)
    if mag_db_ref.size:
        img = librosa.display.specshow(mag_db_ref, sr=SR, hop_length=hop_length, x_axis='time', y_axis='linear', ax=ax1)
        ax1.set_title('Reference spectrogram (dB)')
    else:
        ax1.text(0.5, 0.5, 'No data', ha='center')
    ax2 = fig1.add_subplot(2, 1, 2)
    if mag_db_user.size:
        img2 = librosa.display.specshow(mag_db_user, sr=SR, hop_length=hop_length, x_axis='time', y_axis='linear', ax=ax2)
        ax2.set_title('User spectrogram (dB)')
    else:
        ax2.text(0.5, 0.5, 'No data', ha='center')
    fig1.tight_layout()
    figures['f1'] = _fig_to_base64(fig1)

    # Figure 2: Peak frequency tracks over time
    fig2 = plt.figure(figsize=(10, 4))
    ax = fig2.add_subplot(1, 1, 1)
    if peak_times_ref:
        ax.scatter(peak_times_ref, peak_freqs_ref, s=8, c='C0', label='ref', alpha=0.7)
    if peak_times_user:
        ax.scatter(peak_times_user, peak_freqs_user, s=8, c='C1', label='user', alpha=0.7)
    ax.set_ylabel('Frequency (Hz)')
    ax.set_xlabel('Time (s)')
    ax.set_title('Spectral peaks over time')
    ax.legend()
    fig2.tight_layout()
    figures['f2'] = _fig_to_base64(fig2)

    # Figure 3: Per-frame mean freq error over time
    fig3 = plt.figure(figsize=(10, 3))
    ax3 = fig3.add_subplot(1, 1, 1)
    if n_frames > 0:
        ax3.plot(times, np.array(frame_mean_freq_errors), drawstyle='steps-mid')
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Mean freq error (cents)')
        ax3.set_title('Per-frame mean frequency error (cents)')
    else:
        ax3.text(0.5, 0.5, 'No frames', ha='center')
    fig3.tight_layout()
    figures['f3'] = _fig_to_base64(fig3)

    # Figure 4: Histogram of amplitude errors (dB)
    fig4 = plt.figure(figsize=(6, 4))
    ax4 = fig4.add_subplot(1, 1, 1)
    if amp_errors_all:
        ax4.hist(amp_errors_all, bins=40, color='C3', alpha=0.8)
        ax4.set_xlabel('Amplitude error (dB)')
        ax4.set_title('Histogram of amplitude errors (dB)')
    else:
        ax4.text(0.5, 0.5, 'No amplitude errors', ha='center')
    fig4.tight_layout()
    figures['f4'] = _fig_to_base64(fig4)

    result = {
        'duration': float(duration),
        'mean_freq_error_cents': mean_freq_error_cents,
        'mean_amp_error_db': mean_amp_error_db,
        'mean_combined_error': mean_combined_error,
        'figures': figures,
    }
    return result
