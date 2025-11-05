FROM python:3.11-slim
WORKDIR /app

# shared packages
COPY packages/schemas /tmp/schemas
RUN pip install --no-cache-dir -e /tmp/schemas

COPY packages/llm_protos /tmp/llm_protos
RUN pip install --no-cache-dir /tmp/llm_protos

# app deps
COPY services/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY services/orchestrator/app ./app
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
