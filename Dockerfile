# EquityPilot AI v2 – FastAPI backend serving the built React app on one port.
#   docker build -t equitypilot .
#   docker run -p 8000:8000 -v equitypilot-data:/app/data equitypilot
# Optional env: EQUITYPILOT_SECRET (session signing key), EQUITYPILOT_SECURE_COOKIES=1 (behind HTTPS),
#               EQUITYPILOT_OFFLINE=1 (sample data only), EQUITYPILOT_DATABASE_URL (PostgreSQL),
#               ANTHROPIC_API_KEY + EQUITYPILOT_SHARED_AI_KEY=1 (paid, optional: lets every visitor use YOUR key)

# ---- 1. build the frontend
FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- 2. Python runtime
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY equitypilot/ equitypilot/
COPY api/ api/
COPY --from=web /web/dist web/dist
RUN useradd --create-home --uid 10001 app && mkdir -p data && chown app:app data
USER app
VOLUME ["/app/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
