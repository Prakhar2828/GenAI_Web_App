# Stage 1: build React
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Ollama + Python + your app
FROM ollama/ollama:latest

# Install Python, pip, build tools, zip (for zipping results)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip build-essential zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install your Python deps (including Gunicorn)
COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt gunicorn

# Copy your backend code
COPY backend/ ./

# Copy the React build
COPY --from=frontend-builder /app/frontend/build frontend/build

# Expose both ports: Flask + Ollama
EXPOSE 5000 11434

# Flask env
ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Drop any inherited ENTRYPOINT
ENTRYPOINT []

# Start Ollama, wait, pull the model, then launch Gunicorn with a long timeout
CMD ["sh", "-c", "\
    ollama serve & \
    sleep 10 && \
    ollama pull llama2:7b && \
    exec gunicorn app:app \
      --bind 0.0.0.0:5000 \
      --workers 1 \
      --timeout 500 \
"]
