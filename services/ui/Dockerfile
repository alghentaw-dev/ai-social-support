# ===== UI image (root Dockerfile) =====
FROM python:3.11-slim AS ui

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Put the UI under /app/ui to match your layout
WORKDIR /app/ui

# <-- CHANGED: copy requirements from services/ui/
COPY services/ui/requirements.txt /app/ui/requirements.txt
RUN pip install --no-cache-dir -r /app/ui/requirements.txt

# Copy just the UI code (faster builds)
COPY services/ui /app/ui
# (Optional) if your app reads a .env at runtime:
# COPY .env /app/ui/.env

ENV STREAMLIT_SERVER_PORT=8501 \
    PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
