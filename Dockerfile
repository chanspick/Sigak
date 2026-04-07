FROM python:3.12-slim

# OpenCV, MediaPipe, InsightFace 시스템 의존성 + C++ 컴파일러 (insightface 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    build-essential g++ wget unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 배포용 경량 의존성 (torch 제외)
COPY sigak/requirements-deploy.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# InsightFace buffalo_l 모델 미리 다운로드 (런타임 다운로드 방지)
RUN mkdir -p /root/.insightface/models && \
    wget -q https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip \
    -O /tmp/buffalo_l.zip && \
    unzip -q /tmp/buffalo_l.zip -d /root/.insightface/models/ && \
    rm /tmp/buffalo_l.zip

COPY sigak/ ./

ENV PYTHONPATH=/app
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
