# EquityPilot AI – web frontend

React 19 + TypeScript + Vite + Tailwind CSS v4 single-page app. It talks only to the FastAPI backend in `../api` under `/api`.

```bash
npm install
npm run dev      # http://localhost:5173 – proxies /api (and the quotes WebSocket) to http://127.0.0.1:8000
npm run build    # type-check + production build into dist/, which FastAPI serves at http://localhost:8000
```

Start the backend first (from the project root): `python -m uvicorn api.main:app --port 8000`.

Layout: `src/pages/` one file per route (lazy-loaded) · `src/components/` shell, UI kit, charts, search · `src/lib/` API client, formatters, hooks.
