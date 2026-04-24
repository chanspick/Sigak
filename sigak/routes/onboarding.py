"""Onboarding endpoints (MVP v1.2 + v2 essentials).

v1.2 (legacy, Sia 대체 대상):
  POST /api/v1/onboarding/save-step   shallow-merge fields, auto-flip completed on step 4
  GET  /api/v1/onboarding/state       current progress + next_step hint
  POST /api/v1/onboarding/reset       unset completed; preserve onboarding_data for pre-fill

v2 (SPEC-ONBOARDING-V2 REQ-ONBD-001/002):
  POST /api/v1/onboarding/essentials  Step 0 structured input (gender/birth_date/ig_handle)
                                      Sia 대화 진입 전 구조화 필드 확보.

Data shape (v1 save-step) is flat — keys match Pydantic ``SubmitRequest`` in main.py — so the
existing pipeline entrypoint ``_run_analysis_pipeline`` can read onboarding_data
directly as the interview payload without transformation.
"""
import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from deps import db_session, get_current_user


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ─────────────────────────────────────────────
#  Required fields per step (spec: Q-V2-3)
# ─────────────────────────────────────────────

# ``reference_celebs`` and ``current_concerns`` are optional — excluded here.
REQUIRED_FIELDS_BY_STEP: dict[int, list[str]] = {
    1: ["height", "weight", "shoulder_width", "neck_length"],
    2: ["face_concerns"],
    3: ["style_image_keywords", "desired_image", "makeup_level"],
    4: ["self_perception"],
}

ALL_REQUIRED_FIELDS: list[str] = [
    f for fields in REQUIRED_FIELDS_BY_STEP.values() for f in fields
]


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class SaveStepRequest(BaseModel):
    step: Literal[1, 2, 3, 4]
    fields: Dict[str, Any] = Field(default_factory=dict)


class SaveStepResponse(BaseModel):
    onboarding_data: Dict[str, Any]
    completed: bool


class StateResponse(BaseModel):
    onboarding_completed: bool
    onboarding_data: Optional[Dict[str, Any]]
    next_step: Optional[int]


class ResetResponse(BaseModel):
    onboarding_completed: bool


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _compute_next_step(data: Dict[str, Any], completed: bool) -> Optional[int]:
    """Returns first step whose required field is missing. None if completed."""
    if completed:
        return None
    for step in (1, 2, 3, 4):
        for field in REQUIRED_FIELDS_BY_STEP[step]:
            if not data.get(field):
                return step
    # All required present but completion not flipped — nudge to step 4
    # so the next save-step call triggers the auto-completion check.
    return 4


