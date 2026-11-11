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

The following are excluded by `.gitignore` and are never pushed: `.venv/`, the `data/` folder (database, uploads, reports) and `.streamlit/secrets.toml`.

## 2. Streamlit Community Cloud (free, recommended)

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

## 3. Run on your laptop for a live demo (most reliable)

```bash
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
streamlit run app.py
```

To let others on the same Wi-Fi open it (for example, from a phone):

```bash
streamlit run app.py --server.address 0.0.0.0
```

Then open `http://<your-laptop-ip>:8501`.

**Before an interview:** start the app 10 minutes early, click **Data Manager → Refresh entire universe** so quotes are fresh, and keep a generated PDF report ready as a backup.

## 4. Automatic data refresh on your computer

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

## 5. Other hosts

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
| `ANTHROPIC_API_KEY` | secrets or environment | Optional, paid Claude engine |
| `.streamlit/config.toml` | file | Theme, upload size limit (50 MB) |
