"""
SIGAK API — FastAPI Application (v2: 결제 후 분석 구조)

Flow:
  /submit  → 사진+질문지 저장 + order 생성 (AI 비용 0)
  /confirm → 관리자 결제확인 → AI 파이프라인 실행 → 리포트 생성
  /report  → 리포트 조회 (status 기반)
"""
import json
import os
import uuid
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import httpx

from db import init_db, get_db, User as DBUser, Order as DBOrder, Report as DBReport, Notification as DBNotification


def _use_db() -> bool:
    """Check if DB is available."""
    from db import SessionLocal
    return SessionLocal is not None

# 데이터 저장 디렉토리 (Railway 볼륨 마운트 경로를 env로 지정 가능)
DATA_DIR = Path(os.getenv("SIGAK_DATA_DIR", Path(os.path.dirname(__file__)) / "uploads"))
DATA_DIR.mkdir(exist_ok=True)


def _save_json(user_id: str, filename: str, data: dict):
    """유저별 JSON 데이터를 로컬 디스크에 저장."""
    user_dir = DATA_DIR / user_id
    user_dir.mkdir(exist_ok=True)
    with open(user_dir / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _load_json(user_id: str, filename: str) -> dict | None:
    """유저별 JSON 데이터 로드."""
    path = DATA_DIR / user_id / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _migrate_legacy_data():
    """기존 /app/uploads/ 데이터를 볼륨(DATA_DIR)으로 1회 마이그레이션."""
    import shutil
    legacy_dir = Path(os.path.dirname(__file__)) / "uploads"

    # DATA_DIR이 레거시 경로와 같으면 마이그레이션 불필요
    if legacy_dir.resolve() == DATA_DIR.resolve():
        return

    if not legacy_dir.exists():
        return

    # 볼륨에 이미 유저 데이터가 있으면 마이그레이션 스킵
    existing = [d for d in DATA_DIR.iterdir() if d.is_dir()] if DATA_DIR.exists() else []
    if existing:
        print(f"[MIGRATE] 볼륨에 이미 {len(existing)}개 디렉토리 존재, 스킵")
        return

    migrated = 0
    for item in legacy_dir.iterdir():
        dest = DATA_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
            migrated += 1
        else:
            shutil.copy2(item, dest)

    print(f"[MIGRATE] /app/uploads/ → {DATA_DIR}: {migrated}개 유저 마이그레이션 완료")


def _restore_stores():
    """서버 시작 시 디스크에 저장된 JSON에서 인메모리 스토어 복원."""
    restored = {"users": 0, "interviews": 0, "analyses": 0, "orders": 0, "reports": 0}

    if not DATA_DIR.exists():
        print("[RESTORE] DATA_DIR 없음, 스킵")
        return

    for user_dir in DATA_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name

        # user.json → USERS
        user_data = _load_json(user_id, "user.json")
        if user_data:
            USERS[user_id] = user_data
            restored["users"] += 1

        # booking.json → USERS (레거시 부킹 데이터도 복원)
        if not user_data:
            booking = _load_json(user_id, "booking.json")
            if booking:
                USERS[user_id] = booking
                restored["users"] += 1

        # interview.json → INTERVIEWS
        interview = _load_json(user_id, "interview.json")
        if interview:
            INTERVIEWS[user_id] = interview
            restored["interviews"] += 1

        # face_analysis.json → ANALYSES
        analysis = _load_json(user_id, "face_analysis.json")
        if analysis:
            ANALYSES[user_id] = analysis
            restored["analyses"] += 1

        # order.json → ORDERS
        order = _load_json(user_id, "order.json")
        if order and "order_id" in order:
            ORDERS[order["order_id"]] = order
            restored["orders"] += 1

        # report.json → REPORTS (report_id + user_id 둘 다 등록)
        report = _load_json(user_id, "report.json")
        if report and "id" in report:
            REPORTS[report["id"]] = report
            REPORTS[user_id] = report  # 하위호환: user_id로도 접근
            restored["reports"] += 1

    print(f"[RESTORE] 복원 완료: {restored}")


def _find_user(user_id: str) -> dict | None:
    """유저를 모든 저장소에서 조회: 인메모리 → DB → 디스크."""
    # 1. 인메모리
    if user_id in USERS:
        return USERS[user_id]
    # 2. DB
    if _use_db():
        db = get_db()
        try:
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if db_user:
                user = {
                    "id": db_user.id,
                    "name": db_user.name or "",
                    "phone": db_user.phone or "",
                    "gender": db_user.gender or "female",
                    "tier": db_user.tier or "standard",
                    "kakao_id": db_user.kakao_id or "",
                    "status": db_user.status or "booked",
                    "created_at": db_user.created_at.isoformat() + "Z" if db_user.created_at else "",
                }
                USERS[user_id] = user  # 인메모리 캐시
                return user
        except Exception as e:
            print(f"[FIND_USER] DB error: {e}")
        finally:
            db.close()
    # 3. 디스크
    user_data = _load_json(user_id, "user.json") or _load_json(user_id, "booking.json")
    if user_data:
        USERS[user_id] = user_data
        return user_data
    return None


def _find_all_user_ids(user_id: str) -> list[str]:
    """같은 kakao_id를 가진 모든 user_id를 반환 (중복 계정 병합용)."""
    user_ids = {user_id}
    if not _use_db():
        return list(user_ids)
    db = get_db()
    try:
        # 현재 유저의 kakao_id 조회
        db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if db_user and db_user.kakao_id:
            # 같은 kakao_id를 가진 모든 유저 검색
            siblings = db.query(DBUser).filter(DBUser.kakao_id == db_user.kakao_id).all()
            for s in siblings:
                user_ids.add(s.id)
    except Exception as e:
        print(f"[FIND_ALL_IDS] error: {e}")
    finally:
        db.close()
    return list(user_ids)


def _find_reports_for_user(user_id: str) -> list[dict]:
    """유저의 리포트를 모든 저장소에서 조회. kakao_id 기반 병합."""
    # 같은 카카오 계정의 모든 user_id 수집
    all_ids = _find_all_user_ids(user_id)
    reports_list = []
    seen_ids = set()

    # 1. DB 우선
    if _use_db():
        db = get_db()
        try:
            db_reports = db.query(DBReport)\
                .filter(DBReport.user_id.in_(all_ids))\
                .order_by(DBReport.created_at.desc())\
                .all()
            for r in db_reports:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    reports_list.append({
                        "id": r.id,
                        "access_level": r.access_level,
                        "created_at": r.created_at.isoformat() + "Z" if r.created_at else "",
                        "url": f"/report/{r.id}",
                    })
        except Exception as e:
            print(f"[FIND_REPORTS] DB error: {e}")
        finally:
            db.close()

    # 2. 인메모리 fallback
    if not reports_list:
        for rid, r in REPORTS.items():
            if r.get("user_id") in all_ids and rid not in all_ids and rid not in seen_ids:
                seen_ids.add(rid)
                reports_list.append({
                    "id": rid,
                    "access_level": r.get("access_level", "standard"),
                    "created_at": r.get("created_at", ""),
                    "url": f"/report/{rid}",
                })

    # 3. 디스크 fallback
    if not reports_list:
        for uid in all_ids:
            report_data = _load_json(uid, "report.json")
            if report_data and "id" in report_data and report_data["id"] not in seen_ids:
                seen_ids.add(report_data["id"])
                reports_list.append({
                    "id": report_data["id"],
                    "access_level": report_data.get("access_level", "standard"),
                    "created_at": report_data.get("created_at", ""),
                    "url": f"/report/{report_data['id']}",
                })
    return reports_list


from config import get_settings
from pipeline.face import analyze_face
from pipeline.coordinate import compute_coordinates, compute_gap, get_all_axis_labels
from pipeline.llm import interpret_interview, generate_report, parse_or_fallback, interpret_face_structure
from pipeline.action_spec import build_action_spec, build_overlay_plan
from pipeline.hair_spec import build_hair_spec
from pipeline.similarity import find_similar_types, select_teaser_type
from pipeline.face_comparison import compare_with_top_anchors
from pipeline.cluster import classify_user, discover_clusters, load_cluster_labels
from pipeline.report_formatter import format_report_for_frontend, _sanitize
from pipeline.hair_overlay import render_hair_simulation
from pipeline.overlay_renderer import render_overlay

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: DB 초기화 시도, 실패 시 기존 파일/인메모리 폴백
    db_ok = init_db()
    if db_ok:
        print("[STARTUP] PostgreSQL connected, DB is source of truth")
    else:
        print("[STARTUP] No DB, falling back to in-memory + JSON files")
    # 항상 인메모리 복원 (dual-write 호환 위해)
    _migrate_legacy_data()
    _restore_stores()
    yield
    # shutdown: 필요 시 정리 로직 추가


app = FastAPI(title="SIGAK PI API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores ──
USERS = {}
INTERVIEWS = {}
ANALYSES = {}
REPORTS = {}
ORDERS = {}  # order_id → order dict

# Zapier 웹훅 URL (env var)
ZAPIER_WEBHOOK_NEW_ORDER = os.getenv("ZAPIER_WEBHOOK_NEW_ORDER", "")
ZAPIER_WEBHOOK_REPORT_READY = os.getenv("ZAPIER_WEBHOOK_REPORT_READY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "sigak-admin-2026")

# 가격표 (세일가)
PRICE_MAP = {
    "standard": 2900,    # 오버뷰 (블러 해제는 추가 결제)
    "full": 29000,       # 풀 리포트 (처음부터 전부 열림)
}
# 정가 (삭선 표시용)
ORIGINAL_PRICE_MAP = {
    "standard": 5000,
    "full": 49000,
}
# 오버뷰 → 풀 업그레이드 가격
UPGRADE_PRICE = 26100

PAYMENT_INFO = {
    "bank": "카카오뱅크",
    "account": "3333-19-3591206",
    "holder": "최진규",
    "toss_deeplink": "supertoss://send?amount={amount}&bank=kakaobank&account=3333193591206",
    "kakao_deeplink": "kakaotalk://send?amount={amount}&bank=kakaobank&account=3333193591206",
}

# ── 클러스터 부트스트랩 ──
_cluster_data = load_cluster_labels()
if not _cluster_data.get("clusters"):
    discover_clusters(gender="female")
    discover_clusters(gender="male")


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class SubmitRequest(BaseModel):
    """질문지 + 메타데이터 (사진은 multipart로 별도)."""
    user_id: Optional[str] = None  # 카카오 로그인 유저의 기존 user_id
    name: str = ""
    phone: str = ""
    gender: str = "female"
    tier: str = "standard"  # 항상 standard(₩5,000)로 시작
    # Step 1: 얼굴 & 체형
    face_concerns: Optional[str] = None
    neck_length: Optional[str] = None
    shoulder_width: Optional[str] = None
    # Step 2: 현재 헤어
    hair_texture: Optional[str] = None
    hair_thickness: Optional[str] = None
    hair_volume: Optional[str] = None
    current_length: Optional[str] = None
    current_bangs: Optional[str] = None
    current_perm: Optional[str] = None
    root_volume_experience: Optional[str] = None
    # Step 3: 스타일 & 추구미
    self_perception: Optional[str] = None
    desired_image: Optional[str] = None
    reference_celebs: Optional[str] = None
    style_image_keywords: Optional[str] = None
    makeup_level: Optional[str] = None
    current_concerns: Optional[str] = None
    # Legacy
    style_keywords: Optional[str] = None
    # Wedding/Creator
    wedding_concept: Optional[str] = None
    dress_preference: Optional[str] = None
    content_style: Optional[str] = None
    target_audience: Optional[str] = None
    brand_tone: Optional[str] = None


class ConfirmRequest(BaseModel):
    admin_key: str


class FeedbackSubmit(BaseModel):
    satisfaction_score: int
    usefulness_score: int
    feedback_text: Optional[str] = None
    would_repurchase: bool = False
    would_recommend: bool = False


# ─────────────────────────────────────────────
#  Phase A: /submit — 사진+질문지 저장, AI 실행 안 함
# ─────────────────────────────────────────────

@app.post("/api/v1/submit")
async def submit(data: str = Form(""), files: list[UploadFile] = File(...)):
    """
    사진 + 질문지 제출 → order 생성. AI 비용 0.

    - data: JSON 문자열 (SubmitRequest)
    - files: 사진 파일 (multipart)
    """
    # JSON 파싱
    print(f"[SUBMIT] raw data field: {data[:200] if data else '(empty)'!r}")
    try:
        submit_data = SubmitRequest.model_validate_json(data) if data else SubmitRequest(name="익명", phone="")
    except Exception:
        raise HTTPException(400, "질문지를 좀 더 자세히 작성해주세요")

    # 기존 유저 재사용 (통합 조회: DB → 인메모리 → 디스크)
    existing_user = False
    if submit_data.user_id:
        found = _find_user(submit_data.user_id)
        if found:
            existing_user = True
            user_id = submit_data.user_id
            print(f"[SUBMIT] reusing user: {user_id} (kakao_id={found.get('kakao_id', '')})")
        else:
            user_id = str(uuid.uuid4())
            print(f"[SUBMIT] user_id={submit_data.user_id} not found, new: {user_id}")
    else:
        user_id = str(uuid.uuid4())

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    tier = submit_data.tier if submit_data.tier in PRICE_MAP else "full"
    amount = PRICE_MAP[tier]

    print(f"[SUBMIT] user_id={user_id} existing={existing_user} tier={tier!r} amount={amount}")

    # 1. 사진 저장
    save_dir = DATA_DIR / user_id
    save_dir.mkdir(exist_ok=True)

    photo_results = []
    for i, f in enumerate(files):
        contents = await f.read()
        ext = Path(f.filename or "photo.jpg").suffix or ".jpg"
        save_path = save_dir / f"photo_{i}{ext}"
        with open(save_path, "wb") as fp:
            fp.write(contents)

        # 얼굴 검출만 (빠름, LLM 비용 없음)
        face_result = analyze_face(contents)
        if face_result:
            photo_results.append({
                "filename": save_path.name,
                "features": face_result.to_dict(),
                "landmarks_106": face_result.landmarks_106,
                "bbox": face_result.bbox,
            })

    if not photo_results:
        raise HTTPException(400, "얼굴을 인식하지 못했어요. 정면을 바라보고 밝은 곳에서 다시 촬영해 주세요.")

    # 2. 분석 데이터 저장
    analysis = {
        "photos": photo_results,
        "primary_features": photo_results[0]["features"],
        "landmarks_106": photo_results[0].get("landmarks_106", []),
        "bbox": photo_results[0].get("bbox", []),
    }
    ANALYSES[user_id] = analysis
    _save_json(user_id, "face_analysis.json", analysis)

    # 3. 질문지 저장
    interview = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        **submit_data.model_dump(),
    }
    INTERVIEWS[user_id] = interview
    _save_json(user_id, "interview.json", interview)

    # 4. 유저 저장
    user = {
        "id": user_id,
        "name": submit_data.name or "익명",
        "phone": submit_data.phone or "",
        "gender": submit_data.gender,
        "tier": tier,
        "status": "pending_payment",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    USERS[user_id] = user
    _save_json(user_id, "user.json", user)

    # 5. Order 생성
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "tier": tier,
        "amount": amount,
        "status": "pending_payment",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "report_id": None,
    }
    ORDERS[order_id] = order
    _save_json(user_id, "order.json", order)

    # 5.5. DB 저장 (dual-write)
    if _use_db():
        db = get_db()
        try:
            if existing_user:
                # 기존 카카오 유저: tier/status만 업데이트 (kakao_id 보존)
                db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                if db_user:
                    db_user.tier = tier
                    db_user.status = "pending_payment"
                    db_user.gender = submit_data.gender
                    if submit_data.name and submit_data.name != "익명":
                        db_user.name = submit_data.name
                    if submit_data.phone:
                        db_user.phone = submit_data.phone
            else:
                # 신규 유저 생성
                db.merge(DBUser(
                    id=user_id,
                    name=submit_data.name or "익명",
                    phone=submit_data.phone or "",
                    gender=submit_data.gender,
                    tier=tier,
                    status="pending_payment",
                    extra_data={"created_at": user["created_at"]},
                    created_at=datetime.utcnow(),
                ))
            db.add(DBOrder(
                id=order_id,
                user_id=user_id,
                tier=tier,
                order_type="new",
                amount=amount,
                status="pending_payment",
                interview_data=json.loads(json.dumps(_sanitize(interview), default=str)),
                analysis_data=json.loads(json.dumps(_sanitize(analysis), default=str)),
                created_at=datetime.utcnow(),
            ))
            db.commit()
            print(f"[DB] submit: user={user_id} order={order_id} saved")
        except Exception as e:
            db.rollback()
            print(f"[DB] submit error: {e}")
        finally:
            db.close()

    # 6. Zapier 웹훅 → 관리자 알림
    print(f"[WEBHOOK] NEW_ORDER url={'SET' if ZAPIER_WEBHOOK_NEW_ORDER else 'EMPTY'}")
    if ZAPIER_WEBHOOK_NEW_ORDER:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(ZAPIER_WEBHOOK_NEW_ORDER, json={
                    "order_id": order_id,
                    "user_name": user["name"],
                    "phone": user["phone"],
                    "tier": tier,
                    "amount": amount,
                    "created_at": order["created_at"],
                    "confirm_url": f"{settings.base_url}/api/v1/confirm/{order_id}",
                }, timeout=10.0)
                print(f"[WEBHOOK] NEW_ORDER response: {resp.status_code}")
        except Exception as e:
            print(f"[WEBHOOK] NEW_ORDER error: {e}")

    # 7. 응답
    return {
        "order_id": order_id,
        "user_id": user_id,
        "status": "pending_payment",
        "payment_info": {
            "amount": amount,
            "bank": PAYMENT_INFO["bank"],
            "account": PAYMENT_INFO["account"],
            "holder": PAYMENT_INFO["holder"],
            "toss_deeplink": PAYMENT_INFO["toss_deeplink"].format(amount=amount),
            "kakao_deeplink": PAYMENT_INFO["kakao_deeplink"].format(amount=amount),
        },
    }


# ─────────────────────────────────────────────
#  Phase A: /confirm — 관리자 결제확인 → AI 실행
# ─────────────────────────────────────────────

@app.post("/api/v1/confirm/{order_id}")
async def confirm_order(order_id: str, data: ConfirmRequest):
    """관리자가 결제 확인 후 호출. AI 파이프라인 실행."""
    if data.admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")

    # DB 우선, 폴백으로 dict
    order = None
    db_order = None
    if _use_db():
        db = get_db()
        try:
            db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
            if db_order:
                order = {
                    "order_id": db_order.id,
                    "user_id": db_order.user_id,
                    "tier": db_order.tier,
                    "amount": db_order.amount,
                    "status": db_order.status,
                    "report_id": db_order.report_id,
                    "created_at": db_order.created_at.isoformat() + "Z" if db_order.created_at else "",
                }
        except Exception as e:
            print(f"[DB] confirm read error: {e}")
        finally:
            db.close()

    if not order:
        order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다")
    if order["status"] == "completed":
        return {"order_id": order_id, "status": "already_completed", "report_id": order.get("report_id")}
    if order["status"] not in ("pending_payment", "error"):
        raise HTTPException(400, f"확인할 수 없는 상태: {order['status']}")

    user_id = order["user_id"]
    order["status"] = "processing"

    # DB에서 interview/analysis 데이터 가져오기 (파이프라인에 전달)
    user_data = USERS.get(user_id, {})
    interview_data = INTERVIEWS.get(user_id, {})
    analysis_data = ANALYSES.get(user_id)

    if _use_db():
        db = get_db()
        try:
            db_ord = db.query(DBOrder).filter(DBOrder.id == order_id).first()
            if db_ord:
                db_ord.status = "processing"
                # DB에 저장된 interview/analysis 우선 사용
                if db_ord.interview_data:
                    interview_data = db_ord.interview_data
                if db_ord.analysis_data:
                    analysis_data = db_ord.analysis_data
                db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                if db_user:
                    user_data = {
                        "id": db_user.id,
                        "name": db_user.name,
                        "phone": db_user.phone,
                        "gender": db_user.gender or "female",
                        "tier": db_user.tier or "standard",
                        "status": db_user.status or "booked",
                        "created_at": db_user.created_at.isoformat() + "Z" if db_user.created_at else "",
                    }
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[DB] confirm processing update error: {e}")
        finally:
            db.close()

    # 인메모리에도 user/interview/analysis 최신 반영
    if user_data:
        USERS.setdefault(user_id, user_data)
    if interview_data:
        INTERVIEWS.setdefault(user_id, interview_data)
    if analysis_data:
        ANALYSES.setdefault(user_id, analysis_data)

    # AI 파이프라인 실행
    try:
        report_id, report_dict = _run_analysis_pipeline(
            user_id, order, user_data, interview_data, analysis_data
        )
    except Exception as e:
        print(f"[CONFIRM ERROR] {traceback.format_exc()}")
        order["status"] = "error"
        order["error"] = str(e)
        # DB 에러 상태 업데이트
        if _use_db():
            db = get_db()
            try:
                db_ord = db.query(DBOrder).filter(DBOrder.id == order_id).first()
                if db_ord:
                    db_ord.status = "error"
                    db_ord.error = str(e)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        raise HTTPException(500, f"분석 중 오류: {str(e)}")

    order["status"] = "completed"
    order["report_id"] = report_id
    order["completed_at"] = datetime.utcnow().isoformat() + "Z"
    _save_json(user_id, "order.json", order)

    # DB에 Report 저장 + Order 완료 업데이트
    if _use_db():
        db = get_db()
        try:
            # Report 저장
            db.add(DBReport(
                id=report_id,
                user_id=user_id,
                order_id=order_id,
                access_level=order.get("tier", "standard"),
                report_data=report_dict.get("formatted"),
                raw_data={
                    "current_coords": report_dict.get("current_coords"),
                    "aspiration_coords": report_dict.get("aspiration_coords"),
                    "gap": report_dict.get("gap"),
                    "content": report_dict.get("content"),
                },
                created_at=datetime.utcnow(),
            ))
            # Order 완료 상태
            db_ord = db.query(DBOrder).filter(DBOrder.id == order_id).first()
            if db_ord:
                db_ord.status = "completed"
                db_ord.report_id = report_id
                db_ord.completed_at = datetime.utcnow()
            # User 상태 업데이트
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if db_user:
                db_user.status = "reported"
            # 알림 생성
            db.add(DBNotification(
                user_id=user_id,
                type="report_ready",
                title="리포트가 완료되었습니다",
                message="AI 분석이 완료되었어요. 지금 확인해보세요!",
                link=f"/report/{report_id}",
            ))
            db.commit()
            print(f"[DB] confirm: report={report_id} order={order_id} completed")
        except Exception as e:
            db.rollback()
            print(f"[DB] confirm save error: {e}")
        finally:
            db.close()

    # Zapier 웹훅 → 유저에게 카톡 발송
    report_url = f"{settings.base_url}/report/{report_id}"
    if ZAPIER_WEBHOOK_REPORT_READY:
        try:
            user = USERS.get(user_id, {})
            async with httpx.AsyncClient() as client:
                await client.post(ZAPIER_WEBHOOK_REPORT_READY, json={
                    "order_id": order_id,
                    "user_phone": user.get("phone", ""),
                    "user_name": user.get("name", ""),
                    "report_url": report_url,
                    "tier": order["tier"],
                }, timeout=5.0)
        except Exception:
            pass

    return {
        "order_id": order_id,
        "status": "completed",
        "report_id": report_id,
        "report_url": report_url,
    }


def _run_analysis_pipeline(
    user_id: str,
    order: dict,
    user_data: dict = None,
    interview_data: dict = None,
    analysis_data: dict = None,
) -> tuple:
    """
    기존 analyze의 Step 1~9 전체. 결제 확인된 order만 실행.
    Returns (report_id, report_dict) tuple.
    """
    # 파라미터 우선, 폴백으로 인메모리 dict
    user = user_data or USERS.get(user_id, {})
    interview = interview_data or INTERVIEWS.get(user_id, {})
    analysis = analysis_data or ANALYSES.get(user_id)
    gender = user.get("gender", "female")

    # Step 1: 좌표 계산
    if analysis:
        features = analysis["primary_features"]
        current_coords = compute_coordinates(features)
    else:
        features = {}
        current_coords = {"shape": 0, "volume": 0, "age": 0}

    # Step 2: 얼굴 구조 해석 (LLM)
    face_interpretation = interpret_face_structure(features) if features else {}

    # Step 3: 유형 매칭
    similar_types = find_similar_types(user_embedding=None, user_coords=current_coords, gender=gender, top_k=3)

    # Step 4: 구조 비교
    type_comparisons = compare_with_top_anchors(user_features=features, similar_types=similar_types, gender=gender, max_compare=3)

    # Step 5: 클러스터
    cluster_result = classify_user(user_coords=current_coords, gender=gender)

    # Step 6: 인터뷰 → 추구미 좌표 (LLM)
    aspiration_result = interpret_interview(interview, gender=gender)
    aspiration_coords = aspiration_result.get("coordinates", {"shape": 0, "volume": 0, "age": 0})

    aspiration_similar = find_similar_types(user_embedding=None, user_coords=aspiration_coords, gender=gender, top_k=1)
    aspiration_anchor = aspiration_similar[0] if aspiration_similar else None

    # Step 7: 갭
    gap = compute_gap(current_coords, aspiration_coords)

    # Step 8: 액션 스펙
    top_type = similar_types[0] if similar_types else {"key": "type_2", "name_kr": "차갑지만 동안", "similarity": 0.5, "mode": "coord"}
    action_spec = build_action_spec(
        face_features=features, current_coords=current_coords, matched_type=top_type,
        type_delta=type_comparisons[0]["axis_impacts"] if type_comparisons else {},
        gap=gap, interview_intent=aspiration_result.get("intent_tags"), gender=gender,
    )

    # Step 8.5: 오버레이
    overlay_plan = build_overlay_plan(action_spec, features)
    import cv2
    overlay_image_url = None
    photo_dir = DATA_DIR / user_id
    photo_files = sorted(photo_dir.glob("*.jpg")) + sorted(photo_dir.glob("*.jpeg")) + sorted(photo_dir.glob("*.png"))
    if photo_files and analysis:
        photo_img = cv2.imdecode(np.fromfile(str(photo_files[0]), dtype=np.uint8), cv2.IMREAD_COLOR)
        if photo_img is not None:
            lmk106 = analysis.get("landmarks_106")
            face_bbox = analysis.get("bbox")
            if lmk106:
                overlay_plan_dicts = [{"zone": z.zone_name, "type": z.zone_type, "color": z.color_hex, "opacity": z.opacity} for z in overlay_plan]
                overlay_img = render_overlay(img=photo_img, landmarks_106=np.array(lmk106), overlay_plan=overlay_plan_dicts, face_type=features.get("face_shape", ""), bbox=np.array(face_bbox) if face_bbox else None)
                if overlay_img is not None:
                    cv2.imwrite(str(photo_dir / "overlay.png"), overlay_img)
                    overlay_image_url = f"/api/v1/uploads/{user_id}/overlay.png"

    # Step 9: LLM 리포트 (퍼스널컬러 정보 포함)
    personal_color_label = ""
    pc = features.get("personal_color")
    if pc:
        personal_color_label = pc.get("label_kr", "")
    raw_report = generate_report(action_spec, {
        "name": user["name"], "face_shape": features.get("face_shape", ""),
        "tier": user["tier"], "gender": gender,
        "aspiration_summary": aspiration_result.get("interpretation", ""),
        "primary_gap_direction_kr": gap.get("primary_shift_kr", ""),
        "personal_color": personal_color_label,
    })
    report_content = parse_or_fallback(raw_report, action_spec)

    # Step 9.3: 헤어 스펙
    hair_spec = build_hair_spec(face_features=features, interview=interview, gap=gap, gender=gender)
    report_content["hair_recommendation"] = hair_spec

    # Step 9.5: 일치 검증
    action_tips = report_content.get("action_tips", [])
    if len(action_tips) != len(action_spec.recommended_actions):
        report_content = parse_or_fallback("", action_spec)
        action_tips = report_content.get("action_tips", [])
    for tip, rec in zip(action_tips, action_spec.recommended_actions):
        if tip.get("zone") != rec.zone:
            tip["zone"] = rec.zone

    # Step 10: 포맷
    formatted_report = format_report_for_frontend(
        user_id=user_id, user_name=user["name"], tier=user["tier"], gender=gender,
        face_features=features, current_coords=current_coords,
        aspiration_coords=aspiration_coords, gap=gap, similar_types=similar_types,
        face_interpretation=face_interpretation, report_content=report_content,
        aspiration_interpretation=aspiration_result, aspiration_anchor=aspiration_anchor,
    )

    # 오버레이 URL 삽입
    if overlay_image_url:
        original_photos = [p for p in photo_files if p.name != "overlay.png"]
        formatted_report["overlay"] = {
            "before_url": f"/api/v1/uploads/{user_id}/{original_photos[0].name}" if original_photos else None,
            "after_url": overlay_image_url,
        }

    # Step 10.5: 헤어컬러 시뮬레이션 (퍼스널컬러 → 1순위 추천색 적용)
    hair_sim_url = None
    try:
        # skin_analysis 섹션에서 hair_colors 추출
        skin_section = next(
            (s for s in formatted_report.get("sections", []) if s.get("id") == "skin_analysis"),
            None,
        )
        hair_colors = (skin_section or {}).get("content", {}).get("hair_colors", [])
        if hair_colors and photo_files:
            target_hex = hair_colors[0].get("hex", "")
            if target_hex:
                photo_img_for_hair = cv2.imdecode(
                    np.fromfile(str(photo_files[0]), dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if photo_img_for_hair is not None:
                    sim_img = render_hair_simulation(photo_img_for_hair, target_hex)
                    if sim_img is not None:
                        sim_path = photo_dir / "hair_simulation.png"
                        cv2.imwrite(str(sim_path), sim_img)
                        hair_sim_url = f"/api/v1/uploads/{user_id}/hair_simulation.png"
                        print(f"[HAIR_SIM] 생성 완료: {hair_sim_url}")
    except Exception as e:
        print(f"[HAIR_SIM] 실패 (무시): {e}")

    if hair_sim_url:
        formatted_report["hair_simulation"] = {
            "before_url": f"/api/v1/uploads/{user_id}/{photo_files[0].name}" if photo_files else None,
            "after_url": hair_sim_url,
            "color_name": hair_colors[0].get("name", "") if hair_colors else "",
            "color_hex": hair_colors[0].get("hex", "") if hair_colors else "",
        }

    # 저장
    from dataclasses import asdict
    report_id = str(uuid.uuid4())
    report = {
        "id": report_id,
        "user_id": user_id,
        "order_id": order["order_id"],
        "formatted": formatted_report,
        "current_coords": current_coords,
        "aspiration_coords": aspiration_coords,
        "gap": gap,
        "content": report_content,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "access_level": order.get("tier", "standard"),  # standard(₩5K) 또는 full
    }
    sanitized_report = _sanitize(report)
    REPORTS[report_id] = sanitized_report
    # user_id로도 접근 가능하게 (하위호환)
    REPORTS[user_id] = REPORTS[report_id]
    _save_json(user_id, "report.json", REPORTS[report_id])
    if user_id in USERS:
        USERS[user_id]["status"] = "reported"

    return report_id, sanitized_report


# ─────────────────────────────────────────────
#  Report 조회
# ─────────────────────────────────────────────

@app.get("/api/v1/report/{report_id}")
async def get_report(report_id: str):
    """리포트 조회. report_id 또는 user_id로 접근 가능."""
    report = REPORTS.get(report_id)

    # DB에서 조회 (report_id → user_id 순서)
    if not report and _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.id == report_id).first()
            if not db_report:
                # user_id로도 시도
                db_report = db.query(DBReport).filter(DBReport.user_id == report_id).first()
            if db_report:
                report = {
                    "id": db_report.id,
                    "user_id": db_report.user_id,
                    "order_id": db_report.order_id,
                    "formatted": db_report.report_data,
                    "access_level": db_report.access_level,
                    "pending_level": db_report.pending_level,
                    "created_at": db_report.created_at.isoformat() + "Z" if db_report.created_at else "",
                    "feedback": db_report.feedback,
                }
                if db_report.raw_data:
                    report.update(db_report.raw_data)
        except Exception as e:
            print(f"[DB] report read error: {e}")
        finally:
            db.close()

    if not report:
        # order_id로 찾기 (인메모리 폴백)
        for o in ORDERS.values():
            if o.get("report_id") == report_id:
                report = REPORTS.get(o["user_id"])
                break

    # 디스크 fallback: report_id가 user_id인 경우
    if not report:
        disk_report = _load_json(report_id, "report.json")
        if disk_report and "id" in disk_report:
            REPORTS[disk_report["id"]] = disk_report
            REPORTS[report_id] = disk_report
            report = disk_report

    if not report:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")

    if "formatted" in report:
        response = {**report["formatted"]}
        access = report.get("access_level", "standard")
        response["access_level"] = access
        response["pending_level"] = report.get("pending_level")
        response["user_id"] = report.get("user_id", "")

        # access_level에 따라 섹션 잠금
        level_order = {"free": 0, "standard": 1, "full": 2}
        current = level_order.get(access, 0)
        for section in response.get("sections", []):
            unlock = section.get("unlock_level")
            if unlock:
                section["locked"] = current < level_order.get(unlock, 0)
            else:
                section["locked"] = False

        # 풀 업그레이드 페이월 정보
        if access != "full":
            response["paywall"] = {
                "full": {
                    "price": 26100,
                    "original_price": 44000,
                    "label": "풀 리포트 언락",
                    "total_note": "기존 ₩2,900 + 추가 ₩26,100 = 총 ₩29,000",
                    "method": "manual",
                },
            }
            response["payment_account"] = PAYMENT_INFO

        return response

    return report


# ─────────────────────────────────────────────
#  Order 상태 조회 (프론트엔드 폴링용)
# ─────────────────────────────────────────────

@app.get("/api/v1/order/{order_id}")
async def get_order_status(order_id: str):
    """주문 상태 조회."""
    order = ORDERS.get(order_id)

    # DB 폴백
    if not order and _use_db():
        db = get_db()
        try:
            db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
            if db_order:
                order = {
                    "order_id": db_order.id,
                    "user_id": db_order.user_id,
                    "tier": db_order.tier,
                    "amount": db_order.amount,
                    "status": db_order.status,
                    "report_id": db_order.report_id,
                }
        except Exception as e:
            print(f"[DB] order read error: {e}")
        finally:
            db.close()

    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다")

    result = {
        "order_id": order_id,
        "status": order["status"],
        "tier": order["tier"],
        "amount": order["amount"],
    }
    if order["status"] == "completed" and order.get("report_id"):
        result["report_id"] = order["report_id"]
        result["report_url"] = f"/report/{order['report_id']}"

    return result


# ─────────────────────────────────────────────
#  풀 업그레이드 요청 (유저가 송금 완료 버튼 누름)
# ─────────────────────────────────────────────

ZAPIER_WEBHOOK_UPGRADE = os.getenv("ZAPIER_WEBHOOK_UPGRADE", ZAPIER_WEBHOOK_NEW_ORDER)


@app.post("/api/v1/upgrade-request/{report_id}")
async def request_upgrade(report_id: str):
    """유저가 ₩26,100 풀 업그레이드 요청. 주문 생성 + 웹훅 → 결제 페이지로 이동."""
    report = REPORTS.get(report_id)
    if not report:
        for rid, r in REPORTS.items():
            if r.get("user_id") == report_id:
                report = r
                report_id = rid
                break

    # DB 폴백
    if not report and _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.id == report_id).first()
            if not db_report:
                db_report = db.query(DBReport).filter(DBReport.user_id == report_id).first()
            if db_report:
                report = {
                    "id": db_report.id,
                    "user_id": db_report.user_id,
                    "order_id": db_report.order_id,
                    "access_level": db_report.access_level,
                }
                report_id = db_report.id
        except Exception as e:
            print(f"[DB] upgrade-request read error: {e}")
        finally:
            db.close()

    if not report:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")

    if report.get("access_level") == "full":
        return {"status": "already_full", "report_id": report["id"]}

    user_id = report.get("user_id", "")
    user = _find_user(user_id) or {}

    # 업그레이드 주문 생성 (신규 주문과 동일 구조)
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "tier": "full",
        "type": "upgrade",
        "amount": UPGRADE_PRICE,
        "status": "pending_payment",
        "report_id": report["id"],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    ORDERS[order_id] = order
    _save_json(user_id, "order.json", order)

    # DB에 업그레이드 주문 저장
    if _use_db():
        db = get_db()
        try:
            db.add(DBOrder(
                id=order_id,
                user_id=user_id,
                tier="full",
                order_type="upgrade",
                amount=UPGRADE_PRICE,
                status="pending_payment",
                report_id=report["id"],
                created_at=datetime.utcnow(),
            ))
            # Report에 pending_level 설정
            db_report = db.query(DBReport).filter(DBReport.id == report["id"]).first()
            if db_report:
                db_report.pending_level = "full"
            db.commit()
            print(f"[DB] upgrade-request: order={order_id} saved")
        except Exception as e:
            db.rollback()
            print(f"[DB] upgrade-request save error: {e}")
        finally:
            db.close()

    # Zapier 웹훅 → 관리자 알림 (신규 주문과 동일 웹훅)
    if ZAPIER_WEBHOOK_NEW_ORDER:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(ZAPIER_WEBHOOK_NEW_ORDER, json={
                    "order_id": order_id,
                    "type": "upgrade",
                    "user_name": user.get("name", ""),
                    "phone": user.get("phone", ""),
                    "tier": "full",
                    "amount": UPGRADE_PRICE,
                    "created_at": order["created_at"],
                    "confirm_url": f"{settings.base_url}/api/v1/upgrade/{report['id']}",
                }, timeout=10.0)
                print(f"[WEBHOOK] UPGRADE order={order_id} response={resp.status_code}")
        except Exception as e:
            print(f"[WEBHOOK] UPGRADE error: {e}")

    return {
        "status": "pending_payment",
        "order_id": order_id,
        "report_id": report["id"],
        "payment_info": {
            "amount": UPGRADE_PRICE,
            "bank": PAYMENT_INFO["bank"],
            "account": PAYMENT_INFO["account"],
            "holder": PAYMENT_INFO["holder"],
            "toss_deeplink": PAYMENT_INFO["toss_deeplink"].format(amount=UPGRADE_PRICE),
            "kakao_deeplink": PAYMENT_INFO["kakao_deeplink"].format(amount=UPGRADE_PRICE),
        },
    }


# ─────────────────────────────────────────────
#  풀 업그레이드 확인 (관리자 전용)
# ─────────────────────────────────────────────

@app.post("/api/v1/upgrade/{report_id}")
async def upgrade_report(report_id: str, data: ConfirmRequest):
    """관리자가 추가 입금(₩44,000) 확인 후 호출. 블러 해제."""
    if data.admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")

    report = REPORTS.get(report_id)
    if not report:
        # user_id로도 시도
        for rid, r in REPORTS.items():
            if r.get("user_id") == report_id:
                report = r
                report_id = rid
                break

    # DB 폴백
    if not report and _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.id == report_id).first()
            if not db_report:
                db_report = db.query(DBReport).filter(DBReport.user_id == report_id).first()
            if db_report:
                report = {
                    "id": db_report.id,
                    "user_id": db_report.user_id,
                    "order_id": db_report.order_id,
                    "access_level": db_report.access_level,
                    "formatted": db_report.report_data,
                }
                report_id = db_report.id
        except Exception as e:
            print(f"[DB] upgrade read error: {e}")
        finally:
            db.close()

    if not report:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")

    if report.get("access_level") == "full":
        return {"status": "already_full", "report_id": report["id"]}

    report["access_level"] = "full"
    report["upgraded_at"] = datetime.utcnow().isoformat() + "Z"

    user_id = report.get("user_id", "")
    if user_id:
        _save_json(user_id, "report.json", report)

    # DB 업데이트
    if _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.id == report["id"]).first()
            if db_report:
                db_report.access_level = "full"
                db_report.pending_level = None
                db_report.upgraded_at = datetime.utcnow()
            # 해당 upgrade 주문도 완료 처리
            upgrade_orders = db.query(DBOrder).filter(
                DBOrder.report_id == report["id"],
                DBOrder.order_type == "upgrade",
                DBOrder.status == "pending_payment",
            ).all()
            for uo in upgrade_orders:
                uo.status = "completed"
                uo.confirmed_at = datetime.utcnow()
                uo.completed_at = datetime.utcnow()
            # 알림 생성
            db.add(DBNotification(
                user_id=user_id,
                type="upgrade_complete",
                title="풀 리포트가 열렸습니다",
                message="헤어 추천, 액션 플랜까지 모두 확인해보세요!",
                link=f"/report/{report['id']}",
            ))
            db.commit()
            print(f"[DB] upgrade: report={report['id']} upgraded to full")
        except Exception as e:
            db.rollback()
            print(f"[DB] upgrade save error: {e}")
        finally:
            db.close()

    # 인메모리도 업데이트
    if report["id"] in REPORTS:
        REPORTS[report["id"]]["access_level"] = "full"
    if user_id in REPORTS:
        REPORTS[user_id]["access_level"] = "full"

    # Zapier 웹훅 → 유저에게 풀 리포트 알림
    if ZAPIER_WEBHOOK_REPORT_READY:
        try:
            user = USERS.get(user_id, {})
            if not user and _use_db():
                db = get_db()
                try:
                    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                    if db_user:
                        user = {"name": db_user.name, "phone": db_user.phone}
                except Exception:
                    pass
                finally:
                    db.close()
            async with httpx.AsyncClient() as client:
                await client.post(ZAPIER_WEBHOOK_REPORT_READY, json={
                    "order_id": report.get("order_id", ""),
                    "user_phone": user.get("phone", ""),
                    "user_name": user.get("name", ""),
                    "report_url": f"{settings.base_url}/report/{report['id']}",
                    "tier": "full",
                    "message": "풀 리포트가 언락되었습니다!",
                }, timeout=5.0)
        except Exception:
            pass

    return {"status": "upgraded", "report_id": report["id"], "access_level": "full"}


