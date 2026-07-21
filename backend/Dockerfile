# Single-image build: compile the React SPA, then serve it from FastAPI.
FROM node:20-alpine AS frontend

WORKDIR /ui

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8417

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY test_set/ ./test_set/
COPY --from=frontend /ui/dist ./frontend/dist

WORKDIR /app/backend

EXPOSE 8417

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/api/health\")"

# Shell form so $PORT is expanded and can be overridden at run time.
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
