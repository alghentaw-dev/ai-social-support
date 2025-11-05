
FROM python:3.11-slim

WORKDIR /app

# System deps (optional, keep small)
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

ENV RECO_HOST=0.0.0.0
ENV RECO_PORT=8006
EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
