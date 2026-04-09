"""
SIGAK API — FastAPI Application

Endpoints for the full PI diagnostic pipeline:
  Booking → Interview → Analysis → Report → Feedback
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

# 데이터 저장 디렉토리
DATA_DIR = Path(os.path.dirname(__file__)) / "uploads"
DATA_DIR.mkdir(exist_ok=True)


def _save_json(user_id: str, filename: str, data: dict):
    """유저별 JSON 데이터를 로컬 디스크에 저장."""
    user_dir = DATA_DIR / user_id
    user_dir.mkdir(exist_ok=True)
    with open(user_dir / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

from config import get_settings
from pipeline.face import analyze_face
from pipeline.coordinate import compute_coordinates, compute_gap, get_all_axis_labels, get_axis_names
from pipeline.llm import interpret_interview, generate_report, parse_or_fallback, interpret_face_structure
from pipeline.action_spec import build_action_spec, build_overlay_plan
from pipeline.similarity import find_similar_types, select_teaser_type
from pipeline.face_comparison import compare_with_top_anchors
from pipeline.cluster import classify_user, discover_clusters, load_cluster_labels
from pipeline.report_formatter import format_report_for_frontend, _sanitize
from pipeline.overlay_renderer import render_overlay
from payment import router as payment_router, PAYMENT_ACCOUNT

settings = get_settings()
app = FastAPI(title="SIGAK PI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Payment router
app.include_router(payment_router)


# ── In-memory store (replace with DB in production) ──
USERS = {}
INTERVIEWS = {}
ANALYSES = {}
REPORTS = {}

# ── 클러스터 부트스트랩 (cluster_labels.json 없으면 coords 기반 자동 생성) ──
_cluster_data = load_cluster_labels()
if not _cluster_data.get("clusters"):
    print("[부트스트랩] 클러스터 라벨 없음 — coords 기반 자동 생성")
    discover_clusters(gender="female")
    discover_clusters(gender="male")


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class BookingCreate(BaseModel):
    name: str
    phone: str
    gender: str  # female | male
    tier: str  # basic | creator | wedding
    booking_date: str  # "2026-04-15"
    booking_time: str  # "14:00"
    instagram: Optional[str] = None
    partner_name: Optional[str] = None
    partner_phone: Optional[str] = None
    channel_url: Optional[str] = None

class InterviewSubmit(BaseModel):
    interviewer_name: Optional[str] = None
    self_perception: Optional[str] = None
    desired_image: Optional[str] = None
    reference_celebs: Optional[str] = None
    style_keywords: Optional[str] = None
    current_concerns: Optional[str] = None
    daily_routine: Optional[str] = None
    raw_notes: Optional[str] = None
    # Wedding
    wedding_concept: Optional[str] = None
    dress_preference: Optional[str] = None
    # Creator
    content_style: Optional[str] = None
    target_audience: Optional[str] = None
    brand_tone: Optional[str] = None

class FeedbackSubmit(BaseModel):
    satisfaction_score: int  # 1–5
    usefulness_score: int    # 1–5
    feedback_text: Optional[str] = None
    would_repurchase: bool = False
    would_recommend: bool = False
    b2b_opt_in: bool = False
    b2b_categories: Optional[list[str]] = None


# ─────────────────────────────────────────────
#  1. Booking
# ─────────────────────────────────────────────

@app.post("/api/v1/booking")
async def create_booking(data: BookingCreate):
    user_id = str(uuid.uuid4())
    price_map = {"basic": 5000, "creator": 200000, "wedding": 200000}

    user = {
        "id": user_id,
        "status": "booked",
        "created_at": datetime.utcnow().isoformat(),
        "price": price_map.get(data.tier, 5000),
        **data.model_dump(),
    }
    USERS[user_id] = user
    _save_json(user_id, "booking.json", user)
    return {"user_id": user_id, "status": "booked", "price": user["price"]}


# ─────────────────────────────────────────────
#  2. Interview Data Submission (알바 dashboard)
# ─────────────────────────────────────────────

@app.post("/api/v1/interview/{user_id}")
async def submit_interview(user_id: str, data: InterviewSubmit):
    if user_id not in USERS:
        raise HTTPException(404, "User not found")

    interview = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        **data.model_dump(),
    }
    INTERVIEWS[user_id] = interview
    _save_json(user_id, "interview.json", interview)
    USERS[user_id]["status"] = "interviewed"

    return {"status": "interviewed", "interview_id": interview["id"]}


# ─────────────────────────────────────────────
#  3. Photo Upload
# ─────────────────────────────────────────────

@app.post("/api/v1/photos/{user_id}")
async def upload_photos(user_id: str, files: list[UploadFile] = File(...)):
    if user_id not in USERS:
        raise HTTPException(404, "User not found")

    # 사진 로컬 저장
    save_dir = DATA_DIR / user_id
    save_dir.mkdir(exist_ok=True)

    photo_results = []
    for f in files:
        contents = await f.read()
        # 로컬 디스크에 저장 (한글 파일명 → ASCII로 변환)
        ext = Path(f.filename or "photo.jpg").suffix or ".jpg"
        save_path = save_dir / f"photo_{len(photo_results)}{ext}"
        with open(save_path, "wb") as fp:
            fp.write(contents)

        face_result = analyze_face(contents)
        if face_result:
            photo_results.append({
                "filename": f.filename,
                "features": face_result.to_dict(),
                "landmarks_count": len(face_result.landmarks),
                "landmarks_106": face_result.landmarks_106,
                "bbox": face_result.bbox,
            })

    if not photo_results:
        raise HTTPException(400, "얼굴을 인식하지 못했어요. 정면을 바라보고, 밝은 곳에서 선글라스/마스크 없이 다시 촬영해 주세요.")

    # Use first photo's features as primary (multi-photo averaging later)
    # landmarks_106 + bbox도 저장 (overlay 렌더용)
    first_face = photo_results[0].get("_face_obj")
    ANALYSES[user_id] = {
        "photos": photo_results,
        "primary_features": photo_results[0]["features"],
        "landmarks_106": photo_results[0].get("landmarks_106", []),
        "bbox": photo_results[0].get("bbox", []),
    }
    _save_json(user_id, "face_analysis.json", ANALYSES[user_id])

    return {
        "status": "photos_processed",
        "faces_detected": len(photo_results),
        "primary_face_shape": photo_results[0]["features"]["face_shape"],
    }


# ─────────────────────────────────────────────
#  4. Run Analysis Pipeline
# ─────────────────────────────────────────────

@app.post("/api/v1/analyze/{user_id}")
async def run_analysis(user_id: str):
    """
    Full analysis pipeline (v2 — Action Spec 기반):
    1. CV features → coordinates (structural 100%)
    2. Type matching + comparison
    3. Interview → aspiration (LLM)
    4. Gap → Action Spec → Overlay Plan
    5. Report generation (LLM 해설) + parse fallback
    6. Action Spec ↔ 리포트 일치 검증
    """
    if user_id not in USERS:
        raise HTTPException(404, "User not found")
    if user_id not in INTERVIEWS:
        raise HTTPException(400, "Interview data not submitted yet")

    user = USERS[user_id]
    interview = INTERVIEWS[user_id]
    USERS[user_id]["status"] = "analyzing"

    # ── Step 1: Face analysis → coordinates (CLIP 비활성) ──
    gender = user.get("gender", "female")

    analysis = ANALYSES.get(user_id)
    if analysis:
        features = analysis["primary_features"]
        current_coords = compute_coordinates(features)
    else:
        features = {}
        current_coords = {"shape": 0, "volume": 0, "age": 0}

    # ── Step 2: Face structure interpretation (LLM) ──
    face_interpretation = {}
    if features:
        face_interpretation = interpret_face_structure(features)

    # ── Step 3: Type matching (좌표 기반) ──
    similar_types = find_similar_types(
        user_embedding=None,
        user_coords=current_coords,
        gender=gender,
        top_k=3,
    )

    # ── Step 4: Structural comparison ──
    type_comparisons = compare_with_top_anchors(
        user_features=features,
        similar_types=similar_types,
        gender=gender,
        max_compare=3,
    )

    # ── Step 5: Cluster classification ──
    cluster_result = classify_user(user_coords=current_coords, gender=gender)

    # ── Step 6: Interview → aspiration coordinates (LLM) ──
    aspiration_result = interpret_interview(interview, gender=gender)
    aspiration_coords = aspiration_result.get("coordinates", {
        "shape": 0, "volume": 0, "age": 0
    })

    # ── Step 6.5: 추구미 좌표 → 가장 가까운 앵커 확정 ──
    aspiration_similar = find_similar_types(
        user_embedding=None,
        user_coords=aspiration_coords,
        gender=gender,
        top_k=1,
    )
    aspiration_anchor = aspiration_similar[0] if aspiration_similar else None

    # ── Step 7: Gap calculation ──
    gap = compute_gap(current_coords, aspiration_coords)

    # ── Step 8: Action Spec 생성 ★ ──
    top_type = similar_types[0] if similar_types else {
        "key": "type_2", "name_kr": "차갑지만 동안",
        "similarity": 0.5, "mode": "coord",
    }
    action_spec = build_action_spec(
        face_features=features,
        current_coords=current_coords,
        matched_type=top_type,
        type_delta=type_comparisons[0]["axis_impacts"] if type_comparisons else {},
        gap=gap,
        interview_intent=aspiration_result.get("intent_tags"),
        gender=gender,
    )

    # ── Step 8.5: Overlay Plan 생성 ★ ──
    overlay_plan = build_overlay_plan(action_spec, features)

    # ── Step 8.6: Overlay 이미지 렌더링 ★ ──
    import cv2
    overlay_image_url = None
    # 유저 사진 로드 (첫 번째 사진)
    photo_dir = DATA_DIR / user_id
    photo_files = sorted(photo_dir.glob("*.jpg")) + sorted(photo_dir.glob("*.jpeg")) + sorted(photo_dir.glob("*.png"))
    if photo_files and analysis and analysis["primary_features"]:
        # Windows 한글 경로 대응: np.fromfile + imdecode
        photo_img = cv2.imdecode(np.fromfile(str(photo_files[0]), dtype=np.uint8), cv2.IMREAD_COLOR)
        if photo_img is not None:
            lmk106 = analysis.get("landmarks_106")
            face_bbox = analysis.get("bbox")
            if lmk106:
                overlay_plan_dicts = [
                    {"zone": z.zone_name, "type": z.zone_type, "color": z.color_hex, "opacity": z.opacity}
                    for z in overlay_plan
                ]
                overlay_img = render_overlay(
                    img=photo_img,
                    landmarks_106=np.array(lmk106),
                    overlay_plan=overlay_plan_dicts,
                    face_type=features.get("face_shape", ""),
                    bbox=np.array(face_bbox) if face_bbox else None,
                )
                if overlay_img is not None:
                    overlay_path = photo_dir / "overlay.png"
                    cv2.imwrite(str(overlay_path), overlay_img)
                    overlay_image_url = f"/api/v1/uploads/{user_id}/overlay.png"

    # ── Step 9: Report generation (축소된 입력) ★ ──
    raw_report = generate_report(action_spec, {
        "name": user["name"],
        "face_shape": features.get("face_shape", ""),
        "tier": user["tier"],
        "gender": gender,
        "aspiration_summary": aspiration_result.get("interpretation", ""),
        "primary_gap_direction_kr": gap.get("primary_shift_kr", ""),
    })
    report_content = parse_or_fallback(raw_report, action_spec)

    # ── Step 9.5: Action Spec ↔ 리포트 일치 검증 ★ ──
    action_tips = report_content.get("action_tips", [])
    if len(action_tips) != len(action_spec.recommended_actions):
        # 불일치 시 fallback 리포트로 교체
        report_content = parse_or_fallback("", action_spec)
        action_tips = report_content.get("action_tips", [])

    for tip, rec in zip(action_tips, action_spec.recommended_actions):
        if tip.get("zone") != rec.zone:
            # zone 불일치 시 강제 교정
            tip["zone"] = rec.zone

    # ── 프론트엔드용 리포트 포매팅 ──
    formatted_report = format_report_for_frontend(
        user_id=user_id,
        user_name=user["name"],
        tier=user["tier"],
        gender=gender,
        face_features=features,
        current_coords=current_coords,
        aspiration_coords=aspiration_coords,
        gap=gap,
        similar_types=similar_types,
        face_interpretation=face_interpretation,
        report_content=report_content,
        aspiration_interpretation=aspiration_result,
        aspiration_anchor=aspiration_anchor,
    )

    # ── Store report ──
    from dataclasses import asdict
    teaser_type = select_teaser_type(similar_types)
    report_id = str(uuid.uuid4())
    # overlay URL을 formatted report에 삽입
    if overlay_image_url:
        # 원본 사진 URL도 함께
        original_photos = sorted(photo_dir.glob("*.jpg")) + sorted(photo_dir.glob("*.jpeg")) + sorted(photo_dir.glob("*.png"))
        original_photos = [p for p in original_photos if p.name != "overlay.png"]
        original_url = f"/api/v1/uploads/{user_id}/{original_photos[0].name}" if original_photos else None
        formatted_report["overlay"] = {
            "before_url": original_url,
            "after_url": overlay_image_url,
        }

    report = {
        "id": report_id,
        "user_id": user_id,
        "formatted": formatted_report,
        # 디버깅/대시보드용
        "face_interpretation": face_interpretation,
        "current_coords": current_coords,
        "aspiration_coords": aspiration_coords,
        "gap": gap,
        "aspiration_interpretation": aspiration_result,
        "similar_types": similar_types,
        "type_comparisons": type_comparisons,
        "cluster": cluster_result,
        "teaser_type": teaser_type,
        "action_spec_debug": action_spec._debug_trace,
        "overlay_plan": [
            {"zone": z.zone_name, "type": z.zone_type, "color": z.color_hex, "opacity": z.opacity}
            for z in overlay_plan
        ],
        "overlay_image_url": overlay_image_url,
        "content": report_content,
        "created_at": datetime.utcnow().isoformat(),
        "access_level": "free",
        "pending_level": None,
        "payment_1_at": None,
        "payment_2_at": None,
    }
    REPORTS[user_id] = _sanitize(report)
    _save_json(user_id, "report.json", REPORTS[user_id])
    USERS[user_id]["status"] = "reported"

    return {
        "status": "reported",
        "report_id": report_id,
        "current_coords": current_coords,
        "aspiration_coords": aspiration_coords,
        "similar_types": [
            {"name": c["name_kr"], "similarity_pct": c["similarity_pct"]}
            for c in similar_types
        ],
        "cluster": cluster_result.get("cluster_label_kr") if cluster_result else None,
        "teaser": f"{teaser_type['name_kr']}와 {teaser_type['similarity_pct']}% 유사" if teaser_type else None,
        "action_count": len(action_spec.recommended_actions),
    }


# ─────────────────────────────────────────────
#  5. Get Report
# ─────────────────────────────────────────────

@app.get("/api/v1/report/{user_id}")
async def get_report(user_id: str):
    """
    프론트엔드 ReportData 형식으로 리포트를 반환한다.

    formatted 키에 저장된 프론트엔드 구조를 직접 반환하되,
    결제 상태(access_level, pending_level)를 실시간으로 반영한다.
    """
    if user_id not in REPORTS:
        raise HTTPException(404, "Report not found")
    report = REPORTS[user_id]

    # 포맷된 리포트가 있으면 프론트엔드 구조로 반환
    if "formatted" in report:
        response = {**report["formatted"]}
        # 결제 상태를 실시간으로 반영 (결제 후 access_level 변경)
        response["access_level"] = report.get("access_level", "free")
        response["pending_level"] = report.get("pending_level")

        # access_level에 따라 섹션 잠금 상태 업데이트
        level_order = {"free": 0, "standard": 1, "full": 2}
        current_level = level_order.get(response["access_level"], 0)

        for section in response.get("sections", []):
            unlock = section.get("unlock_level")
            if unlock:
                required_level = level_order.get(unlock, 0)
                section["locked"] = current_level < required_level

        return response

    # 폴백: 기존 형식 (formatted가 없는 경우 하위 호환)
    response = {**report}
    response.pop("formatted", None)
    response["pending_level"] = report.get("pending_level")
    response["access_level"] = report.get("access_level", "free")
    response["paywall"] = {
        "standard": {"price": 5000, "label": "\u20A95,000 잠금 해제", "method": "manual"},
        "full": {"price": 15000, "label": "+\u20A915,000 잠금 해제", "total_note": "이전 결제 포함 총 \u20A920,000", "method": "manual"},
    }
    response["payment_account"] = PAYMENT_ACCOUNT
    return response


# ─────────────────────────────────────────────
#  6. Submit Feedback (H2 + H3 + H4 validation)
# ─────────────────────────────────────────────

@app.post("/api/v1/feedback/{user_id}")
async def submit_feedback(user_id: str, data: FeedbackSubmit):
    if user_id not in REPORTS:
        raise HTTPException(404, "Report not found")

    REPORTS[user_id]["feedback"] = data.model_dump()
    USERS[user_id]["status"] = "feedback_done"

    return {"status": "feedback_recorded"}


# ─────────────────────────────────────────────
#  Dashboard Endpoints (알바 + admin)
# ─────────────────────────────────────────────

@app.get("/api/v1/dashboard/queue")
async def get_queue():
    """Get list of users pending interview or analysis."""
    queue = []
    for uid, u in USERS.items():
        queue.append({
            "id": uid,
            "name": u["name"],
            "gender": u.get("gender", "female"),
            "tier": u["tier"],
            "status": u["status"],
            "booking_date": u["booking_date"],
            "booking_time": u["booking_time"],
            "has_interview": uid in INTERVIEWS,
            "has_photos": uid in ANALYSES,
            "has_report": uid in REPORTS,
        })
    return sorted(queue, key=lambda x: (x["booking_date"], x["booking_time"]))


@app.get("/api/v1/dashboard/stats")
async def get_stats():
    """Dashboard statistics for hypothesis validation."""
    total = len(USERS)
    interviewed = sum(1 for u in USERS.values() if u["status"] != "booked")
    reported = sum(1 for u in USERS.values() if u["status"] in ("reported", "feedback_done"))

    feedbacks = [r.get("feedback", {}) for r in REPORTS.values() if r.get("feedback")]
    avg_satisfaction = (
        sum(f.get("satisfaction_score", 0) for f in feedbacks) / len(feedbacks)
        if feedbacks else 0
    )
    avg_usefulness = (
        sum(f.get("usefulness_score", 0) for f in feedbacks) / len(feedbacks)
        if feedbacks else 0
    )
    opt_in_count = sum(1 for f in feedbacks if f.get("b2b_opt_in"))
    repurchase_count = sum(1 for f in feedbacks if f.get("would_repurchase"))

    return {
        "total_bookings": total,
        "interviewed": interviewed,
        "reports_sent": reported,
        "feedbacks_received": len(feedbacks),
        # H2: Product value
        "avg_satisfaction": round(avg_satisfaction, 2),
        "avg_usefulness": round(avg_usefulness, 2),
        "nps_target": 4.2,
        "nps_met": avg_usefulness >= 4.2,
        # H3: BM validation
        "conversion_rate": round(total / max(1, total) * 100, 1),  # Needs funnel data
        # H4: Growth
        "b2b_opt_in_count": opt_in_count,
        "b2b_opt_in_rate": round(opt_in_count / max(1, len(feedbacks)) * 100, 1),
        "repurchase_rate": round(repurchase_count / max(1, len(feedbacks)) * 100, 1),
    }


# ─────────────────────────────────────────────
#  Coordinate System Info
# ─────────────────────────────────────────────

@app.get("/api/v1/axes")
async def get_axes():
    """Return axis definitions for frontend rendering."""
    all_labels = get_all_axis_labels()
    return [
        {
            "name": name,
            "name_kr": labels["name_kr"],
            "negative": {"label": labels["low_en"], "label_kr": labels["low"]},
            "positive": {"label": labels["high_en"], "label_kr": labels["high"]},
        }
        for name, labels in all_labels.items()
    ]


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  Overlay / 사진 정적 서빙
# ─────────────────────────────────────────────

from fastapi.responses import FileResponse

@app.get("/api/v1/uploads/{user_id}/{filename}")
async def serve_upload(user_id: str, filename: str):
    """유저 사진/오버레이 이미지 서빙."""
    file_path = DATA_DIR / user_id / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mt = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(file_path), media_type=mt)


@app.get("/api/v1/photos/{user_id}/original")
async def get_original_photo(user_id: str):
    """원본 사진 URL 반환 (before/after용)."""
    photo_dir = DATA_DIR / user_id
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        photos = sorted(photo_dir.glob(ext))
        photos = [p for p in photos if p.name != "overlay.png"]
        if photos:
            return {"url": f"/api/v1/uploads/{user_id}/{photos[0].name}"}
    raise HTTPException(404, "No photo found")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "woz_mode": settings.use_mock_clip}
