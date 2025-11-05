FROM python:3.11-slim

WORKDIR /app

# install shared schemas first to leverage layer caching
COPY ../../packages/schemas /tmp/schemas
RUN pip install --no-cache-dir -e /tmp/schemas

COPY services/documents/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/documents/app ./app

ENV DOCS_PORT=8001
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
