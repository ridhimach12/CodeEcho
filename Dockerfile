# ==========================================
# Stage 1: Build React/Vite Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend & Runner
# ==========================================
FROM python:3.12-slim AS runner

# Install git CLI (mandatory for git clone & repository mining)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code
COPY backend ./backend

# Copy built frontend assets
COPY --from=frontend-builder /build/dist ./frontend/dist

# Create persistent data and temp directory mounts
RUN mkdir -p /app/data /app/temp_clones

# Default environment configuration
ENV ENVIRONMENT=production \
    PORT=8000 \
    HOST=0.0.0.0 \
    DATABASE_URL=sqlite:////app/data/codeecho.db \
    SERVE_FRONTEND=true \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    TEMP_DIR_ROOT=/app/temp_clones \
    PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
