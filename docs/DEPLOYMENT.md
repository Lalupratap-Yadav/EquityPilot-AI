# Deployment guide

## 1. Put the code on GitHub (one-time)

The project is already a Git repository with a full commit history.

1. Sign in at https://github.com and click **New repository**.
2. Name it `EquityPilot-AI`. Leave **all** "initialize" options unticked (no README, no .gitignore, no licence).
3. In a terminal inside the project folder, run:

```bash
git remote add origin https://github.com/<your-username>/EquityPilot-AI.git
git push -u origin main
```

The following are excluded by `.gitignore` and are never pushed: `.venv/`, the `data/` folder (database, uploads, reports, the session secret), `web/node_modules/`, `web/dist/`, `.env` and `.streamlit/secrets.toml`. Never commit API keys or passwords.

## 2. EquityPilot v2 (FastAPI + React) – run anywhere

### Locally

```bash
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 (or `http://<your-laptop-ip>:8000` from a phone on the same Wi-Fi). One process serves both the API and the built frontend.

### Docker / container hosts (Render, Railway, Fly.io, a VM)

```bash
docker build -t equitypilot .
docker run -p 8000:8000 -v equitypilot-data:/app/data   -e EQUITYPILOT_SECRET="<a long random string>" -e EQUITYPILOT_SECURE_COOKIES=1 equitypilot
```

The Dockerfile has not been build-tested on the development machine (Docker was not installed). It contains a two-stage build: Node builds `web/dist`, then a slim Python image runs uvicorn as a non-root user with a health check on `/api/health`.

**Hosting checklist**
- **Persistent data:** mount a volume at `/app/data`. Without one, users, watchlists, Virtual Invest accounts and uploads are lost on every restart. For a managed database, set `EQUITYPILOT_DATABASE_URL` (PostgreSQL; this path is implemented but untested against a live server).
- **HTTPS:** serve behind HTTPS (most hosts provide it) and set `EQUITYPILOT_SECURE_COOKIES=1`.
- **Secret:** set `EQUITYPILOT_SECRET` so that sessions survive redeploys.
- **AI key:** do **not** set `ANTHROPIC_API_KEY` on a public deployment unless you also set `EQUITYPILOT_SHARED_AI_KEY=1` and accept that every visitor spends your credit. Without that flag, each user enters their own key.
- **Free tiers:** these often sleep when idle. The first request after waking is slow while the caches warm.
- **Yahoo rate limits:** Yahoo Finance may rate-limit shared cloud IPs. The app keeps serving cached data and labels it with its timestamp.

## 3. Classic workbench on Streamlit Community Cloud (free)

The original Streamlit app (`app.py`) still works and can be hosted for free. It does not include the v2 features (accounts, Virtual Invest, news feeds, Industry Intelligence Centre).

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app → Deploy a public app from GitHub**.
3. Repository: `<your-username>/EquityPilot-AI`; branch: `main`; main file path: `app.py`.
4. Under **Advanced settings**, choose a Python version (3.12 or later works).
5. *(Optional, paid)* To enable the Claude engine for everyone using the app, add this under **Secrets**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   Leave this out to keep the app free (the offline analyst works without it). A public app with your key would let visitors spend your API credit, so for a public demo prefer leaving it unset or deploying a private app.
6. Click **Deploy**. The first build takes a few minutes.

**What to expect on the free tier**
- The SQLite database is **ephemeral**: it resets when the app restarts or sleeps. Sample companies reload automatically, and real companies are fetched again on demand (or via **Load default research universe**).
- Apps sleep after a period of inactivity; the first visit wakes them.
- Yahoo Finance may rate-limit requests from shared cloud servers. If fetches fail, wait and retry; the app keeps working with whatever is cached.

## 4. Run on your laptop for a live demo (most reliable)

```bash
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
streamlit run app.py
```

To let others on the same Wi-Fi open it (for example, from a phone):

```bash
streamlit run app.py --server.address 0.0.0.0
```

Then open `http://<your-laptop-ip>:8501`.

**Before an interview:** start the app 10 minutes early so the background task refreshes quotes and feeds, and keep a generated PDF report ready as a backup. (For the classic workbench, click **Data Manager → Refresh entire universe**.)

## 5. Automatic data refresh on your computer

Windows (Task Scheduler) - refresh quotes every weekday at 16:00 IST after market close:

Run this in **Command Prompt** (cmd), replacing `<project-folder>` with the full path of the project:

```bat
schtasks /Create /TN "EquityPilot refresh" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:00 /TR "\"<project-folder>\.venv\Scripts\python.exe\" -m equitypilot refresh --quotes-only"
```

Set "Start in" to the project folder in Task Scheduler's task properties (so the `data` folder is found), or set the
`EQUITYPILOT_DATA_DIR` environment variable. A full refresh (`python -m equitypilot refresh`) is best run weekly.

macOS/Linux (cron):

```bash
0 16 * * 1-5 cd /path/to/EquityPilot-AI && .venv/bin/python -m equitypilot refresh --quotes-only
```

## 6. Other hosts for the classic workbench

Any platform that runs a Python web process works (Hugging Face Spaces, Render, Railway, a VM). The start command is:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

For persistent data, mount a disk and set `EQUITYPILOT_DATA_DIR` to a folder on it.

## Configuration reference

| Setting | Where | Purpose |
|---|---|---|
| `EQUITYPILOT_OFFLINE=1` | environment | No network calls; sample data only |
| `EQUITYPILOT_DATA_DIR` | environment | Folder for the database, uploads and reports (default `./data`) |
| `EQUITYPILOT_DB` | environment | Explicit database file path |
| `EQUITYPILOT_SECRET` | environment | v2 session-signing key (default: generated in `data/secret.key`) |
| `EQUITYPILOT_SECURE_COOKIES=1` | environment | v2: `Secure` cookies (use with HTTPS) |
| `EQUITYPILOT_DATABASE_URL` | environment | v2: PostgreSQL URL instead of SQLite (untested on a live server) |
| `EQUITYPILOT_NO_WARMER=1` | environment | v2: disable the background refresh task |
| `ANTHROPIC_API_KEY` | secrets or environment | Optional, paid Claude engine. In v2 it is used for all users only with `EQUITYPILOT_SHARED_AI_KEY=1` |
| `.streamlit/config.toml` | file | Theme, upload size limit (50 MB) |