# ─────────────────────────────────────────────
#  하위호환: 기존 엔드포인트 유지
# ─────────────────────────────────────────────

class BookingCreate(BaseModel):
    name: str
    phone: str
    gender: str = "female"
    tier: str = "basic"
    booking_date: str = ""
    booking_time: str = "00:00"
    instagram: Optional[str] = None
    partner_name: Optional[str] = None
    partner_phone: Optional[str] = None
    channel_url: Optional[str] = None

class InterviewSubmit(BaseModel):
    interviewer_name: Optional[str] = None
    face_concerns: Optional[str] = None
    neck_length: Optional[str] = None
    shoulder_width: Optional[str] = None
    hair_texture: Optional[str] = None
    hair_thickness: Optional[str] = None
    hair_volume: Optional[str] = None
    current_length: Optional[str] = None
    current_bangs: Optional[str] = None
    current_perm: Optional[str] = None
    root_volume_experience: Optional[str] = None
    self_perception: Optional[str] = None
    desired_image: Optional[str] = None
    reference_celebs: Optional[str] = None
    style_image_keywords: Optional[str] = None
    makeup_level: Optional[str] = None
    current_concerns: Optional[str] = None
    style_keywords: Optional[str] = None
    daily_routine: Optional[str] = None
    raw_notes: Optional[str] = None
    wedding_concept: Optional[str] = None
    dress_preference: Optional[str] = None
    content_style: Optional[str] = None
    target_audience: Optional[str] = None
    brand_tone: Optional[str] = None


