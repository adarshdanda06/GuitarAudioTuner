import React, { useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';

export default function Waveform() {
  const containerRef = useRef(null);
  const wavesurferRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    wavesurferRef.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#7c3aed',
      progressColor: '#a78bfa',
      height: 80,
    });

    return () => {
      wavesurferRef.current?.destroy();
    };
  }, []);

  return (
    <div className="waveform">
      <div ref={containerRef} />
      <p className="hint">Waveform will appear here once audio is loaded.</p>
    </div>
  );
}
