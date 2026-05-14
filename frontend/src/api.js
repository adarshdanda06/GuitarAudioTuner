// frontend/src/api.js
// Small helper functions to call backend endpoints.
// Usage:
//   // Convert a single input file to MP3 (returns a File object)
//   const mp3File = await convertFile(inputFile);
//
//   // Analyze two audio files with optional params
//   const result = await analyzeFiles(referenceFile, userFile, { pitchTolerance: 0.5 });

// Upload helper left as a placeholder for other features
export async function uploadAudio(file) {
  // Not used by current UI; implement when needed.
  return null;
}

// Sends a file to POST /convert using FormData('file')
// Returns a File (audio/mpeg) created from the response blob.
export async function convertFile(file) {
  if (!file) throw new Error('convertFile: file required');
  const fd = new FormData();
  // Use provided file name when available
  fd.append('file', file, file.name || 'input');

  let res;
  try {
    res = await fetch('/convert', {
      method: 'POST',
      body: fd,
    });
  } catch (err) {
    throw new Error(`Network error while converting file: ${err.message}`);
  }

  if (!res.ok) {
    // Try to extract JSON or text error message
    let errMsg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      errMsg += `: ${data.message || JSON.stringify(data)}`;
    } catch (e) {
      const text = await res.text();
      if (text) errMsg += `: ${text}`;
    }
    throw new Error(`Convert failed: ${errMsg}`);
  }

  // Response should be binary MP3 data
  const blob = await res.blob();
  // Derive filename from original file
  const baseName = (file && file.name) ? file.name.replace(/\.[^.]+$/, '') : 'converted';
  const filename = `${baseName}.mp3`;
  try {
    return new File([blob], filename, { type: 'audio/mpeg' });
  } catch (e) {
    // Some environments may not support File constructor; return Blob with name property fallback
    blob.name = filename;
    return blob;
  }
}

// Sends two files to POST /analyze with fields 'reference_audio' and 'user_audio'.
// Optional params is a plain object; its keys/values will be appended to the FormData.
// Returns parsed JSON from the server.
export async function analyzeFiles(refFile, userFile, params = {}) {
  if (!refFile || !userFile) throw new Error('analyzeFiles: refFile and userFile are required');
  const fd = new FormData();
  fd.append('reference_audio', refFile, refFile.name || 'reference');
  fd.append('user_audio', userFile, userFile.name || 'user');

  // Append optional params (scalars). Objects/arrays will be JSON-stringified.
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    if (typeof v === 'object') fd.append(k, JSON.stringify(v));
    else fd.append(k, String(v));
  });

  let res;
  try {
    res = await fetch('/analyze', {
      method: 'POST',
      body: fd,
    });
  } catch (err) {
    throw new Error(`Network error while analyzing files: ${err.message}`);
  }

  const text = await res.text();
  if (!res.ok) {
    // Try to include server message in the error
    let serverMsg = text || `HTTP ${res.status}`;
    try {
      const json = JSON.parse(text);
      serverMsg = json.message || JSON.stringify(json);
    } catch (e) {
      // not JSON
    }
    throw new Error(`Analyze failed: ${serverMsg}`);
  }

  // Parse JSON response (server should return JSON)
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`Failed to parse analyze response as JSON: ${err.message}`);
  }
}
