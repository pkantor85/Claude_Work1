# ============================================================
# Dockerfile — BigQuery Data Analytics Agent (Streamlit)
# ============================================================
# Optimised for fast Cloud Run cold starts.
# ============================================================

FROM python:3.11-slim AS base

# Prevent .pyc files at build time (we compile explicitly below)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install system deps (curl for healthcheck) ───────────

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ──────────────────────────
# Separate layer so code changes don't re-install deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application ──────────────────────────────────────

COPY src/ src/
COPY ui/ ui/
COPY config/ config/
COPY scripts/ scripts/

# ── Streamlit configuration ───────────────────────────────

COPY .streamlit/ .streamlit/

RUN mkdir -p /root/.streamlit && \
  printf '[server]\nheadless = true\nport = 8080\nenableCORS = false\nenableXsrfProtection = false\nfileWatcherType = "none"\n\n[browser]\ngatherUsageStats = false\n' > /root/.streamlit/config.toml

# ── Pre-compile bytecode for faster startup ───────────────

RUN python -m compileall -q src/ ui/ scripts/ 2>/dev/null || true

# ── Pre-warm: import heavy modules once to verify ─────────

RUN python -c "import streamlit; import pandas; import altair; import google.cloud.storage; print('Pre-warm OK')"

# ── Expose port ───────────────────────────────────────────

EXPOSE 8080

# ── Health check ──────────────────────────────────────────

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/_stcore/health || exit 1

# ── Run ───────────────────────────────────────────────────

ENTRYPOINT ["streamlit", "run", "ui/app.py", \
  "--server.port=8080", \
  "--server.address=0.0.0.0", \
  "--server.headless=true", \
  "--server.fileWatcherType=none", \
  "--server.runOnSave=false"]
