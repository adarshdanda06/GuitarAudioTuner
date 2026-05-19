"""
Interactive walkthrough of the _stft_db() function with real output examples.

Run this script to see step-by-step how STFT transforms audio into frequency-time data.
You can modify parameters below to experiment!
"""

import numpy as np
import librosa

# ============================================================================
# CONFIGURATION - Try changing these!
# ============================================================================
SR = 44100              # Sample rate (Hz)
DURATION = 2.0          # Duration in seconds
FREQUENCY = 440         # Test tone frequency (Hz)
N_FFT = 2048            # FFT window size
HOP_LENGTH = 512        # Overlap between windows

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                 DETAILED WALKTHROUGH: _stft_db() FUNCTION                  ║
║                                                                            ║
║  This script traces through _stft_db() line by line with real examples.   ║
║  Parameters to experiment with:                                           ║
║    - FREQUENCY (try 440, 880, 220 - different pitches)                   ║
║    - N_FFT (try 1024, 2048, 4096 - affects frequency resolution)         ║
║    - HOP_LENGTH (try 256, 512, 1024 - affects time resolution)           ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

print(f"\n📋 Configuration:")
print(f"  Sample Rate (SR): {SR} Hz")
print(f"  Duration: {DURATION} seconds")
print(f"  Test Tone Frequency: {FREQUENCY} Hz")
print(f"  FFT Size (n_fft): {N_FFT}")
print(f"  Window Hop (hop_length): {HOP_LENGTH}")

# ============================================================================
# STEP 1: Create test audio signal
# ============================================================================
print("\n" + "=" * 80)
print("STEP 1: Create input audio signal y")
print("=" * 80)

t = np.linspace(0, DURATION, int(SR * DURATION), endpoint=False)
y = np.sin(2 * np.pi * FREQUENCY * t)

print(f"""
Created: {DURATION}s of {FREQUENCY} Hz sine wave at SR={SR}

Code:
  t = np.linspace(0, {DURATION}, int({SR} * {DURATION}), endpoint=False)
  y = np.sin(2 * np.pi * {FREQUENCY} * t)

Result:
  y shape: {y.shape}
  y length: {len(y)} samples
  y range: [{y.min():.4f}, {y.max():.4f}]
  
Sample values (first 10):
  {y[:10]}
""")

# ============================================================================
# STEP 2: Compute STFT (this is librosa.stft internally)
# ============================================================================
print("\n" + "=" * 80)
print("STEP 2: Compute STFT magnitude")
print("=" * 80)

S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))

print(f"""
Code:
  S = np.abs(librosa.stft(y, n_fft={N_FFT}, hop_length={HOP_LENGTH}))

What librosa.stft() does:
  1. Splits audio into overlapping windows of size {N_FFT}
  2. Applies Hann window function to each window
  3. Computes FFT for each window (complex frequency spectrum)
  4. np.abs() extracts magnitude (removes phase)

Result shape explanation:
  {S.shape} = ({N_FFT}//2 + 1, n_frames)
  
  Frequency bins: {N_FFT}//2 + 1 = {N_FFT//2 + 1}
    (0 to Nyquist frequency = SR/2 = {SR//2} Hz)
    
  Time frames: {S.shape[1]}
    Formula: ceil((len(y) - {N_FFT}) / {HOP_LENGTH}) + 1
    = ceil(({len(y)} - {N_FFT}) / {HOP_LENGTH}) + 1 = {S.shape[1]}
    
Frequency resolution (Hz per bin):
  SR / n_fft = {SR} / {N_FFT} = {SR / N_FFT:.2f} Hz/bin
  
Time resolution (seconds per frame):
  n_fft / SR = {N_FFT} / {SR} = {N_FFT / SR:.4f} seconds/frame
  Frame advances by: {HOP_LENGTH} / {SR} = {HOP_LENGTH / SR:.4f} seconds

S value statistics:
  min: {S.min():.4f}
  max: {S.max():.4f}
  mean: {S.mean():.4f}

First 5 frequency bins, first 3 frames (magnitude values):
{S[:5, :3]}
""")

# ============================================================================
# STEP 3: Convert to dB scale
# ============================================================================
print("\n" + "=" * 80)
print("STEP 3: Convert magnitude to dB scale")
print("=" * 80)

