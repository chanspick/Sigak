FROM python:3.12-slim

# OpenCV, MediaPipe, InsightFace 시스템 의존성 + C++ 컴파일러 (insightface 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    build-essential g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 배포용 경량 의존성 (torch 제외)
COPY sigak/requirements-deploy.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY sigak/ ./

ENV PYTHONPATH=/app
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
