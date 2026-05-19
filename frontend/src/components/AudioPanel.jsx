import React, { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { convertFile } from "../api";

export default function AudioPanel({ onUserReady = () => {}, onRefReady = () => {} }) {
  const userContainer = useRef(null);
  const refContainer = useRef(null);
  const userWaves = useRef(null);
  const refWaves = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const [userFileName, setUserFileName] = useState(null);
  const [refFileName, setRefFileName] = useState(null);
  const [userReady, setUserReady] = useState(false);
  const [refReady, setRefReady] = useState(false);

  useEffect(() => {
    userWaves.current = WaveSurfer.create({
      container: userContainer.current,
      waveColor: "#6EE7B7",
      progressColor: "#10B981",
      height: 80,
    });
    refWaves.current = WaveSurfer.create({
      container: refContainer.current,
      waveColor: "#93C5FD",
      progressColor: "#3B82F6",
      height: 80,
    });

    return () => {
      try {
        userWaves.current.destroy();
      } catch (e) {}
      try {
        refWaves.current.destroy();
      } catch (e) {}
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Helpers to load blobs/files into wavesurfer
  const loadIntoWave = async (wsInstance, fileOrUrl) => {
    if (!wsInstance) return;
    wsInstance.empty();
    if (typeof fileOrUrl === "string") {
      wsInstance.load(fileOrUrl);
    } else {
      // file or blob
      const url = URL.createObjectURL(fileOrUrl);
      wsInstance.load(url);
      // revoke after a short delay when decoded
      wsInstance.on("ready", () => {
        setTimeout(() => URL.revokeObjectURL(url), 2000);
      });
    }
  };

  // Play/pause toggles
  const togglePlay = (wsInstance) => {
    if (!wsInstance) return;
    wsInstance.playPause();
  };

  // User file selection (upload)
  const handleUserFile = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    // If MP4 or video, call convert endpoint
    if (file.type.includes("mp4") || file.type.includes("video")) {
      try {
        const mp3File = await convertFile(file);
        setUserFileName(mp3File.name || "user.mp3");
        await loadIntoWave(userWaves.current, mp3File);
        setUserReady(true);
        onUserReady(mp3File);
      } catch (err) {
        console.error("Conversion failed", err);
        alert("Conversion failed: " + err.message);
      }
    } else {
      // audio file
      setUserFileName(file.name);
      await loadIntoWave(userWaves.current, file);
      setUserReady(true);
      onUserReady(file);
    }
  };

  // Reference file selection
  const handleRefFile = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setRefFileName(file.name);
    await loadIntoWave(refWaves.current, file);
    setRefReady(true);
    onRefReady(file);
  };

  // Recording
  const startRecording = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Media devices / getUserMedia not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const mr = new MediaRecorder(stream);
      const chunks = [];
      mr.ondataavailable = (ev) => {
        if (ev.data && ev.data.size) chunks.push(ev.data);
      };
      mr.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        // Create a file from blob
        const file = new File([blob], "recording.webm", { type: blob.type });
        setUserFileName(file.name);
        await loadIntoWave(userWaves.current, file);
        setUserReady(true);
        onUserReady(file);
      };
      mediaRecorderRef.current = mr;
      mr.start();
    } catch (err) {
      console.error("Failed to start recorder", err);
      alert("Failed to access microphone: " + err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
  };

  return (
    <div className="audio-panel">
      <div className="audio-section">
        <h3>User Audio</h3>
        <div className="controls">
          <input type="file" accept="audio/*,video/mp4" onChange={handleUserFile} />
          <div className="record-controls">
            <button onClick={startRecording}>Start Recording</button>
            <button onClick={stopRecording}>Stop Recording</button>
          </div>
        </div>
        <div className="waveform" ref={userContainer}></div>
        <div className="section-footer">
          <button onClick={() => togglePlay(userWaves.current)} disabled={!userReady}>
            Play/Pause
          </button>
          <span className="filename">{userFileName || "No file"}</span>
        </div>
      </div>

      <div className="audio-section">
        <h3>Reference Audio</h3>
        <div className="controls">
          <input type="file" accept="audio/*" onChange={handleRefFile} />
        </div>
        <div className="waveform" ref={refContainer}></div>
        <div className="section-footer">
          <button onClick={() => togglePlay(refWaves.current)} disabled={!refReady}>
            Play/Pause
          </button>
          <span className="filename">{refFileName || "No file"}</span>
        </div>
      </div>
    </div>
  );
}
