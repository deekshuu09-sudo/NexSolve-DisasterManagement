# NexSolve Disaster Management System — Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for data libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application code & data resources
COPY backend /app/backend

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI backend server using uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
