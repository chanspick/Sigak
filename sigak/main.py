"""
SIGAK API — FastAPI Application

Endpoints for the full PI diagnostic pipeline:
  Booking → Interview → Analysis → Report → Feedback
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from config import get_settings
from pipeline.face import analyze_face
from pipeline.coordinate import (
    compute_coordinates, compute_gap,
    mock_clip_embedding, mock_anchor_projector, AXES,
)
from pipeline.llm import interpret_interview, generate_report
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

# ── WoZ: Mock CLIP projector ──
PROJECTOR = mock_anchor_projector()


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class BookingCreate(BaseModel):
    name: str
    phone: str
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
    price_map = {"basic": 50000, "creator": 200000, "wedding": 200000}

    user = {
        "id": user_id,
        "status": "booked",
        "created_at": datetime.utcnow().isoformat(),
        "price": price_map.get(data.tier, 50000),
        **data.model_dump(),
    }
    USERS[user_id] = user
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
    USERS[user_id]["status"] = "interviewed"

    return {"status": "interviewed", "interview_id": interview["id"]}


# ─────────────────────────────────────────────
#  3. Photo Upload
# ─────────────────────────────────────────────

@app.post("/api/v1/photos/{user_id}")
async def upload_photos(user_id: str, files: list[UploadFile] = File(...)):
    if user_id not in USERS:
        raise HTTPException(404, "User not found")

    photo_results = []
    for f in files:
        contents = await f.read()
        # In production: upload to S3
        # For now: store analysis result
        face_result = analyze_face(contents)
        if face_result:
            photo_results.append({
                "filename": f.filename,
                "features": face_result.to_dict(),
                "landmarks_count": len(face_result.landmarks),
            })

    if not photo_results:
        raise HTTPException(400, "No valid face detected in uploaded photos")

    # Use first photo's features as primary (multi-photo averaging later)
    ANALYSES[user_id] = {
        "photos": photo_results,
        "primary_features": photo_results[0]["features"],
    }

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
    Triggers the full analysis pipeline:
    1. CV features → coordinates
    2. Interview → aspiration coordinates (LLM)
    3. Gap calculation
    4. Report generation (LLM)
    """
    if user_id not in USERS:
        raise HTTPException(404, "User not found")
    if user_id not in INTERVIEWS:
        raise HTTPException(400, "Interview data not submitted yet")

    user = USERS[user_id]
    interview = INTERVIEWS[user_id]
    USERS[user_id]["status"] = "analyzing"

    # ── Step 1: Get face features + compute coordinates ──
    analysis = ANALYSES.get(user_id)
    if analysis:
        features = analysis["primary_features"]
        # WoZ: mock CLIP embedding (replace with real CLIP later)
        mock_emb = mock_clip_embedding(str(features).encode())
        current_coords = compute_coordinates(features, mock_emb, PROJECTOR)
    else:
        # No photo uploaded — use neutral coordinates (manual override needed)
        features = {}
        current_coords = {"structure": 0, "impression": 0, "maturity": 0, "intensity": 0}

    # ── Step 2: Interpret interview → aspiration coordinates ──
    aspiration_result = interpret_interview(interview)
    aspiration_coords = aspiration_result.get("coordinates", {
        "structure": 0, "impression": 0, "maturity": 0, "intensity": 0
    })

    # ── Step 3: Compute gap ──
    gap = compute_gap(current_coords, aspiration_coords)

    # ── Step 4: Generate report ──
    report_content = generate_report(
        user_name=user["name"],
        tier=user["tier"],
        face_features=features,
        current_coords=current_coords,
        aspiration_coords=aspiration_coords,
        gap=gap,
        interview_data=interview,
        aspiration_interpretation=aspiration_result,
    )

    # ── Store report ──
    report_id = str(uuid.uuid4())
    report = {
        "id": report_id,
        "user_id": user_id,

        "current_coords": current_coords,
        "aspiration_coords": aspiration_coords,
        "gap": gap,
        "aspiration_interpretation": aspiration_result,
        "content": report_content,
        "created_at": datetime.utcnow().isoformat(),
        "access_level": "free",
        "pending_level": None,
        "payment_1_at": None,
        "payment_2_at": None,
    }
    REPORTS[user_id] = report
    USERS[user_id]["status"] = "reported"

    return {
        "status": "reported",
        "report_id": report_id,
        "current_coords": current_coords,
        "aspiration_coords": aspiration_coords,
        "gap_magnitude": gap["magnitude"],
        "gap_primary": f"{gap['primary_direction']} → {gap['primary_shift_kr']}",
    }


# ─────────────────────────────────────────────
#  5. Get Report
# ─────────────────────────────────────────────

@app.get("/api/v1/report/{user_id}")
async def get_report(user_id: str):
    if user_id not in REPORTS:
        raise HTTPException(404, "Report not found")
    report = REPORTS[user_id]
    # Add payment info to response
    response = {**report}
    response["pending_level"] = report.get("pending_level")
    response["access_level"] = report.get("access_level", "free")
    response["paywall"] = {
        "standard": {"price": 20000, "label": "₩20,000 unlock", "method": "manual"},
        "full": {"price": 30000, "label": "+₩30,000 unlock", "total_note": "Total ₩50,000", "method": "manual"},
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
    return [
        {
            "name": ax.name,
            "name_kr": ax.name_kr,
            "negative": {"label": ax.negative_label, "label_kr": ax.negative_label_kr},
            "positive": {"label": ax.positive_label, "label_kr": ax.positive_label_kr},
        }
        for ax in AXES
    ]


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "woz_mode": settings.use_mock_clip}
