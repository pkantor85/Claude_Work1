# ============================================================
# Dockerfile — BigQuery Data Analytics Agent (Streamlit)
# ============================================================
# Multi-stage build for a lean Cloud Run container.
# ============================================================

FROM python:3.11-slim AS base

# Prevent .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies ──────────────────────────────────

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application ──────────────────────────────────────

COPY src/ src/
COPY ui/ ui/
COPY config/ config/
COPY scripts/ scripts/

# ── Streamlit configuration ───────────────────────────────

COPY .streamlit/ .streamlit/

# Streamlit expects a config dir; create defaults
RUN mkdir -p /root/.streamlit && \
  echo '[server]\n\
  headless = true\n\
  port = 8080\n\
  enableCORS = false\n\
  enableXsrfProtection = false\n\
  ' > /root/.streamlit/config.toml

# ── Expose port ───────────────────────────────────────────

EXPOSE 8080

# ── Health check ──────────────────────────────────────────

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/_stcore/health || exit 1

# ── Run ───────────────────────────────────────────────────

ENTRYPOINT ["streamlit", "run", "ui/app.py", \
  "--server.port=8080", \
  "--server.address=0.0.0.0", \
  "--server.headless=true"]
