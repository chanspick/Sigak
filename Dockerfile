FROM python:3.11-slim

# OpenCV, MediaPipe, InsightFace 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY sigak/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sigak/ ./sigak/

# Railway는 PORT 환경변수를 설정한다
CMD uvicorn sigak.main:app --host 0.0.0.0 --port ${PORT:-8000}