@app.post("/api/v1/booking")
async def create_booking(data: BookingCreate):
    user_id = str(uuid.uuid4())
    user = {"id": user_id, "status": "booked", "created_at": datetime.utcnow().isoformat() + "Z", "price": PRICE_MAP.get(data.tier, 2900), **data.model_dump()}
    USERS[user_id] = user
    _save_json(user_id, "user.json", user)  # booking.json → user.json 통일

    # DB dual-write
    if _use_db():
        db = get_db()
        try:
            db.merge(DBUser(
                id=user_id,
                name=data.name,
                phone=data.phone,
                gender=data.gender,
                tier=data.tier,
                status="booked",
                extra_data=user,
                created_at=datetime.utcnow(),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[DB] booking error: {e}")
        finally:
            db.close()

    return {"user_id": user_id, "status": "booked", "price": user["price"]}


@app.post("/api/v1/interview/{user_id}")
async def submit_interview_legacy(user_id: str, data: InterviewSubmit):
    if not _find_user(user_id):
        raise HTTPException(404, "User not found")
    interview = {"id": str(uuid.uuid4()), "user_id": user_id, "created_at": datetime.utcnow().isoformat() + "Z", **data.model_dump()}
    INTERVIEWS[user_id] = interview
    _save_json(user_id, "interview.json", interview)
    if user_id in USERS:
        USERS[user_id]["status"] = "interviewed"

    # DB: 유저 상태 업데이트 (interview 데이터는 Order의 JSON에 저장)
    if _use_db():
        db = get_db()
        try:
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if db_user:
                db_user.status = "interviewed"
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[DB] interview error: {e}")
        finally:
            db.close()

    return {"status": "interviewed", "interview_id": interview["id"]}


@app.post("/api/v1/photos/{user_id}")
async def upload_photos(user_id: str, files: list[UploadFile] = File(...)):
    if not _find_user(user_id):
        raise HTTPException(404, "User not found")
    save_dir = DATA_DIR / user_id
    save_dir.mkdir(exist_ok=True)
    photo_results = []
    for i, f in enumerate(files):
        contents = await f.read()
        ext = Path(f.filename or "photo.jpg").suffix or ".jpg"
        save_path = save_dir / f"photo_{i}{ext}"
        with open(save_path, "wb") as fp:
            fp.write(contents)
        face_result = analyze_face(contents)
        if face_result:
            photo_results.append({"filename": save_path.name, "features": face_result.to_dict(), "landmarks_106": face_result.landmarks_106, "bbox": face_result.bbox})
    if not photo_results:
        raise HTTPException(400, "얼굴을 인식하지 못했어요.")
    ANALYSES[user_id] = {"photos": photo_results, "primary_features": photo_results[0]["features"], "landmarks_106": photo_results[0].get("landmarks_106", []), "bbox": photo_results[0].get("bbox", [])}
    _save_json(user_id, "face_analysis.json", ANALYSES[user_id])
    return {"status": "photos_processed", "faces_detected": len(photo_results), "primary_face_shape": photo_results[0]["features"]["face_shape"]}


@app.post("/api/v1/analyze/{user_id}")
async def run_analysis_legacy(user_id: str):
    """하위호환: 기존 프론트엔드에서 호출 가능."""
    user_data = _find_user(user_id)
    if not user_data:
        raise HTTPException(404, "User not found")

    interview_exists = user_id in INTERVIEWS
    interview_data = INTERVIEWS.get(user_id, {})
    analysis_data = ANALYSES.get(user_id)
    if not interview_exists:
        raise HTTPException(400, "Interview data not submitted yet")

    order = {"order_id": f"ord_{uuid.uuid4().hex[:12]}", "user_id": user_id, "tier": user_data.get("tier", "full"), "amount": 0, "status": "pending_payment"}
    report_id, _ = _run_analysis_pipeline(user_id, order, user_data, interview_data, analysis_data)
    return {"status": "reported", "report_id": report_id}


# ─────────────────────────────────────────────
#  Feedback
# ─────────────────────────────────────────────

@app.post("/api/v1/feedback/{user_id}")
async def submit_feedback(user_id: str, data: FeedbackSubmit):
    report = REPORTS.get(user_id)

    # DB 폴백
    if not report and _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.user_id == user_id).first()
            if db_report:
                report = {"id": db_report.id, "user_id": db_report.user_id}
        except Exception:
            pass
        finally:
            db.close()

    if not report:
        raise HTTPException(404, "Report not found")

    feedback_data = data.model_dump()

    # 인메모리 업데이트
    if user_id in REPORTS:
        REPORTS[user_id]["feedback"] = feedback_data
    if user_id in USERS:
        USERS[user_id]["status"] = "feedback_done"

    # DB 업데이트
    if _use_db():
        db = get_db()
        try:
            db_report = db.query(DBReport).filter(DBReport.user_id == user_id).first()
            if db_report:
                db_report.feedback = feedback_data
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if db_user:
                db_user.status = "feedback_done"
            db.commit()
            print(f"[DB] feedback: user={user_id} saved")
        except Exception as e:
            db.rollback()
            print(f"[DB] feedback save error: {e}")
        finally:
            db.close()

    return {"status": "feedback_recorded"}


# ─────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────

@app.get("/api/v1/dashboard/queue")
async def get_queue():
    # DB 우선
    if _use_db():
        db = get_db()
        try:
            db_users = db.query(DBUser).all()
            if db_users:
                queue = [
                    {
                        "id": u.id,
                        "name": u.name or "",
                        "gender": u.gender or "female",
                        "tier": u.tier or "",
                        "status": u.status or "",
                    }
                    for u in db_users
                ]
                return sorted(queue, key=lambda x: x.get("name", ""))
        except Exception as e:
            print(f"[DB] dashboard/queue error: {e}")
        finally:
            db.close()

    # 인메모리 폴백
    queue = []
    for uid, u in USERS.items():
        queue.append({
            "id": uid, "name": u.get("name", ""), "gender": u.get("gender", "female"),
            "tier": u.get("tier", ""), "status": u.get("status", ""),
        })
    return sorted(queue, key=lambda x: x.get("name", ""))


@app.get("/api/v1/dashboard/orders")
async def get_orders():
    """관리자용: 전체 주문 목록."""
    # DB 우선
    if _use_db():
        db = get_db()
        try:
            db_orders = db.query(DBOrder).all()
            if db_orders is not None:
                result = []
                for o in db_orders:
                    db_user = db.query(DBUser).filter(DBUser.id == o.user_id).first()
                    result.append({
                        "order_id": o.id,
                        "user_name": db_user.name if db_user else "",
                        "phone": db_user.phone if db_user else "",
                        "tier": o.tier,
                        "amount": o.amount,
                        "status": o.status,
                        "created_at": o.created_at.isoformat() + "Z" if o.created_at else "",
                        "report_id": o.report_id,
                    })
                return sorted(result, key=lambda x: x["created_at"], reverse=True)
        except Exception as e:
            print(f"[DB] dashboard/orders error: {e}")
        finally:
            db.close()

    # 인메모리 폴백
    result = []
    for oid, o in ORDERS.items():
        user = USERS.get(o["user_id"], {})
        result.append({
            "order_id": oid,
            "user_name": user.get("name", ""),
            "phone": user.get("phone", ""),
            "tier": o["tier"],
            "amount": o["amount"],
            "status": o["status"],
            "created_at": o["created_at"],
            "report_id": o.get("report_id"),
        })
    return sorted(result, key=lambda x: x["created_at"], reverse=True)


# ─────────────────────────────────────────────
#  Static files & Health
# ─────────────────────────────────────────────

@app.get("/api/v1/axes")
async def get_axes():
    all_labels = get_all_axis_labels()
    return [{"name": n, "name_kr": l["name_kr"], "negative": {"label": l["low_en"], "label_kr": l["low"]}, "positive": {"label": l["high_en"], "label_kr": l["high"]}} for n, l in all_labels.items()]


@app.get("/api/v1/uploads/{user_id}/{filename}")
async def serve_upload(user_id: str, filename: str):
    file_path = DATA_DIR / user_id / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    return FileResponse(str(file_path), media_type=media_types.get(file_path.suffix.lower(), "application/octet-stream"))


# ─────────────────────────────────────────────
#  Kakao OAuth 인증
# ─────────────────────────────────────────────

@app.get("/api/v1/auth/kakao/login")
async def kakao_login(redirect_uri: str = "https://www.sigak.asia/auth/kakao/callback"):
    """카카오 OAuth 인가 URL 반환."""
    kakao_key = os.getenv("KAKAO_REST_API_KEY", "")
    if not kakao_key:
        raise HTTPException(500, "카카오 로그인이 설정되지 않았습니다")
    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={kakao_key}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=profile_nickname,account_email"
    )
    return {"auth_url": auth_url}


