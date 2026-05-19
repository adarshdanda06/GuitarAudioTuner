import React, { useState } from 'react';
import AudioPanel from './components/AudioPanel';
import ResultsPanel from './components/ResultsPanel';
import { analyzeFiles } from './api';
import './index.css';

export default function App() {
  const [userFile, setUserFile] = useState(null);
  const [refFile, setRefFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onUserReady = (file) => {
    setUserFile(file);
    setAnalysis(null);
    setError(null);
  };
  const onRefReady = (file) => {
    setRefFile(file);
    setAnalysis(null);
    setError(null);
  };

  const canAnalyze = userFile && refFile && !loading;

  const handleAnalyze = async () => {
    if (!canAnalyze) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeFiles(refFile, userFile, {});
      // map server result to ResultsPanel shape
      const figs = result.figures || {};
      const images = [figs.f1, figs.f2, figs.f3, figs.f4].filter(Boolean);
      const durationMs = result.duration ? Math.round(result.duration * 1000) : null;
      const meanError = result.mean_combined_error ?? result.mean_combined ?? null;
      setAnalysis({ images, durationMs, meanError, raw: result });
    } catch (err) {
      console.error(err);
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>Guitar Audio Tuner</h1>
      </header>

      <main className="layout">
        <section className="left">
          <AudioPanel onUserReady={onUserReady} onRefReady={onRefReady} />
          <div className="analyze-controls">
            <button className="analyze-button" onClick={handleAnalyze} disabled={!canAnalyze}>
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
            <div className="status">
              {!userFile && <div className="hint">Upload or record user audio</div>}
              {!refFile && <div className="hint">Upload reference audio</div>}
              {error && <div className="error">Error: {error}</div>}
            </div>
          </div>
        </section>

        <aside className="right">
          {analysis ? (
            <ResultsPanel analysis={{ images: analysis.images, durationMs: analysis.durationMs, meanError: analysis.meanError }} />
          ) : (
            <div className="placeholder-card">No analysis yet. Load both files and click Analyze.</div>
          )}
        </aside>
      </main>
    </div>
  );
}
