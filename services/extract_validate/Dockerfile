FROM python:3.11-slim
WORKDIR /app

COPY packages/schemas /tmp/schemas
RUN pip install --no-cache-dir -e /tmp/schemas

COPY packages/llm_protos /tmp/llm_protos
RUN pip install --no-cache-dir --no-binary llm-protos /tmp/llm_protos

COPY services/extract_validate/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# enforce runtime match
RUN pip install --no-cache-dir "protobuf==5.29.5"

COPY services/extract_validate/app ./app

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
