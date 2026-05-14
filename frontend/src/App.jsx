import React from 'react';
import Waveform from './components/Waveform';

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>Guitar Audio Tuner</h1>
      </header>
      <main>
        <Waveform />
      </main>
    </div>
  );
}
