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

    Uses librosa.stft (input: y shape (n_samples,), output: S shape (n_freq_bins, n_frames))
    and librosa.amplitude_to_db (converts magnitude to dB scale).

    Output dimensions:
      - mag_db: (n_freq_bins, n_frames) — spectral magnitude in dB; represents energy per frequency per time frame
      - freqs: (n_freq_bins,) — frequency values in Hz for each bin
    """
    # librosa.stft(y): y shape (n_samples,) → S shape (n_freq_bins, n_frames)
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    # avoid all-zero S when empty
    if S.size == 0:
        return np.zeros((0, 0)), np.array([])
    # librosa.amplitude_to_db(S): S shape (n_freq_bins, n_frames) → mag_db shape (n_freq_bins, n_frames)
    mag_db = librosa.amplitude_to_db(S, ref=np.max)
    # librosa.fft_frequencies(): returns freqs shape (n_freq_bins,) — frequency bin centers in Hz
    freqs = librosa.fft_frequencies(sr=SR, n_fft=n_fft)
    return mag_db, freqs


def _frame_peaks(mag_db_col: np.ndarray, freqs: np.ndarray, threshold_db: float) -> Tuple[np.ndarray, np.ndarray]:
    """Find peaks in a single spectral frame (column of mag_db) above threshold_db.

    Uses scipy.signal.find_peaks (input: 1D array, output: indices of peaks + properties dict).

    Output dimensions:
      - peak_freqs: (n_peaks,) — frequency values of detected peaks in Hz
      - peak_amps_db: (n_peaks,) — amplitude values of detected peaks in dB
    """
    if mag_db_col.size == 0:
        return np.array([]), np.array([])
    # scipy.signal.find_peaks(mag_db_col): returns (peaks, props) where peaks shape (n_peaks,)
    peaks, props = find_peaks(mag_db_col, height=threshold_db)
    if peaks.size == 0:
        return np.array([]), np.array([])
    peak_freqs = freqs[peaks]
    # props["peak_heights"] shape (n_peaks,) — amplitude values for each peak
    peak_amps_db = props["peak_heights"]
    # Exclude non-positive freqs (e.g., DC)
    mask = peak_freqs > 0
    return peak_freqs[mask], peak_amps_db[mask]


def _match_peaks(freqs_user: np.ndarray, freqs_ref: np.ndarray) -> List[Tuple[int, int, float]]:
    """Match peaks between user and ref using scipy.optimize.linear_sum_assignment.
    
    Builds a cost matrix of cents differences and solves the assignment problem.
    Uses scipy.optimize.linear_sum_assignment (input: cost matrix shape (m, n), 
    output: row_ind shape (m,), col_ind shape (m,)).

    Output dimensions:
      - matches: list of tuples [(i, j, cents_error), ...] where:
          i: index in freqs_user (int)
          j: index in freqs_ref (int)
          cents_error: frequency difference in cents (float)
        Length: min(len(freqs_user), len(freqs_ref)), filtered for valid assignments
    
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
    # scipy.optimize.linear_sum_assignment(cost): cost shape (m, n) → row_ind, col_ind each shape (min(m,n),)
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
    """Convert matplotlib figure to base64-encoded PNG string.
    
    Uses fig.savefig (output: PNG bytes) and base64.b64encode (output: ASCII string).

    Output dimensions:
      - base64_string: ASCII-encoded string representation of the figure PNG
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    # base64.b64encode(buf.read()): bytes input → bytes output, decode to ASCII string
    return base64.b64encode(buf.read()).decode('ascii')


def _load_audio(path: str) -> np.ndarray:
    """Load audio file using librosa.load at fixed sample rate.
    
    Uses librosa.load (input: file path, sr=44100, mono=True,
    output: y shape (n_samples,), sr scalar).

    Output dimensions:
      - y: (n_samples,) — mono audio waveform samples
    """
    # librosa.load returns (y, sr) where y shape (n_samples,)
    y, _ = librosa.load(path, sr=SR, mono=True)
    return y


def _compute_mag_db(y: np.ndarray, n_fft: int, hop_length: int) -> Tuple[np.ndarray, np.ndarray]:
    """Wrapper for _stft_db. Computes STFT magnitude in dB.
    
    Output dimensions:
      - mag_db: (n_freq_bins, n_frames) — spectral magnitude in dB
      - freqs: (n_freq_bins,) — frequency bin centers in Hz
    """
    return _stft_db(y, n_fft=n_fft, hop_length=hop_length)


def _process_frames(mag_db_ref: np.ndarray,
                    freqs_ref: np.ndarray,
                    mag_db_user: np.ndarray,
                    freqs_user: np.ndarray,
                    threshold_db: float,
                    hop_length: int) -> Tuple[list, list, list, list, list, list, np.ndarray, int]:
    """Process frames and return collected metrics and peak tracks.

    Iterates over frames, extracts peaks, performs matching, and collects errors.

    Output dimensions:
      - freq_errors_all: list of floats — frequency errors in cents for all matched peaks
      - amp_errors_all: list of floats — amplitude errors in dB for all matched peaks
      - frame_mean_freq_errors: list of floats (len: n_frames) — mean frequency error per frame (NaN if no peaks)
      - peak_times_ref: list of floats — time values for each reference peak detected
      - peak_freqs_ref: list of floats — frequency values for each reference peak detected
      - peak_times_user: list of floats — time values for each user peak detected
      - peak_freqs_user: list of floats — frequency values for each user peak detected
      - times: (n_frames,) — time value for each frame in seconds
      - n_frames: int — number of frames processed
    """
    n_frames = min(mag_db_ref.shape[1] if mag_db_ref.size else 0,
                   mag_db_user.shape[1] if mag_db_user.size else 0)
    times = (np.arange(n_frames) * hop_length) / float(SR)

    freq_errors_all = []
    amp_errors_all = []
    frame_mean_freq_errors = []

    peak_times_ref = []
    peak_freqs_ref = []
    peak_times_user = []
    peak_freqs_user = []

    for frame in range(n_frames):
        col_ref = mag_db_ref[:, frame]
        col_user = mag_db_user[:, frame]

        max_ref = np.max(col_ref) if col_ref.size else -np.inf
        max_user = np.max(col_user) if col_user.size else -np.inf
        if max_ref < threshold_db and max_user < threshold_db:
            frame_mean_freq_errors.append(np.nan)
            continue

        pf_ref, pa_ref = _frame_peaks(col_ref, freqs_ref, threshold_db)
        pf_user, pa_user = _frame_peaks(col_user, freqs_user, threshold_db)

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
            frame_freq_errs.append(cents)
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

    return (freq_errors_all, amp_errors_all, frame_mean_freq_errors,
            peak_times_ref, peak_freqs_ref, peak_times_user, peak_freqs_user,
            times, n_frames)


def _compute_aggregates(freq_errors_all: list, amp_errors_all: list) -> Tuple[float, float, float]:
    """Compute aggregate statistics from collected error lists.
    
    Uses np.nanmean (input: array-like, output: scalar float ignoring NaN values).

    Output dimensions:
      - mean_freq_error_cents: scalar float — mean frequency error in cents (NaN if no errors)
      - mean_amp_error_db: scalar float — mean amplitude error in dB (NaN if no errors)
      - mean_combined_error: scalar float — combined metric normalized from both error types
    """
    mean_freq_error_cents = float(np.nanmean(freq_errors_all)) if len(freq_errors_all) else float('nan')
    mean_amp_error_db = float(np.nanmean(amp_errors_all)) if len(amp_errors_all) else float('nan')
    if math.isnan(mean_freq_error_cents):
        mean_combined_error = float('nan')
    else:
        amp_term = 0.0 if math.isnan(mean_amp_error_db) else (mean_amp_error_db / 20.0)
        mean_combined_error = math.sqrt((mean_freq_error_cents / 100.0) ** 2 + amp_term ** 2)
    return mean_freq_error_cents, mean_amp_error_db, mean_combined_error


def _make_figures(mag_db_ref: np.ndarray, mag_db_user: np.ndarray,
                  peak_times_ref: list, peak_freqs_ref: list,
                  peak_times_user: list, peak_freqs_user: list,
                  frame_mean_freq_errors: list, amp_errors_all: list,
                  times: np.ndarray, n_frames: int,
                  hop_length: int) -> Dict[str, str]:
    """Generate matplotlib figures for visualization.
    
    Uses librosa.display.specshow to render spectrograms and matplotlib plotting functions.
    Each figure is converted to base64 PNG string via _fig_to_base64.

    Output dimensions:
      - figures: dict with keys 'f1', 'f2', 'f3', 'f4', each value is a base64-encoded PNG string
        f1: Reference and user spectrograms side-by-side
        f2: Frequency peaks over time (scatter plot)
        f3: Per-frame mean frequency error over time (line plot)
        f4: Histogram of amplitude errors (dB)
    """
    figures: Dict[str, str] = {}

    # Figure 1: Spectrograms side-by-side
    fig1 = plt.figure(figsize=(10, 6))
    ax1 = fig1.add_subplot(2, 1, 1)
    if mag_db_ref.size:
        # librosa.display.specshow: mag_db input shape (n_freq_bins, n_frames) → rendered to axis
        librosa.display.specshow(mag_db_ref, sr=SR, hop_length=hop_length, x_axis='time', y_axis='linear', ax=ax1)
        ax1.set_title('Reference spectrogram (dB)')
    else:
        ax1.text(0.5, 0.5, 'No data', ha='center')
    ax2 = fig1.add_subplot(2, 1, 2)
    if mag_db_user.size:
        librosa.display.specshow(mag_db_user, sr=SR, hop_length=hop_length, x_axis='time', y_axis='linear', ax=ax2)
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
        # ax.hist: input list of values → renders histogram to axis
        ax4.hist(amp_errors_all, bins=40, color='C3', alpha=0.8)
        ax4.set_xlabel('Amplitude error (dB)')
        ax4.set_title('Histogram of amplitude errors (dB)')
    else:
        ax4.text(0.5, 0.5, 'No amplitude errors', ha='center')
    fig4.tight_layout()
    figures['f4'] = _fig_to_base64(fig4)

    return figures


def analyze_files(ref_path: str, user_path: str, threshold_db: float, n_fft: int, hop_length: int) -> Dict[str, Any]:
    """Analyze two audio files and compute spectral peak matching errors.

    This function is a thin orchestrator that delegates to helper functions for
    loading, STFT, per-frame processing, aggregation, and figure creation.

    Output dimensions:
      - result: dict with keys:
          'duration': float — audio duration in seconds
          'mean_freq_error_cents': float — mean frequency error in cents
          'mean_amp_error_db': float — mean amplitude error in dB
          'mean_combined_error': float — combined normalized error metric
          'figures': dict with keys 'f1', 'f2', 'f3', 'f4' (base64 PNG strings)
    """
    # Load audio
    y_ref = _load_audio(ref_path)
    y_user = _load_audio(user_path)

    duration = max(len(y_ref), len(y_user)) / float(SR)

    mag_db_ref, freqs_ref = _compute_mag_db(y_ref, n_fft, hop_length)
    mag_db_user, freqs_user = _compute_mag_db(y_user, n_fft, hop_length)

    (freq_errors_all, amp_errors_all, frame_mean_freq_errors,
     peak_times_ref, peak_freqs_ref, peak_times_user, peak_freqs_user,
     times, n_frames) = _process_frames(
        mag_db_ref, freqs_ref, mag_db_user, freqs_user, threshold_db, hop_length)

    mean_freq_error_cents, mean_amp_error_db, mean_combined_error = _compute_aggregates(freq_errors_all, amp_errors_all)

    figures = _make_figures(mag_db_ref, mag_db_user,
                             peak_times_ref, peak_freqs_ref,
                             peak_times_user, peak_freqs_user,
                             frame_mean_freq_errors, amp_errors_all,
                             times, n_frames, hop_length)

    result = {
        'duration': float(duration),
        'mean_freq_error_cents': mean_freq_error_cents,
        'mean_amp_error_db': mean_amp_error_db,
        'mean_combined_error': mean_combined_error,
        'figures': figures,
    }
    return result
