# LectureMind AI — Frontend

React 19 app with Tailwind CSS + Radix UI.

This is the frontend for **LectureMind AI**. See the [root README](../README.md) for setup and usage.

## Local Dev

```bash
cd frontend
npm install --legacy-peer-deps
REACT_APP_BACKEND_URL=http://localhost:8001 npm start
```

Runs on [http://localhost:3000](http://localhost:3000).

## Production Build

```bash
npm run build
```

Served via nginx (see `Dockerfile` and `nginx.conf`).
