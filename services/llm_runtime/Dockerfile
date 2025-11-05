FROM python:3.11-slim

WORKDIR /srv

# 1) Install runtime deps first (better cache)
COPY services/llm_runtime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Install shared LLM protos (provides `llmruntime.v1.*` stubs)
COPY packages/llm_protos /tmp/llm_protos
# Build our local package from source, allow wheels for deps
RUN pip install --no-cache-dir --no-binary llm-protos /tmp/llm_protos

# 3) Enforce protobuf runtime to match the stubs (5.x)
RUN pip install --no-cache-dir "protobuf==5.29.5"

# 4) Copy service source
COPY services/llm_runtime /srv


EXPOSE 51051
CMD ["python", "-m", "app.server"]
