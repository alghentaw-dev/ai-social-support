# services/score/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY services/score/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

COPY services/score /app

ENV SCORE_MODEL_DIR=/app/models/eligibility_v1
EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