ref_val = np.max(S)
mag_db = librosa.amplitude_to_db(S, ref=np.max)

print(f"""
Code:
  mag_db = librosa.amplitude_to_db(S, ref=np.max)

What this does:
  Formula: 20 * log10(magnitude / reference)
  Reference: np.max(S) = {ref_val:.4f}
  
Why dB scale?
  - Logarithmic (matches human hearing perception)
  - Dynamic range compression (large values become manageable)
  - Reference to maximum means 0 dB = loudest, -80 dB = quiet
  - Easier to visualize in spectrograms

Example calculation for S[0,0]:
  S[0, 0] = {S[0, 0]:.6f}
  mag_db[0, 0] = 20 * log10({S[0, 0]:.6f} / {ref_val:.6f})
               = 20 * log10({S[0, 0] / ref_val:.8f})
               = {mag_db[0, 0]:.2f} dB

Result:
  mag_db shape: {mag_db.shape} (same as S)
  mag_db range: [{mag_db.min():.2f}, {mag_db.max():.2f}] dB
  
First 5 frequency bins, first 3 frames (dB values):
{mag_db[:5, :3]}

Notice: Peak value is 0 dB (reference), quiet values are negative
""")

# ============================================================================
# STEP 4: Get frequency values
# ============================================================================
print("\n" + "=" * 80)
print("STEP 4: Get frequency bin centers")
print("=" * 80)

freqs = librosa.fft_frequencies(sr=SR, n_fft=N_FFT)

print(f"""
Code:
  freqs = librosa.fft_frequencies(sr={SR}, n_fft={N_FFT})

What this does:
  Creates array of Hz values for each FFT bin
  
Formula for bin k:
  f_k = k * SR / n_fft = k * {SR} / {N_FFT} = k * {SR / N_FFT:.2f}

Result:
  freqs shape: {freqs.shape}
  freqs range: [{freqs.min():.1f}, {freqs.max():.1f}] Hz

Frequency values for selected bins:
""")

