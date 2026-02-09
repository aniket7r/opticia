# Backend Dockerfile for Cloud Run
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Cloud Run sets PORT=8080 at runtime
# Run with uvicorn on whatever port Cloud Run assigns
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
