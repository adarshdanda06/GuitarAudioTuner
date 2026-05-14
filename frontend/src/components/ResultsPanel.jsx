import React from 'react';
import './ResultsPanel.css';

/**
 * ResultsPanel
 * Props:
 *  - analysis: {
 *      images: [base64PNGString,...],
 *      durationMs: number,
 *      duration: number, // optional alias
 *      errors: [number,...],
 *      meanError: number // optional
 *    }
 */
export default function ResultsPanel({ analysis = {} }) {
  const images = Array.isArray(analysis.images) ? analysis.images : [];
  const duration = analysis.durationMs ?? analysis.duration ?? null;
  const errorsArr = Array.isArray(analysis.errors) ? analysis.errors : (Array.isArray(analysis.errorList) ? analysis.errorList : []);
  const meanError = typeof analysis.meanError === 'number'
    ? analysis.meanError
    : (errorsArr.length ? (errorsArr.reduce((a, b) => a + b, 0) / errorsArr.length) : null);

  const toDataUrl = (b64) => {
    if (!b64) return null;
    return b64.startsWith('data:') ? b64 : `data:image/png;base64,${b64}`;
  };

  return (
    <div className="results-panel">
      <div className="images-grid">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="image-card">
            {images[i] ? (
              <img src={toDataUrl(images[i])} alt={`result-${i + 1}`} />
            ) : (
              <div className="placeholder">No image</div>
            )}
          </div>
        ))}
      </div>

      <div className="summary-card">
        <h3>Summary</h3>
        {duration != null ? (
          <p><strong>Duration:</strong> {Math.round(duration)} ms</p>
        ) : (
          <p><strong>Duration:</strong> —</p>
        )}

        {meanError != null ? (
          <p><strong>Mean error:</strong> {Number(meanError).toFixed(3)}</p>
        ) : (
          <p><strong>Mean error:</strong> —</p>
        )}

        {analysis.note && <p className="note">{analysis.note}</p>}
      </div>
    </div>
  );
}
