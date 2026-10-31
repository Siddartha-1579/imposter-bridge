# Imposter Word 🕵️

A real-time multiplayer party game where friends deduce the secret word, spot the imposter, or bluff their way to victory from their phones or laptops with a 4-letter room code. No login, no downloads, zero friction.

---

## ⚡ Quick Start (Local Run in 2 Commands)

### Option 1: Using Docker (One command)
```bash
docker build -t imposter-word . && docker run -p 8000:8000 imposter-word
```
Visit `http://localhost:8000`.

### Option 2: Using Python & Node
```bash
# 1. Install & build
uv pip install -r requirements.txt && (cd frontend && npm install && npm run build)

# 2. Run
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```
Visit `http://localhost:8000`.

---

## 🚀 One-Click Deployment (Render / Railway)

### Deploying to Render
1. Push this repository to GitHub or GitLab.
2. In [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Blueprint**.
3. Connect your repository. Render reads `render.yaml` automatically and configures the web service using the Dockerfile with `/health` check.
4. Click **Apply**. Once built, your game is live on a single public URL (e.g. `https://imposter-word.onrender.com`).

### Deploying to Railway
1. In [Railway](https://railway.app/), click **New Project** -> **Deploy from GitHub repo**.
2. Railway detects the `Dockerfile` and builds both frontend and backend automatically.
3. In **Settings**, add port `8000` and healthcheck path `/health`.
4. Generate a public domain under **Networking**.

---

## 🧪 Testing & Simulation

### Run Pytest Unit Tests
```bash
pytest backend/tests/test_game.py -v
```
Tests cover:
- Scoring matrix (imposter escape +3, caught + correct guess +2, caught + wrong guess voters +2 / crew +1)
- Vote tie-breaking (tie = imposter not caught)
- Fair imposter rotation across rounds
- State personalization & zero-leak privacy for imposter, crew, and spectators
- Host migration on disconnect
- Seamless token-based reconnection
- Crew vs Imposter clue validation rules
- Pause & resume on low connected players (<3)

### Run 4-Client Automated Simulation
```bash
python -m backend.tests.simulate
```
Simulates 4 WebSocket clients playing a full 5-round game, including simulated mid-game network disconnection and seat reconnection, printing the round scores and final leaderboard.

---

## 📐 Architecture & Decisions Summary
The architecture uses a single FastAPI process hosting WebSockets at `/ws` and serving static Vite/React production assets from `/`. State is strictly held on the server and broadcast via personalized snapshots after every mutation (filtering `secret_word` and `imposter_id` prior to `REVEAL`). A 20-second heartbeat ping detects dropouts without client polling. Per the specification amendments: authentication uses split IDs (public player `id` vs private secret `reconnect_token`), crew cannot use the secret word as a clue while the imposter has no rejection leaks, games pause when fewer than 3 players are connected, and vote ties favor the imposter.
