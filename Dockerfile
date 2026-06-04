# True Cost of Flying — read-only Streamlit app.
# All heavy physics (ERA5 + CoCiP) is precomputed offline in batch/; this image only reads
# the small committed data/processed/* and renders. No DB, no API keys required.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so this layer is cached unless requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App + theme + the precomputed data only (cache/raw are excluded via .dockerignore and
# not copied here — they are offline-build artefacts, ~500 MB, never needed at runtime).
COPY app.py ./
COPY .streamlit ./.streamlit
COPY data/processed ./data/processed

EXPOSE 8501

# Streamlit's built-in health endpoint returns the body "ok". curl isn't in python:slim,
# so probe with the stdlib. Coolify/Traefik use container health to gate routing.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()==b'ok' else 1)"

# headless: no 'open browser' / email prompt. Served at the domain root, so no baseUrlPath.
# If the page loads but stays stuck on "Connecting…" behind the proxy, add
# "--server.enableCORS=false" and "--server.enableXsrfProtection=false" below.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
