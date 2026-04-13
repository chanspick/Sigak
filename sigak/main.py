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
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import httpx

from db import init_db, get_db, User as DBUser, Order as DBOrder, Report as DBReport


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

# 가격표
PRICE_MAP = {
    "standard": 5000,    # 오버뷰 (블러 해제는 추가 결제)
    "full": 49000,       # 풀 리포트 (처음부터 전부 열림)
}
# 오버뷰 → 풀 업그레이드 가격
UPGRADE_PRICE = 44000

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
    name: str
    phone: str
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
async def submit(data: str = "", files: list[UploadFile] = File(...)):
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
        raise HTTPException(400, "질문지 데이터를 파싱할 수 없습니다")

    user_id = str(uuid.uuid4())
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    tier = submit_data.tier if submit_data.tier in PRICE_MAP else "full"
    amount = PRICE_MAP[tier]
    print(f"[SUBMIT] parsed tier={submit_data.tier!r} → resolved tier={tier!r} amount={amount}")

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
        "created_at": datetime.utcnow().isoformat(),
        **submit_data.model_dump(),
    }
    INTERVIEWS[user_id] = interview
    _save_json(user_id, "interview.json", interview)

    # 4. 유저 저장
    user = {
        "id": user_id,
        "name": submit_data.name,
        "phone": submit_data.phone,
        "gender": submit_data.gender,
        "tier": tier,
        "status": "pending_payment",
        "created_at": datetime.utcnow().isoformat(),
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
        "created_at": datetime.utcnow().isoformat(),
        "report_id": None,
    }
    ORDERS[order_id] = order
    _save_json(user_id, "order.json", order)

    # 5.5. DB 저장 (dual-write)
    if _use_db():
        db = get_db()
        try:
            db.merge(DBUser(
                id=user_id,
                name=submit_data.name,
                phone=submit_data.phone,
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
                    "user_name": submit_data.name,
                    "phone": submit_data.phone,
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
                    "created_at": db_order.created_at.isoformat() if db_order.created_at else "",
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
    if order["status"] != "pending_payment":
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
                        "created_at": db_user.created_at.isoformat() if db_user.created_at else "",
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
    order["completed_at"] = datetime.utcnow().isoformat()
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

    # Step 9: LLM 리포트
    raw_report = generate_report(action_spec, {
        "name": user["name"], "face_shape": features.get("face_shape", ""),
        "tier": user["tier"], "gender": gender,
        "aspiration_summary": aspiration_result.get("interpretation", ""),
        "primary_gap_direction_kr": gap.get("primary_shift_kr", ""),
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
        "created_at": datetime.utcnow().isoformat(),
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
                    "created_at": db_report.created_at.isoformat() if db_report.created_at else "",
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

    if not report:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")

    if "formatted" in report:
        response = {**report["formatted"]}
        access = report.get("access_level", "standard")
        response["access_level"] = access
        response["pending_level"] = report.get("pending_level")

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
                    "price": 44000,
                    "label": "풀 리포트 언락",
                    "total_note": "기존 ₩5,000 + 추가 ₩44,000 = 총 ₩49,000",
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
    """유저가 ₩44,000 풀 업그레이드 요청. 주문 생성 + 웹훅 (신규 주문과 동일 플로우)."""
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
    user = USERS.get(user_id, {})

    # DB에서 user 가져오기
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
        "created_at": datetime.utcnow().isoformat(),
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
    report["upgraded_at"] = datetime.utcnow().isoformat()

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
    user = {"id": user_id, "status": "booked", "created_at": datetime.utcnow().isoformat(), "price": PRICE_MAP.get(data.tier, 5000), **data.model_dump()}
    USERS[user_id] = user
    _save_json(user_id, "booking.json", user)

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
    # 인메모리 또는 DB에서 유저 확인
    user_exists = user_id in USERS
    if not user_exists and _use_db():
        db = get_db()
        try:
            user_exists = db.query(DBUser).filter(DBUser.id == user_id).first() is not None
        except Exception:
            pass
        finally:
            db.close()

    if not user_exists:
        raise HTTPException(404, "User not found")
    interview = {"id": str(uuid.uuid4()), "user_id": user_id, "created_at": datetime.utcnow().isoformat(), **data.model_dump()}
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
    # 인메모리 또는 DB에서 유저 확인
    user_exists = user_id in USERS
    if not user_exists and _use_db():
        db = get_db()
        try:
            user_exists = db.query(DBUser).filter(DBUser.id == user_id).first() is not None
        except Exception:
            pass
        finally:
            db.close()

    if not user_exists:
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
    # 인메모리 또는 DB에서 유저/인터뷰 확인
    user_exists = user_id in USERS
    interview_exists = user_id in INTERVIEWS
    user_data = USERS.get(user_id, {})
    interview_data = INTERVIEWS.get(user_id, {})
    analysis_data = ANALYSES.get(user_id)

    if not user_exists and _use_db():
        db = get_db()
        try:
            db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if db_user:
                user_exists = True
                user_data = {
                    "id": db_user.id,
                    "name": db_user.name,
                    "phone": db_user.phone,
                    "gender": db_user.gender or "female",
                    "tier": db_user.tier or "full",
                    "status": db_user.status or "booked",
                }
        except Exception:
            pass
        finally:
            db.close()

    if not user_exists:
        raise HTTPException(404, "User not found")
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
                        "created_at": o.created_at.isoformat() if o.created_at else "",
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0", "woz_mode": settings.use_mock_clip, "db_connected": _use_db()}
