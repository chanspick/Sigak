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
# alembic upgrade head 를 uvicorn 앞에 실행 — 새 migration 자동 반영.
# 실패 시 &&로 uvicorn 부팅 차단 → Railway restart 루프가 health check 실패로 가시화.
# DATABASE_URL은 Railway 대시보드에서 주입되며 alembic/env.py 가 런타임 로드.
CMD echo "[startup] alembic upgrade head" && \
    alembic upgrade head && \
    echo "[startup] migrations applied, starting uvicorn" && \
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