def _load_user_onboarding(db, user_id: str) -> tuple[Dict[str, Any], bool]:
    row = db.execute(
        text(
            "SELECT onboarding_data, onboarding_completed "
            "FROM users WHERE id = :uid"
        ),
        {"uid": user_id},
    ).first()
    if row is None:
        raise HTTPException(404, "user not found")
    data = row.onboarding_data or {}
    return data, bool(row.onboarding_completed)


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@router.post("/save-step", response_model=SaveStepResponse)
def save_step(
    body: SaveStepRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Shallow-merge incoming ``fields`` into ``onboarding_data``.

    Step ordering is NOT enforced server-side — frontend routing decides what
    screen to show. We accept any step's fields and just merge them.

    Auto-completion fires only when ``step=4`` is saved AND all 9 required
    fields (REQUIRED_FIELDS_BY_STEP flattened) are present in the merged
    result. Once flipped, stays True until ``/reset`` is called.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Shallow-merge via PG JSONB concat. COALESCE handles NULL start state.
    db.execute(
        text(
            "UPDATE users "
            "SET onboarding_data = COALESCE(onboarding_data, '{}'::jsonb) || CAST(:fields AS jsonb) "
            "WHERE id = :uid"
        ),
        {"fields": json.dumps(body.fields), "uid": user["id"]},
    )

    # 2. Re-read merged state.
    merged, already_completed = _load_user_onboarding(db, user["id"])
    completed = already_completed

    # 3. Step 4 auto-complete check.
    if body.step == 4 and not already_completed:
        if all(merged.get(f) for f in ALL_REQUIRED_FIELDS):
            db.execute(
                text("UPDATE users SET onboarding_completed = TRUE WHERE id = :uid"),
                {"uid": user["id"]},
            )
            completed = True

    db.commit()
    return SaveStepResponse(onboarding_data=merged, completed=completed)


@router.get("/state", response_model=StateResponse)
def get_state(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Return current progress so frontend can route user to the right step."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    data, completed = _load_user_onboarding(db, user["id"])
    return StateResponse(
        onboarding_completed=completed,
        onboarding_data=data if data else None,
        next_step=_compute_next_step(data, completed),
    )


@router.post("/reset", response_model=ResetResponse)
def reset(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Flip ``onboarding_completed`` back to False. Keep ``onboarding_data``
    intact so the user can edit rather than re-enter from scratch.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 시각 재설정 시 리포트도 다시 잠기게 (release는 idempotent라 재해제 시 추가 차감 없음)
    db.execute(
        text(
            "UPDATE users SET "
            "  onboarding_completed = FALSE, "
            "  sigak_report_released = FALSE "
            "WHERE id = :uid"
        ),
        {"uid": user["id"]},
    )
    db.commit()
    return ResetResponse(onboarding_completed=False)


# ─────────────────────────────────────────────
#  Essentials — Step 0 structured input (SPEC-ONBOARDING-V2 REQ-ONBD-001/002)
# ─────────────────────────────────────────────
#
# Sia 대화(/sia/new) 진입 전에 수집할 구조화 필드:
#   - gender: 진단 엔진 분기 (female/male)
#   - birth_date: 연령 기반 분석 + 만 14세 이상 강제 (consent age_confirmed 와 정합)
#   - ig_handle: (선택) Apify IG 자동 수집 연결
#
# 저장 위치:
#   - users 테이블 (primary) — gender/birth_date/ig_handle 컬럼 직접 갱신
#   - user_profiles 테이블 (v2 profile cache) — upsert. Sia extraction 결과와 합쳐질 row.

MIN_AGE_YEARS = 14

# IG handle: A-Z/a-z/0-9/./_ 최대 30자 (Instagram 공식 규칙 + 50 컬럼 여유)
IG_HANDLE_PATTERN = re.compile(r"[A-Za-z0-9._]{1,30}")


class EssentialsRequest(BaseModel):
    gender: Literal["female", "male"]
    birth_date: date  # FastAPI 가 YYYY-MM-DD 문자열 → date 로 변환
    ig_handle: Optional[str] = Field(default=None, max_length=50)


class EssentialsResponse(BaseModel):
    essentials_completed: bool
    gender: str
    birth_date: str  # ISO 날짜 (YYYY-MM-DD)
    ig_handle: Optional[str]
    # IG wiring — 비동기 fetch 트리거 결과 시그널
    #   pending : ig_handle 있음, BackgroundTask 예약됨. 프론트는 ig-status 폴링 시작
    #   skipped : ig_handle 없음. 프론트는 즉시 Sia 진입 가능
    ig_fetch_status: Literal["pending", "skipped"] = "skipped"


class IgStatusResponse(BaseModel):
    """GET /api/v1/onboarding/ig-status — 프론트 폴링용.

    상태:
      pending          — essentials 직후, 아직 Apify 호출 시작 전/중
      pending_vision   — Apify 성공 + preview DB flush 완료, Vision 진행 중
                         → preview_urls 렌더 시작해도 OK
      success / private / failed / skipped — 최종 상태 (Sia 진입 허용)

    preview_urls 는 pending_vision 부터 채워짐. Instagram CDN URL (TTL 24-48h).
    """
    status: str
    preview_urls: List[str] = Field(default_factory=list)
    username: Optional[str] = None
    analyzed: bool = False


def _normalize_ig_handle(raw: Optional[str]) -> Optional[str]:
    """빈 문자열/공백/None → None. 앞 '@' 제거 + 규칙 검증."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if s.startswith("@"):
        s = s[1:]
    if not IG_HANDLE_PATTERN.fullmatch(s):
        raise HTTPException(
            400,
            "ig_handle 은 영문/숫자/./_ 로 30자 이내여야 합니다",
        )
    return s


def _ensure_min_age(birth: date) -> None:
    """만 14세 미만 거부. consent age_confirmed 와 정합."""
    today = date.today()
    years = today.year - birth.year - (
        (today.month, today.day) < (birth.month, birth.day)
    )
    if years < MIN_AGE_YEARS:
        raise HTTPException(
            400,
            f"만 {MIN_AGE_YEARS}세 이상만 이용 가능해요",
        )
    if birth > today:
        raise HTTPException(400, "생년월일이 미래일 수 없어요")


@router.post("/essentials", response_model=EssentialsResponse)
def save_essentials(
    body: EssentialsRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Step 0 structured input — gender + birth_date + ig_handle (optional).

    SPEC-ONBOARDING-V2 REQ-ONBD-001/002.
    users (primary) + user_profiles (v2 profile cache) 동시 갱신.
    Sia 대화(/sia/new) 진입 전에 반드시 호출되어야 함.

    IG wiring (신규):
      - ig_handle 있을 때 BackgroundTask 로 Apify + Vision 비동기 수집 시작.
      - preview cache 먼저 flush → 프론트가 ig-status 폴링으로 미리보기 렌더.
      - Vision 완료 후 최종 flush (status=success).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    _ensure_min_age(body.birth_date)
    ig_handle = _normalize_ig_handle(body.ig_handle)

    # 1. users 테이블 업데이트 (v1 primary).
    db.execute(
        text(
            "UPDATE users SET "
            "  gender = :gender, "
            "  birth_date = :birth_date, "
            "  ig_handle = :ig_handle "
            "WHERE id = :uid"
        ),
        {
            "gender": body.gender,
            "birth_date": body.birth_date.isoformat(),
            "ig_handle": ig_handle,
            "uid": user["id"],
        },
    )

    # 2. user_profiles upsert (v2 profile). Sia extraction 결과가 합쳐질 row.
    #    ig_handle 있으면 ig_fetch_status='pending' 으로 초기화.
    initial_ig_status = "pending" if ig_handle else None
    db.execute(
        text(
            "INSERT INTO user_profiles "
            "  (user_id, gender, birth_date, ig_handle, ig_fetch_status) "
            "VALUES (:uid, :gender, :birth_date, :ig_handle, :ig_status) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "  gender = EXCLUDED.gender, "
            "  birth_date = EXCLUDED.birth_date, "
            "  ig_handle = EXCLUDED.ig_handle, "
            "  ig_fetch_status = EXCLUDED.ig_fetch_status, "
            "  updated_at = NOW()"
        ),
        {
            "gender": body.gender,
            "birth_date": body.birth_date.isoformat(),
            "ig_handle": ig_handle,
            "ig_status": initial_ig_status,
            "uid": user["id"],
        },
    )

    db.commit()

    # 3. IG 비동기 fetch — handle 있을 때만
    ig_fetch_signal: Literal["pending", "skipped"] = "skipped"
    if ig_handle:
        background_tasks.add_task(
            _run_ig_fetch_job,
            user_id=user["id"],
            ig_handle=ig_handle,
        )
        ig_fetch_signal = "pending"

    return EssentialsResponse(
        essentials_completed=True,
        gender=body.gender,
        birth_date=body.birth_date.isoformat(),
        ig_handle=ig_handle,
        ig_fetch_status=ig_fetch_signal,
    )


# ─────────────────────────────────────────────
#  GET /ig-status — 프론트 대기 화면 폴링 엔드포인트
# ─────────────────────────────────────────────

@router.get("/ig-status", response_model=IgStatusResponse)
def get_ig_status(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """현 유저의 IG fetch 진행 상황 조회. 2-3 초 간격 폴링 전제.

    preview_urls: 최대 6장 (pending_vision 부터 렌더 시작 가능).
    analyzed: Vision 분석 완료 여부. False + status=pending_vision = 로딩 중.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    from services.user_profiles import get_profile
    profile = get_profile(db, user["id"])
    if profile is None:
        raise HTTPException(404, "user_profile not found")

    status = profile.get("ig_fetch_status") or "skipped"
    cache = profile.get("ig_feed_cache") or {}

    preview_urls: List[str] = []
    username: Optional[str] = None
    analyzed = False

    if cache:
        basics = cache.get("profile_basics") or {}
        username = basics.get("username")
        posts = cache.get("latest_posts") or []
        preview_urls = [
            p.get("display_url") for p in posts
            if isinstance(p, dict) and p.get("display_url")
        ][:6]
        analyzed = cache.get("analysis") is not None

    return IgStatusResponse(
        status=status,
        preview_urls=preview_urls,
        username=username,
        analyzed=analyzed,
    )


# ─────────────────────────────────────────────
#  BackgroundTask — 분리 저장 Apify + Vision
# ─────────────────────────────────────────────

def _run_ig_fetch_job(user_id: str, ig_handle: str) -> None:
    """Apify 수집 + preview flush + Vision + 최종 flush.

    상태 전이:
      pending (essentials 직후)
      → pending_vision (preview flush 완료)
      → success | private | failed | skipped (최종)

    각 전이마다 user_profiles.ig_fetch_status 업데이트 + db.commit().
    BackgroundTask 는 독립 DB session (request session 은 이미 close 됨).
    """
    from db import get_db
    from services import ig_scraper, user_profiles

    db = get_db()
    if db is None:
        logger.error(
            "ig_fetch job: DB unavailable user=%s (IG 상태 pending 유지)",
            user_id,
        )
        return

    try:
        # 1. Apify 수집 (Vision 미실행)
        status, preview_cache = ig_scraper.fetch_ig_raw(ig_handle)

        if status != "success" or preview_cache is None:
            # private / failed / skipped — 단일 flush
            user_profiles.upsert_ig_feed_cache(
                db, user_id=user_id, cache=preview_cache, status=status,
            )
            db.commit()
            logger.info(
                "ig_fetch job: user=%s status=%s (no vision)",
                user_id, status,
            )
            return

        # 2. Preview 선 flush (pending_vision)
        user_profiles.upsert_ig_feed_cache(
            db, user_id=user_id, cache=preview_cache, status="pending_vision",
        )
        db.commit()
        logger.info(
            "ig_fetch job: user=%s preview flushed (pending_vision)", user_id,
        )

        # 3. Vision 분석 — 실패 시 analysis=None 인 채 success 처리
        analyzed_cache = ig_scraper.attach_vision_analysis(preview_cache)

        # 4. 최종 flush (success) — Vision 성공/실패 무관 scope=full 이면 success
        user_profiles.upsert_ig_feed_cache(
            db, user_id=user_id, cache=analyzed_cache, status="success",
        )
        db.commit()
        logger.info(
            "ig_fetch job: user=%s done (analysis=%s)",
            user_id,
            analyzed_cache.analysis is not None,
        )
    except Exception:
        logger.exception("ig_fetch job: unexpected error user=%s", user_id)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass
