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

# BiSeNet face parsing 모델 다운로드 (헤어컬러 시뮬레이션용, ~53MB)
RUN mkdir -p /app/models && \
    wget -q -L https://github.com/yakhyo/face-parsing/releases/download/weights/resnet18.onnx \
    -O /app/models/bisenet_face_parsing.onnx && \
    test -s /app/models/bisenet_face_parsing.onnx && \
    echo "[OK] BiSeNet model downloaded ($(du -h /app/models/bisenet_face_parsing.onnx | cut -f1))" || \
    (rm -f /app/models/bisenet_face_parsing.onnx && echo "[WARN] BiSeNet 다운로드 실패 — 헤어 시뮬레이션 비활성")

COPY sigak/ ./

ENV PYTHONPATH=/app
# ⚠️ TEMP (recovery mode): alembic 실패해도 uvicorn 부팅.
# DB 스키마와 alembic_version 이 수동 ALTER로 디싱크된 상태를 진단·복구하기
# 위한 일시 완화. `/api/v1/_debug/schema-state` 호출로 상태 확인 후,
# 수동 복구 완료되면 &&로 다시 조여야 함. TODO(ops): 복구 종료 후 strict 복원.
CMD echo "[startup] alembic upgrade head (non-blocking recovery mode)" ; \
    python -m alembic upgrade head ; \
    echo "[startup] continuing to uvicorn regardless of migration exit" ; \
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
