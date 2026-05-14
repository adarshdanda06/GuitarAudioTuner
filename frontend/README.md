# Frontend (Vite + React)

Quick start

cd frontend
npm install
npm run dev

The dev server (Vite) typically serves at http://localhost:5173.

API configuration

The frontend's API helper (src/api.js) calls the backend at `/convert` and `/analyze` (same-origin). In development you can:

- Run the backend on http://127.0.0.1:5000 and modify src/api.js to use the full URL (e.g., fetch('http://127.0.0.1:5000/convert')).
- Or configure a Vite proxy in vite.config.js to forward `/convert` and `/analyze` to the backend.

Build

npm run build
npm run start  # preview build

Notes
- The backend requires the `ffmpeg` binary (see backend/README.md). The frontend itself does not need ffmpeg but it relies on the backend for conversions.