for i in [0, 1, 10, 20, 100, 512, N_FFT//2]:
    if i < len(freqs):
        print(f"  bin {i:4d}: {freqs[i]:10.2f} Hz")

print(f"""
Notice:
  - bin 0 = 0 Hz (DC component, no signal)
  - Frequencies increase linearly with bin index
  - bin {N_FFT//2} = {freqs[N_FFT//2]:.1f} Hz = Nyquist limit (SR/2)
""")

# ============================================================================
# STEP 5: Find where test signal appears
# ============================================================================
print("\n" + "=" * 80)
print("STEP 5: Locate test signal in the frequency domain")
print("=" * 80)

# Find which bin should contain our test frequency
expected_bin = int(round(FREQUENCY / (SR / N_FFT)))
print(f"""
We created a {FREQUENCY} Hz sine wave.
Where should it appear?

Expected bin: {FREQUENCY} Hz / ({SR / N_FFT:.2f} Hz/bin) = {expected_bin:.1f}
So approximately bin {expected_bin}

Actual strongest peak in frame 0:
""")

peak_bin_frame0 = np.argmax(mag_db[:, 0])
peak_freq = freqs[peak_bin_frame0]
peak_energy = mag_db[peak_bin_frame0, 0]

print(f"  Peak bin: {peak_bin_frame0}")
print(f"  Peak frequency: {peak_freq:.2f} Hz (expected {FREQUENCY} Hz)")
print(f"  Peak energy: {peak_energy:.2f} dB")
print(f"  Difference: {abs(peak_freq - FREQUENCY):.2f} Hz")

# Show energy levels around the peak
print(f"\nEnergy levels around the peak (frame 0):")
print(f"  Bin | Frequency (Hz) | Energy (dB)")
print(f"  {'-'*40}")
for i in range(max(0, peak_bin_frame0 - 3), min(len(freqs), peak_bin_frame0 + 4)):
    marker = " ← PEAK" if i == peak_bin_frame0 else ""
    print(f"  {i:3d} | {freqs[i]:14.2f} | {mag_db[i, 0]:10.2f}{marker}")

# ============================================================================
# STEP 6: Function returns
# ============================================================================
print("\n" + "=" * 80)
print("STEP 6: Return values")
print("=" * 80)

print(f"""
_stft_db() returns a tuple: (mag_db, freqs)

Return 1 - mag_db:
  Shape: {mag_db.shape}
  Type: numpy.ndarray (float)
  Meaning: mag_db[freq_bin, time_frame] = energy in dB
  
  Interpretation:
    - Rows (axis 0): frequency dimension (0 Hz at top, to {freqs[-1]:.0f} Hz at bottom)
    - Cols (axis 1): time dimension (start at left, end at right)
    - Values: negative dB values (0 dB = loudest point in audio)
  
  Access example:
    mag_db[{peak_bin_frame0}, 0] = {mag_db[peak_bin_frame0, 0]:.2f} dB
    (Energy at {freqs[peak_bin_frame0]:.1f} Hz in frame 0)

Return 2 - freqs:
  Shape: {freqs.shape}
  Type: numpy.ndarray (float)
  Meaning: freqs[freq_bin] = frequency value in Hz
  
  Interpretation:
    - One-dimensional array
    - Maps each bin index to its frequency in Hz
    - Used as a lookup table by downstream functions
  
  Access example:
    freqs[{peak_bin_frame0}] = {freqs[peak_bin_frame0]:.2f} Hz
    (Frequency value for bin {peak_bin_frame0})
""")

# ============================================================================
# STEP 7: Visualization prep
# ============================================================================
print("\n" + "=" * 80)
print("STEP 7: How downstream functions use these outputs")
print("=" * 80)

print("""
After _stft_db returns (mag_db, freqs), here's what happens next:

_frame_peaks() function:
  1. Receives mag_db[:, frame] - spectral slice for ONE time frame
  2. Finds local peaks using scipy.signal.find_peaks()
  3. Returns peak_indices (bin numbers)
  4. Maps indices to frequencies: freqs[peak_indices]
  
Example - if we find peaks at bins [20, 100, 500]:
  peak_freqs = freqs[[20, 100, 500]]
  peak_freqs = [{freqs[20]:.1f}, {freqs[100]:.1f}, {freqs[500]:.1f}] Hz

_process_frames() function:
  1. Loops through all frames
  2. For each frame, calls _frame_peaks(mag_db[:, frame], freqs, threshold)
  3. Collects all peaks across all frames
  4. Matches peaks between reference and user audio
  5. Computes frequency and amplitude errors

Full pipeline:
  y_ref → _stft_db() → mag_db_ref, freqs_ref → _frame_peaks() → peak_freqs_ref
     ↓                                                               ↓
  y_user → _stft_db() → mag_db_user, freqs_user → _frame_peaks() → peak_freqs_user
                                                                      ↓
                                        _match_peaks() → error in cents
""")

# ============================================================================
# STEP 8: Summary statistics
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

print(f"""
Input Signal:
  Duration: {DURATION} seconds
  Samples: {len(y):,}
  Test frequency: {FREQUENCY} Hz

Transform Parameters:
  Window size: {N_FFT} samples = {N_FFT / SR:.4f} seconds
  Window overlap: {HOP_LENGTH} samples = {HOP_LENGTH / SR:.4f} seconds
  Frequency resolution: {SR / N_FFT:.2f} Hz per bin
  Time resolution: {HOP_LENGTH / SR:.4f} seconds per frame

Output Dimensions:
  Frequency bins: {mag_db.shape[0]}
  Time frames: {mag_db.shape[1]}
  Total values in mag_db: {mag_db.size:,}
  Total values in freqs: {freqs.size}

Energy Distribution:
  Quietest frequency: {mag_db.min():.2f} dB (at bin {np.unravel_index(mag_db.argmin(), mag_db.shape)[0]})
  Loudest frequency: {mag_db.max():.2f} dB (at bin {np.unravel_index(mag_db.argmax(), mag_db.shape)[0]})
  Mean energy: {mag_db.mean():.2f} dB
  
Test Signal Result:
  Created: {FREQUENCY} Hz sine wave
  Detected peak: {peak_freq:.2f} Hz (error: {abs(peak_freq - FREQUENCY):.2f} Hz)
  Peak energy: {peak_energy:.2f} dB
""")

print("\n✅ End of walkthrough. Modify parameters at the top and rerun to experiment!")
