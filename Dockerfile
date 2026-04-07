FROM python:3.12-slim

# OpenCV, MediaPipe, InsightFace 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY sigak/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sigak/ ./

# Railway 환경변수에서 설정을 읽음 (.env 파일 불필요)
ENV PYTHONPATH=/app
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