class KakaoTokenRequest(BaseModel):
    code: str
    redirect_uri: str = "https://www.sigak.asia/auth/kakao/callback"


@app.post("/api/v1/auth/kakao/token")
async def kakao_token(data: KakaoTokenRequest):
    """카카오 인가 코드 → 액세스 토큰 교환 → 유저 조회/생성."""
    code = data.code
    redirect_uri = data.redirect_uri
    kakao_key = os.getenv("KAKAO_REST_API_KEY", "")
    kakao_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
    print(f"[KAKAO] key={kakao_key[:6]}... secret={'SET' if kakao_secret else 'EMPTY'} redirect={redirect_uri}")

    # 1. 인가 코드로 액세스 토큰 교환
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": kakao_key,
                "client_secret": kakao_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_resp.status_code != 200:
        print(f"[KAKAO] token error: {token_resp.status_code} {token_resp.text}")
        raise HTTPException(400, f"카카오 인증 실패: {token_resp.json().get('error_description', token_resp.text[:100])}")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    # 2. 카카오 사용자 정보 조회
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if user_resp.status_code != 200:
        raise HTTPException(400, "카카오 사용자 정보를 가져올 수 없습니다")

    kakao_user = user_resp.json()
    kakao_id = str(kakao_user.get("id"))
    properties = kakao_user.get("properties", {})
    kakao_account = kakao_user.get("kakao_account", {})

    nickname = properties.get("nickname", "")
    profile_image = properties.get("profile_image", "") or kakao_account.get("profile", {}).get("profile_image_url", "")
    email = kakao_account.get("email", "")
    print(f"[KAKAO] id={kakao_id} nickname={nickname} email={email} profile_image={'SET' if profile_image else 'EMPTY'}")

    # 3. 유저 조회 또는 생성 (병합 로직: kakao_id → email → 신규)
    user_id = None
    merged_name = ""  # 병합 시 기존 유저의 본명 보존용

    if _use_db():
        db = get_db()
        try:
            # 1차: kakao_id로 기존 유저 조회
            existing = db.query(DBUser).filter(DBUser.kakao_id == kakao_id).first()
            if existing:
                user_id = existing.id
                merged_name = existing.name
                # 카카오 프로필 업데이트
                existing.kakao_nickname = nickname
                if profile_image:
                    existing.kakao_profile_image = profile_image
                if email and not existing.email:
                    existing.email = email
                db.commit()
                print(f"[AUTH] found by kakao_id: {user_id}")
            else:
                # 2차: email로 기존 유저 병합
                merge_candidate = None
                if email:
                    merge_candidate = db.query(DBUser).filter(
                        DBUser.email == email,
                        DBUser.kakao_id.is_(None) | (DBUser.kakao_id == ""),
                    ).first()
                # 3차: kakao_id 없는 유저 중 1명만 있으면 병합 (MVP 초기)
                if not merge_candidate:
                    orphans = db.query(DBUser).filter(
                        DBUser.kakao_id.is_(None) | (DBUser.kakao_id == ""),
                    ).all()
                    if len(orphans) == 1:
                        merge_candidate = orphans[0]
                        print(f"[AUTH] single orphan user found: {merge_candidate.id}")

                if merge_candidate:
                    merge_candidate.kakao_id = kakao_id
                    merge_candidate.kakao_nickname = nickname
                    merge_candidate.kakao_profile_image = profile_image
                    if email:
                        merge_candidate.email = email
                    user_id = merge_candidate.id
                    merged_name = merge_candidate.name
                    db.commit()
                    print(f"[AUTH] merged kakao into user: {user_id} (name={merged_name})")
                else:
                    # 신규 유저 생성
                    user_id = str(uuid.uuid4())
                    db.add(DBUser(
                        id=user_id,
                        kakao_id=kakao_id,
                        email=email,
                        kakao_nickname=nickname,
                        kakao_profile_image=profile_image,
                        name=nickname or "익명",
                        phone="",
                        gender="female",
                        status="authenticated",
                        created_at=datetime.utcnow(),
                    ))
                    db.commit()
                    print(f"[AUTH] new kakao user: {user_id}")
        except Exception as e:
            db.rollback()
            print(f"[AUTH] DB error: {e}")
        finally:
            db.close()

    # 폴백: 인메모리
    if not user_id:
        for uid, u in USERS.items():
            if u.get("kakao_id") == kakao_id:
                user_id = uid
                break
        if not user_id:
            user_id = str(uuid.uuid4())

    if user_id not in USERS:
        USERS[user_id] = {
            "id": user_id,
            "kakao_id": kakao_id,
            "email": email,
            "name": merged_name or nickname or "익명",
            "phone": "",
            "gender": "female",
            "status": "authenticated",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    # 디스크 저장 (서버 재시작 시 복원용)
    _save_json(user_id, "user.json", USERS[user_id])

    # 4. 유저의 리포트 조회 (통합 헬퍼 사용)
    reports = _find_reports_for_user(user_id)

    # 응답: 본명이 있으면 본명, 없으면 카카오 닉네임
    display_name = merged_name if (merged_name and merged_name != "익명") else nickname

    return {
        "user_id": user_id,
        "kakao_id": kakao_id,
        "name": display_name,
        "nickname": nickname,
        "email": email,
        "profile_image": profile_image,
        "reports": reports,
    }


@app.get("/api/v1/auth/me")
async def get_me(user_id: str = ""):
    """로그인 상태 확인 (user_id 기반)."""
    if not user_id:
        raise HTTPException(401, "로그인이 필요합니다")

    # 통합 조회: DB → 인메모리 → 디스크
    user = _find_user(user_id)
    if not user:
        raise HTTPException(401, "사용자를 찾을 수 없습니다")

    # 리포트 조회 (통합 헬퍼)
    reports = _find_reports_for_user(user_id)

    return {
        "user_id": user.get("id") or user_id,
        "name": user.get("name", ""),
        "phone": user.get("phone", ""),
        "kakao_id": user.get("kakao_id", ""),
        "reports": reports,
    }


# ─────────────────────────────────────────────
#  캐스팅 풀 (Casting Pool)
# ─────────────────────────────────────────────

@app.post("/api/v1/casting/opt-in")
async def casting_opt_in(user_id: str):
    """풀 리포트 하단 배너에서 동의 클릭 시 호출."""
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")
    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            raise HTTPException(404, "유저를 찾을 수 없습니다")
        if user.casting_opted_in:
            return {"status": "already_opted_in"}
        user.casting_opted_in = True
        user.casting_opted_at = datetime.utcnow()
        db.commit()
        return {"status": "opted_in", "user_id": user.id}
    finally:
        db.close()


@app.post("/api/v1/casting/opt-out")
async def casting_opt_out(user_id: str):
    """마이페이지에서 등록 해제 시 호출. 약관 제4조 5항: 언제든 해제 가능."""
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")
    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            raise HTTPException(404, "유저를 찾을 수 없습니다")
        user.casting_opted_in = False
        user.casting_opted_out_at = datetime.utcnow()
        db.commit()
        return {"status": "opted_out"}
    finally:
        db.close()


@app.get("/api/v1/casting/status")
async def casting_status(user_id: str):
    """현재 opt-in 상태 조회."""
    if not _use_db():
        return {"opted_in": False, "opted_at": None}
    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            raise HTTPException(404, "유저를 찾을 수 없습니다")
        return {
            "opted_in": bool(user.casting_opted_in),
            "opted_at": user.casting_opted_at.isoformat() + "Z" if user.casting_opted_at else None,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
#  캐스팅 풀 Admin API (B2B Dashboard)
# ─────────────────────────────────────────────

def _find_section(report_data: dict, section_id: str) -> dict:
    """report_data sections에서 id로 content를 찾는 헬퍼."""
    for s in (report_data or {}).get("sections", []):
        if s.get("id") == section_id:
            return s.get("content", {})
    return {}


@app.get("/api/v1/admin/casting-pool")
async def get_casting_pool(admin_key: str, face_shape: str = None, image_type: str = None):
    """opt-in 유저 목록 + 얼굴 분석 데이터 (B2B 대시보드용)."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")
    if not _use_db():
        return {"total": 0, "users": []}

    db = get_db()
    try:
        users = db.query(DBUser).filter(DBUser.casting_opted_in == True)\
            .order_by(DBUser.casting_opted_at.desc()).all()

        result = []
        for user in users:
            report = db.query(DBReport)\
                .filter(DBReport.user_id == user.id)\
                .order_by(DBReport.created_at.desc()).first()

            if not report or not report.report_data:
                continue

            data = report.report_data

            # 섹션별 데이터 추출
            face_structure = _find_section(data, "face_structure")
            gap_analysis = _find_section(data, "gap_analysis")
            skin_analysis = _find_section(data, "skin_analysis")

            user_face_shape = face_structure.get("face_type", "")
            user_image_type = gap_analysis.get("current_type", "")
            skin_tone = skin_analysis.get("tone", "")

            # 필터
            if face_shape and face_shape not in user_face_shape:
                continue
            if image_type and image_type not in user_image_type:
                continue

            # 좌표: raw_data 우선, fallback → gap_analysis
            coordinates = {}
            if report.raw_data and isinstance(report.raw_data, dict):
                coordinates = report.raw_data.get("current_coords", {})
            if not coordinates:
                coordinates = gap_analysis.get("current_coordinates", {})

            # 이름 마스킹: 홍길동 → 홍*동
            name = user.name or ""
            if len(name) >= 3:
                masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
            elif len(name) == 2:
                masked_name = name[0] + "*"
            else:
                masked_name = name

            # 사진 URL 생성
            photo_url = None
            overlay = data.get("overlay")
            if overlay and overlay.get("before_url"):
                photo_url = overlay["before_url"]
            else:
                # 디스크에서 사진 찾기
                photo_dir = DATA_DIR / user.id
                if photo_dir.exists():
                    photos = sorted(photo_dir.glob("photo_*.*"))
                    if photos:
                        photo_url = f"/api/v1/uploads/{user.id}/{photos[0].name}"

            result.append({
                "user_id": user.id,
                "name": masked_name,
                "gender": user.gender or "",
                "face_shape": user_face_shape,
                "image_type": user_image_type,
                "coordinates": coordinates,
                "skin_tone": skin_tone,
                "opted_at": user.casting_opted_at.isoformat() + "Z" if user.casting_opted_at else "",
                "report_id": report.id,
                "has_photo": bool(photo_url),
                "photo_url": photo_url,
            })

        return {"total": len(result), "users": result}
    finally:
        db.close()


@app.get("/api/v1/admin/casting-pool/{user_id}")
async def get_casting_profile(user_id: str, admin_key: str):
    """opt-in 유저 상세 프로필 (B2B 대시보드용)."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")

    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user or not user.casting_opted_in:
            raise HTTPException(404, "유저를 찾을 수 없거나 opt-in 상태가 아닙니다")

        report = db.query(DBReport)\
            .filter(DBReport.user_id == user_id)\
            .order_by(DBReport.created_at.desc()).first()
        if not report:
            raise HTTPException(404, "리포트가 없습니다")

        data = report.report_data or {}

        face_structure = _find_section(data, "face_structure")
        gap_analysis = _find_section(data, "gap_analysis")
        skin_analysis = _find_section(data, "skin_analysis")

        # 이름 마스킹
        name = user.name or ""
        if len(name) >= 3:
            masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
        elif len(name) == 2:
            masked_name = name[0] + "*"
        else:
            masked_name = name

        # 좌표
        coordinates = {}
        if report.raw_data and isinstance(report.raw_data, dict):
            coordinates = report.raw_data.get("current_coords", {})
        if not coordinates:
            coordinates = gap_analysis.get("current_coordinates", {})

        # 사진 URL
        photo_url = None
        overlay_url = None
        overlay = data.get("overlay")
        if overlay:
            photo_url = overlay.get("before_url")
            overlay_url = overlay.get("after_url")
        if not photo_url:
            photo_dir = DATA_DIR / user.id
            if photo_dir.exists():
                photos = sorted(photo_dir.glob("photo_*.*"))
                if photos:
                    photo_url = f"/api/v1/uploads/{user.id}/{photos[0].name}"

        return {
            "user_id": user.id,
            "name": masked_name,
            "gender": user.gender or "",
            "face_shape": face_structure.get("face_type", ""),
            "image_type": gap_analysis.get("current_type", ""),
            "coordinates": coordinates,
            "skin_tone": skin_analysis.get("tone", ""),
            "sections": data.get("sections", []),
            "opted_at": user.casting_opted_at.isoformat() + "Z" if user.casting_opted_at else "",
            "report_id": report.id,
            "photo_url": photo_url,
            "overlay_url": overlay_url,
        }
    finally:
        db.close()


@app.post("/api/v1/admin/casting-pool/{user_id}/match-request")
async def request_casting_match(user_id: str, admin_key: str, agency_name: str = "", purpose: str = "", fee: str = ""):
    """매칭 요청 → 유저에게 알림 (출연료 포함)."""
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")

    db = get_db()
    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            raise HTTPException(404, "유저를 찾을 수 없습니다")

        notif_id = str(uuid.uuid4())
        db.add(DBNotification(
            id=notif_id,
            user_id=user_id,
            type="casting_match",
            title=f"{agency_name}에서 캐스팅 제안이 도착했습니다",
            message=json.dumps({
                "agency_name": agency_name,
                "purpose": purpose,
                "fee": fee,
                "response": "pending",
                "requested_at": datetime.utcnow().isoformat() + "Z",
            }, ensure_ascii=False),
            link=f"/casting/invitation?id={notif_id}",
        ))
        db.commit()
        print(f"[CASTING] match request: user={user_id} agency={agency_name} fee={fee}")

        return {"status": "requested", "user_id": user_id, "notification_id": notif_id}
    finally:
        db.close()


@app.post("/api/v1/casting/respond/{notification_id}")
async def respond_casting(notification_id: str, response: str, user_id: str = ""):
    """유저가 캐스팅 제안 수락/거절."""
    if response not in ("accept", "decline"):
        raise HTTPException(400, "response는 accept 또는 decline이어야 합니다")
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")

    db = get_db()
    try:
        notif = db.query(DBNotification).filter(DBNotification.id == notification_id).first()
        if not notif:
            raise HTTPException(404, "알림을 찾을 수 없습니다")

        # message JSON 업데이트
        data = json.loads(notif.message) if notif.message else {}
        data["response"] = response
        data["responded_at"] = datetime.utcnow().isoformat() + "Z"
        notif.message = json.dumps(data, ensure_ascii=False)
        notif.is_read = True
        db.commit()
        print(f"[CASTING] user={notif.user_id} response={response}")

        return {"status": response, "notification_id": notification_id}
    finally:
        db.close()


@app.get("/api/v1/admin/casting-matches")
async def get_casting_matches(admin_key: str, status: str = "all"):
    """매칭 요청 목록 (어드민). status: all, pending, accept, decline"""
    if admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")
    if not _use_db():
        raise HTTPException(500, "DB를 사용할 수 없습니다")

    db = get_db()
    try:
        notifs = db.query(DBNotification)\
            .filter(DBNotification.type == "casting_match")\
            .order_by(DBNotification.created_at.desc())\
            .all()

        matches = []
        for n in notifs:
            data = json.loads(n.message) if n.message else {}
            resp = data.get("response", "pending")
            if status != "all" and resp != status:
                continue
            # 유저 이름 조회
            user = db.query(DBUser).filter(DBUser.id == n.user_id).first()
            user_name = user.name if user else ""
            matches.append({
                "notification_id": n.id,
                "user_id": n.user_id,
                "user_name": user_name,
                "agency_name": data.get("agency_name", ""),
                "purpose": data.get("purpose", ""),
                "fee": data.get("fee", ""),
                "response": resp,
                "requested_at": data.get("requested_at", ""),
                "responded_at": data.get("responded_at"),
            })

        counts = {"total": len(matches)}
        for s in ("pending", "accept", "decline"):
            counts[s] = sum(1 for m in matches if m["response"] == s)

        return {"matches": matches, "counts": counts}
    finally:
        db.close()


# ─────────────────────────────────────────────
#  알림 (Notifications)
# ─────────────────────────────────────────────

@app.get("/api/v1/notifications")
async def get_notifications(user_id: str):
    """로그인한 유저의 알림 목록 조회."""
    if not _use_db():
        return {"notifications": [], "unread_count": 0}
    db = get_db()
    try:
        notifs = db.query(DBNotification)\
            .filter(DBNotification.user_id == user_id)\
            .order_by(DBNotification.created_at.desc())\
            .limit(20)\
            .all()
        unread = sum(1 for n in notifs if not n.is_read)
        return {
            "notifications": [
                {
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "link": n.link,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() + "Z" if n.created_at else "",
                }
                for n in notifs
            ],
            "unread_count": unread,
        }
    finally:
        db.close()


@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """알림 읽음 처리."""
    if not _use_db():
        return {"status": "ok"}
    db = get_db()
    try:
        notif = db.query(DBNotification).filter(DBNotification.id == notification_id).first()
        if not notif:
            raise HTTPException(404, "알림을 찾을 수 없습니다")
        notif.is_read = True
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/api/v1/notifications/read-all")
async def mark_all_read(user_id: str):
    """유저의 전체 알림 읽음 처리."""
    if not _use_db():
        return {"status": "ok"}
    db = get_db()
    try:
        db.query(DBNotification)\
            .filter(DBNotification.user_id == user_id, DBNotification.is_read.is_(False))\
            .update({"is_read": True})
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


# ─────────────────────────────────────────────
#  마이페이지 (내 리포트)
# ─────────────────────────────────────────────

@app.get("/api/v1/my/reports")
async def get_my_reports(user_id: str):
    """로그인한 유저의 리포트 목록 조회."""
    return {"reports": _find_reports_for_user(user_id)}


# ─────────────────────────────────────────────
#  Static files & Health
# ─────────────────────────────────────────────

@app.post("/api/v1/admin/reset-db")
async def reset_db(data: ConfirmRequest):
    """DB 전체 초기화 — 모든 테이블 DROP 후 재생성."""
    if data.admin_key != ADMIN_KEY:
        raise HTTPException(403, "인증 실패")
    if not _use_db():
        raise HTTPException(500, "DB 미연결")
    from db import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from db import _migrate_columns
    _migrate_columns(engine)
    # 인메모리도 초기화
    USERS.clear()
    INTERVIEWS.clear()
    ANALYSES.clear()
    REPORTS.clear()
    ORDERS.clear()
    return {"status": "reset_complete", "message": "모든 테이블 삭제 후 재생성 완료"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0", "woz_mode": settings.use_mock_clip, "db_connected": _use_db()}
