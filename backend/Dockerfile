# ============================================================
# PatchForge for Linux
# Production multi-stage image
# ============================================================


# ------------------------------------------------------------
# Stage 1: Build React frontend
# ------------------------------------------------------------

FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
COPY frontend/tsconfig.json ./
COPY frontend/vite.config.ts ./
COPY frontend/index.html ./
COPY frontend/public ./public
COPY frontend/src ./src

RUN npm install
RUN npm run build

# Fail the image build if the frontend was not created.
RUN test -f /frontend/dist/index.html


# ------------------------------------------------------------
# Stage 2: PatchForge backend + built frontend
# ------------------------------------------------------------

FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./requirements.txt

RUN pip install \
    --no-cache-dir \
    -r requirements.txt

COPY backend/app ./app

COPY --from=frontend-builder \
    /frontend/dist \
    /app/frontend

# Fail the image build if the frontend was not copied.
RUN test -f /app/frontend/index.html

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
