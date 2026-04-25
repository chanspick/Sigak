"""PI (Personal Image) 리포트 엔드포인트 — v1 + v2 + v3 (Phase I PI-D).

v1 (unchanged, deprecate 예정):
  GET  /api/v1/pi          현재 해제 상태 + 해제 시 report_data
  POST /api/v1/pi/unlock   50 토큰 차감 + pi_reports upsert (unlocked_at=NOW())

v2 (D5 Phase 3, deprecate 예정):
  GET  /api/v2/pi          동일 계약, user_profiles row 전제
  POST /api/v2/pi/unlock   첫 1회 무료 + 재생성 50 토큰

v3 (Phase I PI-D, 본인 결정 2026-04-25):
  GET  /api/v3/pi/status            상태 조회 (baseline / current_report / 토큰 잔량)
  POST /api/v3/pi/upload            정면 baseline 사진 업로드 (multipart)
  POST /api/v3/pi/preview           무료 preview 생성 (혼합 iii — cover/celeb 풀 + 4 teaser + 3 lock)
  POST /api/v3/pi/unlock            50 토큰 차감 + 풀 PI (vault history_context 풀 load)
  GET  /api/v3/pi/list              version list (Monthly 후속)
  GET  /api/v3/pi/{report_id}       특정 리포트 조회

v3 정책 (CLAUDE.md §3.2 + §10):
  - 가입 30 토큰 + PI 50 토큰 = 부족 20 토큰 추가 결제 (첫 1회 무료 폐기)
  - preview 는 토큰 차감 X (cover + celeb 풀 노출 / 나머지 teaser/lock)
  - unlock 호출 시 vault.verdict_history + best_shot_history + aspiration_history 를
    pi_engine 에 history_context 로 전달 (PI-A 통합 hook)
  - 환불 path: pi_engine 실패 시 차감된 50 토큰 자동 환불

PI 리포트는 유저당 1회 영속 해제. 재설정 시에도 유지.
"""
import inspect
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from services import pi as pi_service
from services import tokens as tokens_service
from services import user_profiles as user_profiles_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pi", tags=["pi"])
router_v2 = APIRouter(prefix="/api/v2/pi", tags=["pi-v2"])
router_v3 = APIRouter(prefix="/api/v3/pi", tags=["pi-v3"])


# ─────────────────────────────────────────────
#  Response schemas (공용)
# ─────────────────────────────────────────────

class PIStatusResponse(BaseModel):
    unlocked: bool
    cost: int
    unlocked_at: Optional[str] = None
    report_data: Optional[dict] = None


class PIUnlockResponse(BaseModel):
    unlocked: bool
    unlocked_at: str
    report_data: dict
    token_balance: int


# ─────────────────────────────────────────────
#  공용 DB helpers
# ─────────────────────────────────────────────

def _select_report(db, user_id: str):
    return db.execute(
        text(
            "SELECT unlocked_at, report_data "
            "FROM pi_reports WHERE user_id = :uid"
        ),
        {"uid": user_id},
    ).first()


def _upsert_report(db, user_id: str, data: dict, now: datetime) -> None:
    db.execute(
        text(
            """
            INSERT INTO pi_reports (user_id, unlocked_at, report_data, created_at, updated_at)
            VALUES (:uid, :now, CAST(:data AS jsonb), :now, :now)
            ON CONFLICT (user_id) DO UPDATE SET
              unlocked_at = EXCLUDED.unlocked_at,
              report_data = EXCLUDED.report_data,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "uid": user_id,
            "now": now,
            "data": json.dumps(data, ensure_ascii=False),
        },
    )


def _debit_tokens_for_unlock(db, user_id: str) -> int:
    """50 토큰 차감. IntegrityError 시 idempotent 재계산.

    Returns balance_after (차감 성공 또는 기존 잔액).
    Raises HTTPException(402) 잔액 부족 시.
    """
    current_balance = tokens_service.get_balance(db, user_id)
    if current_balance < tokens_service.COST_PI_UNLOCK:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {tokens_service.COST_PI_UNLOCK}토큰 필요, "
            f"현재 {current_balance}",
        )

    idempotency_key = f"pi_unlock:{user_id}"
    try:
        return tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=-tokens_service.COST_PI_UNLOCK,
            kind=tokens_service.KIND_CONSUME_PI,
            idempotency_key=idempotency_key,
            reference_id=user_id,
            reference_type="user",
        )
    except IntegrityError:
        db.rollback()
        logger.info("[pi/unlock] idempotent re-unlock user=%s (no charge)", user_id)
        return tokens_service.get_balance(db, user_id)


# ─────────────────────────────────────────────
#  v1 endpoints — unchanged behavior
# ─────────────────────────────────────────────

@router.get("", response_model=PIStatusResponse)
def get_pi(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """PI 해제 상태 조회 (v1)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = _select_report(db, user["id"])
    if not row or row.unlocked_at is None:
        return PIStatusResponse(
            unlocked=False,
            cost=tokens_service.COST_PI_UNLOCK,
        )
    return PIStatusResponse(
        unlocked=True,
        cost=tokens_service.COST_PI_UNLOCK,
        unlocked_at=row.unlocked_at.isoformat() if row.unlocked_at else None,
        report_data=row.report_data or {},
    )


@router.post("/unlock", response_model=PIUnlockResponse)
def unlock_pi(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """50 토큰 차감 + pi_reports.unlocked_at=NOW() (v1 stub)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    existing = _select_report(db, user["id"])
    if existing and existing.unlocked_at is not None:
        return PIUnlockResponse(
            unlocked=True,
            unlocked_at=existing.unlocked_at.isoformat(),
            report_data=existing.report_data or {},
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    balance_after = _debit_tokens_for_unlock(db, user["id"])

    stub = pi_service.build_v1_report_data()
    now = datetime.utcnow()
    _upsert_report(db, user["id"], stub, now)
    db.commit()

    return PIUnlockResponse(
        unlocked=True,
        unlocked_at=now.isoformat(),
        report_data=stub,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  v2 endpoints — user_profile 통합
# ─────────────────────────────────────────────

@router_v2.get("", response_model=PIStatusResponse)
def get_pi_v2(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """v2 해제 상태. GET 은 user_profiles 요구 없음 (해제 여부만 판정).

    Phase I: is_current 리포트 조회. 버전/스냅샷 포함 report_data 반환.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = _select_current_v2(db, user["id"])
    if row is None:
        return PIStatusResponse(
            unlocked=False,
            cost=tokens_service.COST_PI_UNLOCK,
        )
    return PIStatusResponse(
        unlocked=True,
        cost=tokens_service.COST_PI_UNLOCK,
        unlocked_at=row.unlocked_at.isoformat() if row.unlocked_at else None,
        report_data=row.report_data or {},
    )


@router_v2.post("/unlock", response_model=PIUnlockResponse)
def unlock_pi_v2(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """PI 생성 / 재생성 (Phase I).

    정책:
      - 유저 is_current 리포트 없음 → **첫 1회 무료** 생성
      - 유저 is_current 리포트 있음 → 50 토큰 재생성 (force_new_version=True)

    Phase H 완료 전까지 SiaWriter Stub 기반 placeholder copy. concrete 주입 후
    별도 엔드포인트 호출 없이 자동 반영.

    Legacy 호환:
      - 구 placeholder (status='generating' / 'migrated_from_sigak_report') 는
        "is_current 있음" 으로 처리하지 않는다 — 실제 PIReport 데이터 있는
        version 만 "생성됨" 으로 카운트 (_has_real_current_report).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # Vault 선행 — onboarding 완료 여부
    from services.user_data_vault import load_vault
    vault = load_vault(db, user["id"])
    if vault is None:
        raise HTTPException(
            409,
            "시각이 본 나 리포트를 여시려면 온보딩이 먼저 필요합니다.",
        )

    had_real_current = _has_real_current_report(db, user["id"])

    # 재생성 = 토큰 차감. 첫 1회 = 무료.
    balance_after: int
    if had_real_current:
        balance_after = _debit_regenerate_tokens(db, user["id"])
    else:
        balance_after = tokens_service.get_balance(db, user["id"])

    # 엔진 실행
    from services.pi_engine import PIEngineError, generate_pi_report
    try:
        report = generate_pi_report(
            db,
            user_id=user["id"],
            force_new_version=had_real_current,
        )
    except PIEngineError as e:
        logger.exception("PI engine failed: user=%s", user["id"])
        # 재생성 차감했는데 실패하면 환불
        if had_real_current:
            _refund_regenerate_tokens(db, user["id"])
            db.commit()
            balance_after = tokens_service.get_balance(db, user["id"])
        raise HTTPException(500, f"PI 리포트 생성 실패: {e}")

    db.commit()

    import json
    return PIUnlockResponse(
        unlocked=True,
        unlocked_at=report.generated_at.isoformat(),
        report_data=json.loads(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, default=str)
        ),
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  v2 helpers — Phase I
# ─────────────────────────────────────────────

def _select_current_v2(db, user_id: str):
    """is_current=TRUE 리포트 1건 — 마이그레이션 전 스키마 호환 위해 defensive."""
    try:
        return db.execute(
            text(
                "SELECT unlocked_at, report_data "
                "FROM pi_reports "
                "WHERE user_id = :uid AND is_current = TRUE "
                "LIMIT 1"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        # Phase I 마이그레이션 전 — legacy 스키마 (user_id PK) 로 fallback
        logger.debug("pi_reports is_current column missing — falling back to user_id PK read")
        return _select_report(db, user_id)


def _has_real_current_report(db, user_id: str) -> bool:
    """version 1 이상 실 리포트 존재 여부 — legacy placeholder 제외."""
    try:
        row = db.execute(
            text(
                "SELECT report_data FROM pi_reports "
                "WHERE user_id = :uid AND is_current = TRUE LIMIT 1"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        # 마이그레이션 전 — 무료 첫 생성 허용
        return False
    if row is None or not row.report_data:
        return False
    # placeholder / legacy 는 실 리포트 아님
    status = (row.report_data or {}).get("status")
    if status in ("generating", "migrated_from_sigak_report"):
        return False
    # 실 PIReport 는 최소 report_id / version 키 보유
    if "report_id" not in (row.report_data or {}):
        return False
    return True


def _debit_regenerate_tokens(db, user_id: str) -> int:
    """재생성 50 토큰 차감 — 1분 해상도 idempotency."""
    import time
    cost = tokens_service.COST_PI_UNLOCK
    current = tokens_service.get_balance(db, user_id)
    if current < cost:
        raise HTTPException(
            402,
            f"토큰 부족 — 재생성 {cost} 필요, 보유 {current}",
        )
    minute_bucket = int(time.time()) // 60
    key = f"pi_regenerate:{user_id}:{minute_bucket}"
    try:
        return tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_PI,
            idempotency_key=key,
            reference_type="pi_regenerate",
        )
    except IntegrityError:
        db.rollback()
        return tokens_service.get_balance(db, user_id)


def _refund_regenerate_tokens(db, user_id: str) -> None:
    """생성 실패 환불 — 동일 분 bucket 에 대응."""
    minute_bucket = int(time.time()) // 60
    key = f"pi_regenerate:{user_id}:{minute_bucket}:refund"
    try:
        tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=+tokens_service.COST_PI_UNLOCK,
            kind=tokens_service.KIND_REFUND,
            idempotency_key=key,
            reference_type="pi_regenerate_refund",
        )
    except IntegrityError:
        db.rollback()


# ─────────────────────────────────────────────
#  v3 endpoints — Phase I PI-D (본인 결정 2026-04-25)
#
#  설계 요약:
#    - upload : baseline raw → R2 영구 + DB users.pi_baseline_r2_key
#    - preview: pi_engine 호출 → 9 컴포넌트 응답 (혼합 iii visibility, 토큰 차감 X)
#    - unlock : 50 토큰 차감 + vault history_context 풀 load + pi_engine 호출
#               → 9 컴포넌트 풀 응답
#    - 환불 path: pi_engine 실패 시 자동 환불
# ─────────────────────────────────────────────

from schemas.pi_report import (
    PI_V3_PREVIEW_VISIBILITY,
    PI_V3_SECTION_ORDER,
    PI_V3_UNLOCK_COST_TOKENS,
    PIv3Report,
    PIv3Section,
    PIv3Status,
    PIv3UploadResponse,
    PIv3VersionEntry,
    PIv3VersionsList,
)


# ─────────────────────────────────────────────
#  v3 helpers
# ─────────────────────────────────────────────

def _fetch_baseline_status(db, user_id: str) -> tuple[Optional[str], Optional[datetime], bool]:
    """users.pi_baseline_r2_key + pi_baseline_uploaded_at + pi_pending 조회.

    컬럼 미존재 시 (alembic 미적용) (None, None, False) 반환.
    """
    try:
        row = db.execute(
            text(
                "SELECT pi_baseline_r2_key, pi_baseline_uploaded_at, "
                "       COALESCE(pi_pending, FALSE) AS pi_pending "
                "FROM users WHERE id = :uid"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        logger.debug("users.pi_baseline_* columns absent for user=%s", user_id)
        return (None, None, False)

    if row is None:
        return (None, None, False)

    return (
        getattr(row, "pi_baseline_r2_key", None),
        getattr(row, "pi_baseline_uploaded_at", None),
        bool(getattr(row, "pi_pending", False)),
    )


def _persist_baseline_metadata(
    db,
    user_id: str,
    r2_key: str,
    now: datetime,
) -> None:
    """users.pi_baseline_r2_key + pi_baseline_uploaded_at + pi_pending=TRUE update.

    alembic 컬럼 없을 시 swallow + log (LIVE probe 단계에서 정상화).
    """
    try:
        db.execute(
            text(
                "UPDATE users SET "
                "  pi_baseline_r2_key = :key, "
                "  pi_baseline_uploaded_at = :ts, "
                "  pi_pending = TRUE "
                "WHERE id = :uid"
            ),
            {"key": r2_key, "ts": now, "uid": user_id},
        )
    except Exception:
        logger.warning(
            "pi_baseline metadata update failed (alembic 미적용?) user=%s", user_id,
        )


def _build_history_context(vault) -> dict:
    """vault → pi_engine history_context dict (긴급 보강 2026-04-25).

    PI-A 가 받지 않으면 inspect.signature 로 무시 (PI-D 가 안전 흘리기).
    """
    try:
        return {
            "verdict_history": [
                v.model_dump(mode="json") for v in (vault.verdict_history or [])
            ],
            "best_shot_history": [
                b.model_dump(mode="json") for b in (vault.best_shot_history or [])
            ],
            "aspiration_history": [
                a.model_dump(mode="json") for a in (vault.aspiration_history or [])
            ],
        }
    except Exception:
        logger.debug("history_context build skipped — vault history shape unknown")
        return {
            "verdict_history": [],
            "best_shot_history": [],
            "aspiration_history": [],
        }


def _run_pi_b_pipeline(
    *,
    baseline_r2_key: str,
    gender: Optional[str],
) -> tuple[Optional[dict], Optional[dict], list, list]:
    """PI-B 호출 (face features + 좌표 + anchor matching).

    PI-B 모듈은 별도 인스턴스가 작성. 모듈 미존재 시 빈 결과 fallback —
    PI-A v1 이 None / [] 입력을 받아도 적절히 처리하도록 설계됨.

    Returns:
      (face_features, coord_3axis, matched_celebs, matched_types)
    """
    try:
        from services.pi_b_engine import compute_face_and_anchors  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("pi_b_engine not yet available — PI-B step skipped")
        return (None, None, [], [])

    try:
        result = compute_face_and_anchors(
            baseline_r2_key=baseline_r2_key,
            gender=gender,
        )
    except Exception:
        logger.exception("PI-B pipeline failed — returning empty")
        return (None, None, [], [])

    return (
        getattr(result, "face_features", None),
        getattr(result, "coord_3axis", None),
        list(getattr(result, "matched_celebs", None) or []),
        list(getattr(result, "matched_types", None) or []),
    )


def _run_pi_c_pipeline(
    *,
    coord_3axis: Optional[dict],
    gender: Optional[str],
    face_features: Optional[dict],
) -> tuple[list, list]:
    """PI-C 호출 (KB trend matching + methodology reasons).

    Returns:
      (matched_trends, methodology_reasons)
    """
    try:
        from services.pi_c_engine import compute_trend_methodology  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("pi_c_engine not yet available — PI-C step skipped")
        return ([], [])

    try:
        result = compute_trend_methodology(
            coord_3axis=coord_3axis,
            gender=gender,
            face_features=face_features,
        )
    except Exception:
        logger.exception("PI-C pipeline failed — returning empty")
        return ([], [])

    return (
        list(getattr(result, "matched_trends", None) or []),
        list(getattr(result, "methodology_reasons", None) or []),
    )


def _call_pi_engine_safely(
    db,
    *,
    user_id: str,
    baseline_r2_key: Optional[str],
    vault,
    history_context: dict,
    force_new_version: bool,
):
    """PI-A v1 시그니처 호출 (긴급 보강 2026-04-25).

    흐름:
      1. PI-B 호출 (face + coord + anchors)
      2. PI-C 호출 (trend + methodology)
      3. PI-A v1 호출 — 위 결과 + baseline_r2_key + force_new_version 전달

    Fallback:
      PI-A v1 (generate_pi_report_v1) 미존재 시 기존 generate_pi_report 호출.
      history_context kwarg 받지 않으면 무시.
    """
    gender = (
        vault.basic_info.gender if vault and getattr(vault, "basic_info", None) else None
    )

    face_features, coord_3axis, matched_celebs, matched_types = _run_pi_b_pipeline(
        baseline_r2_key=baseline_r2_key or "", gender=gender,
    )
    matched_trends, methodology_reasons = _run_pi_c_pipeline(
        coord_3axis=coord_3axis, gender=gender, face_features=face_features,
    )

    # PI-A v1 우선 시도
    try:
        from services.pi_engine import generate_pi_report_v1  # type: ignore[attr-defined]
        return generate_pi_report_v1(
            db,
            user_id=user_id,
            baseline_photo_r2_key=baseline_r2_key,
            face_features=face_features,
            coord_3axis=coord_3axis,
            matched_celebs=matched_celebs,
            matched_types=matched_types,
            matched_trends=matched_trends,
            methodology_reasons=methodology_reasons,
            force_new_version=force_new_version,
        )
    except ImportError:
        logger.debug("generate_pi_report_v1 not yet available — fallback to legacy engine")

    # Fallback — 기존 generate_pi_report (history_context 흘림)
    from services.pi_engine import generate_pi_report
    try:
        sig = inspect.signature(generate_pi_report)
        kwargs = {"user_id": user_id, "force_new_version": force_new_version}
        if "history_context" in sig.parameters:
            kwargs["history_context"] = history_context
        return generate_pi_report(db, **kwargs)
    except TypeError:
        logger.debug("generate_pi_report signature inspection failed — bare call")
        return generate_pi_report(
            db, user_id=user_id, force_new_version=force_new_version,
        )


def _photo_insights_to_section_content(photos: list, category: str) -> dict:
    """PI-A PIReport.public_photos / locked_photos 를 v3 section.content 로 변환.

    PI-A 가 9 컴포넌트 schema 정착 전까지의 호환 레이어. PI-A/PI-C 통합 시점에
    section_id 별 content shape 가 정해지면 이 함수 재작성.
    """
    if not photos:
        return {"category": category, "items": []}
    items: list[dict] = []
    for p in photos:
        try:
            items.append({
                "photo_id": getattr(p, "photo_id", None),
                "stored_url": getattr(p, "stored_url", None),
                "category": getattr(p, "category", None),
                "sia_comment": getattr(p, "sia_comment", None),
                "rank": getattr(p, "rank", None),
                "associated_trend_id": getattr(p, "associated_trend_id", None),
            })
        except Exception:
            continue
    return {"category": category, "items": items}


def _compose_v3_sections_from_v1_components(
    v1_components: dict, *, mode: str,
) -> list[PIv3Section]:
    """PI-A v1 9 컴포넌트 dict → v3 PIv3Section list 직접 변환.

    PI-A 의 _assemble_9_components 결과 dict 형태:
      {
        "cover":              {"weight": "vault", "mode": "preview", "content": {...}},
        "celeb_reference":    {"weight": "raw", "mode": "preview", "content": {...}},
        "face_structure":     {"weight": "raw", "mode": "teaser", "content": {...}},
        ...
      }

    각 컴포넌트의 .content 를 PIv3Section.content 로 직접 매핑.
    visibility 는 mode (preview/full) + PI_V3_PREVIEW_VISIBILITY 정책.
    """
    sections: list[PIv3Section] = []
    for sid in PI_V3_SECTION_ORDER:
        component = v1_components.get(sid)
        if isinstance(component, dict):
            content = component.get("content") or {}
            if not isinstance(content, dict):
                content = {}
        else:
            content = {}
        visibility = (
            "full" if mode == "full"
            else PI_V3_PREVIEW_VISIBILITY.get(sid, "locked")
        )
        sections.append(PIv3Section(
            section_id=sid,                    # type: ignore[arg-type]
            visibility=visibility,             # type: ignore[arg-type]
            content=content,
        ))
    return sections


def _compose_v3_sections(report, *, mode: str) -> list[PIv3Section]:
    """PIReport → 9 PIv3Section list.

    mode: "preview" | "full"
      preview: PI_V3_PREVIEW_VISIBILITY 적용
      full   : 모든 section visibility = "full"

    분기 (2026-04-25 PI-A v1 통합):
      (a) report._pi_v1_components 있음 → 직접 9 컴포넌트 dict 사용 (정합)
      (b) 없음 → 옛 25-photo 카테고리 모델 fallback (legacy 호환)
    """
    # PI-A v1 components 우선 — 새로 생성된 PIReport 는 항상 이 분기
    v1_components = getattr(report, "_pi_v1_components", None)
    if isinstance(v1_components, dict) and v1_components:
        return _compose_v3_sections_from_v1_components(
            v1_components, mode=mode,
        )

    # Legacy fallback — DB 에서 load 한 옛 PIReport (25-photo 카테고리 모델)
    by_category: dict[str, list] = {}
    for p in (getattr(report, "public_photos", None) or []):
        cat = getattr(p, "category", None) or "signature"
        by_category.setdefault(cat, []).append(p)
    for p in (getattr(report, "locked_photos", None) or []):
        cat = getattr(p, "category", None) or "detail_analysis"
        by_category.setdefault(cat, []).append(p)

    overall = getattr(report, "sia_overall_message", "") or ""
    boundary = getattr(report, "boundary_message", "") or ""
    user_summary = getattr(report, "user_summary", "") or ""
    needs_statement = getattr(report, "needs_statement", "") or ""
    matched_trend_ids = list(getattr(report, "matched_trend_ids", None) or [])
    matched_methodology_ids = list(
        getattr(report, "matched_methodology_ids", None) or []
    )
    matched_reference_ids = list(
        getattr(report, "matched_reference_ids", None) or []
    )
    snapshot = getattr(report, "user_taste_profile_snapshot", None) or {}
    user_phrases = list(getattr(report, "user_original_phrases", None) or [])

    section_contents: dict[str, dict] = {
        "cover": {
            "user_summary": user_summary,
            "needs_statement": needs_statement,
            "user_original_phrases": user_phrases,
            "sia_overall_message": overall,
            "photos": _photo_insights_to_section_content(
                by_category.get("signature", []), "signature",
            )["items"],
        },
        "celeb_reference": _photo_insights_to_section_content(
            by_category.get("trend_match", []), "trend_match",
        ),
        "face_structure": _photo_insights_to_section_content(
            by_category.get("detail_analysis", []), "detail_analysis",
        ),
        "type_reference": _photo_insights_to_section_content(
            by_category.get("style_element", []), "style_element",
        ),
        "gap_analysis": _photo_insights_to_section_content(
            by_category.get("aspiration_gap", []), "aspiration_gap",
        ),
        "skin_analysis": _photo_insights_to_section_content(
            by_category.get("weaker_angle", []), "weaker_angle",
        ),
        "coordinate_map": {
            "current_position": snapshot.get("current_position"),
            "aspiration_vector": snapshot.get("aspiration_vector"),
            "trajectory": snapshot.get("trajectory") or [],
        },
        "hair_recommendation": {
            "matched_trend_ids": matched_trend_ids,
            "matched_methodology_ids": matched_methodology_ids,
            "matched_reference_ids": matched_reference_ids,
            "photos": _photo_insights_to_section_content(
                by_category.get("methodology", []), "methodology",
            )["items"],
        },
        "action_plan": {
            "boundary_message": boundary,
            "matched_trend_ids": matched_trend_ids,
            "matched_methodology_ids": matched_methodology_ids,
        },
    }

    sections: list[PIv3Section] = []
    for sid in PI_V3_SECTION_ORDER:
        visibility = "full" if mode == "full" else PI_V3_PREVIEW_VISIBILITY.get(sid, "locked")
        sections.append(PIv3Section(
            section_id=sid,                       # type: ignore[arg-type]
            visibility=visibility,                # type: ignore[arg-type]
            content=section_contents.get(sid, {}),
        ))
    return sections


def _build_v3_response(
    report,
    *,
    mode: str,
    token_balance: Optional[int] = None,
) -> PIv3Report:
    """PIReport → PIv3Report wrapper. mode = "preview" | "full"."""
    is_preview = (mode != "full")
    needs = max(0, PI_V3_UNLOCK_COST_TOKENS - (token_balance or 0)) if is_preview else None

    return PIv3Report(
        report_id=getattr(report, "report_id", "") or "",
        version=int(getattr(report, "version", 1) or 1),
        is_current=bool(getattr(report, "is_current", True)),
        generated_at=(
            getattr(report, "generated_at", datetime.now(timezone.utc)).isoformat()
        ),
        is_preview=is_preview,
        sections=_compose_v3_sections(report, mode=mode),
        unlock_cost_tokens=PI_V3_UNLOCK_COST_TOKENS,
        token_balance=token_balance,
        needs_payment_tokens=needs,
    )


def _debit_v3_unlock(db, user_id: str) -> int:
    """v3 unlock 50 토큰 차감 — 1분 idempotency bucket. 부족 시 402."""
    cost = PI_V3_UNLOCK_COST_TOKENS
    current = tokens_service.get_balance(db, user_id)
    if current < cost:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. PI 50 필요, 보유 {current}, 부족 {cost - current}",
        )
    minute_bucket = int(time.time()) // 60
    key = f"pi_v3_unlock:{user_id}:{minute_bucket}"
    try:
        return tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_PI,
            idempotency_key=key,
            reference_type="pi_v3_unlock",
        )
    except IntegrityError:
        db.rollback()
        return tokens_service.get_balance(db, user_id)


def _refund_v3_unlock(db, user_id: str) -> None:
    """v3 unlock 환불 — pi_engine 실패 시 즉시 환원."""
    minute_bucket = int(time.time()) // 60
    key = f"pi_v3_unlock:{user_id}:{minute_bucket}:refund"
    try:
        tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=+PI_V3_UNLOCK_COST_TOKENS,
            kind=tokens_service.KIND_REFUND,
            idempotency_key=key,
            reference_type="pi_v3_unlock_refund",
        )
    except IntegrityError:
        db.rollback()


def _clear_pi_pending_flag(db, user_id: str) -> None:
    """unlock 성공 시 users.pi_pending = FALSE.

    alembic 컬럼 없으면 swallow.
    """
    try:
        db.execute(
            text("UPDATE users SET pi_pending = FALSE WHERE id = :uid"),
            {"uid": user_id},
        )
    except Exception:
        logger.debug("pi_pending flag update skipped for user=%s", user_id)


# ─────────────────────────────────────────────
#  v3 endpoints
# ─────────────────────────────────────────────

@router_v3.get("/status", response_model=PIv3Status)
def get_pi_v3_status(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """PI v3 상태 조회 — baseline 유무 + current report + 토큰 잔량."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]
    baseline_key, baseline_at, pi_pending = _fetch_baseline_status(db, user_id)
    has_baseline = bool(baseline_key)

    # current report
    current_row = _select_current_v2(db, user_id)
    has_current = current_row is not None
    current_report_id = None
    current_version = None
    unlocked_at = None
    if has_current and current_row.report_data:
        current_report_id = current_row.report_data.get("report_id")
        current_version = current_row.report_data.get("version")
        unlocked_at = (
            current_row.unlocked_at.isoformat() if current_row.unlocked_at else None
        )

    balance = tokens_service.get_balance(db, user_id)
    needs = max(0, PI_V3_UNLOCK_COST_TOKENS - balance)

    return PIv3Status(
        has_baseline=has_baseline,
        baseline_uploaded_at=baseline_at.isoformat() if baseline_at else None,
        has_current_report=has_current,
        current_report_id=current_report_id,
        current_version=current_version,
        unlocked_at=unlocked_at,
        unlock_cost_tokens=PI_V3_UNLOCK_COST_TOKENS,
        token_balance=balance,
        needs_payment_tokens=needs,
        pi_pending=pi_pending,
    )


@router_v3.post("/upload", response_model=PIv3UploadResponse)
async def upload_pi_v3_baseline(
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """정면 baseline 사진 업로드 — R2 영구 저장 + users.pi_baseline_r2_key.

    화장 검증은 soft warning (Sonnet Vision 호출 비용 회피 위해 STEP 1 단계는 생략 —
    pi_engine preview 시점에 통합 검증).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]
    contents = await image.read()
    if not contents:
        raise HTTPException(400, "비어있는 파일입니다")

    # 파일 형식 추론 (jpg / png 만 허용)
    content_type = (image.content_type or "").lower()
    if content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        raise HTTPException(400, "이미지 형식은 jpg/png/webp 만 지원합니다")
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else (
        "png" if "png" in content_type else "webp"
    )

    # R2 영구 저장
    from services import r2_client
    now = datetime.now(timezone.utc)
    photo_id = uuid.uuid4().hex[:16]
    r2_key = r2_client.user_photo_key(
        user_id, f"pi_baseline/{int(now.timestamp())}_{photo_id}.{ext}",
    )
    try:
        r2_client.put_bytes(r2_key, contents, content_type=content_type)
    except Exception as e:
        logger.exception("PI baseline R2 put failed user=%s", user_id)
        raise HTTPException(500, f"baseline 저장 실패: {e}")

    # DB 메타데이터 update + 트랜잭션 커밋
    _persist_baseline_metadata(db, user_id, r2_key, now)
    db.commit()

    return PIv3UploadResponse(
        uploaded=True,
        baseline_r2_key=r2_key,
        uploaded_at=now.isoformat(),
        makeup_warning=None,   # Sonnet Vision soft warning 은 preview 단계에 위임
    )


@router_v3.post("/preview", response_model=PIv3Report)
def preview_pi_v3(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """무료 preview 생성 — 토큰 차감 X. 혼합 iii visibility (cover/celeb 풀, 4 teaser, 3 lock).

    baseline 사진 미업로드 시 409. vault 미존재 시 (온보딩 미완) 409.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]

    # baseline 확인 — 정면 사진 없으면 preview 불가
    baseline_key, _, _ = _fetch_baseline_status(db, user_id)
    if not baseline_key:
        raise HTTPException(
            409,
            "정면 사진이 필요해요. 먼저 사진을 한 장 보여주세요.",
        )

    # vault 확인
    from services.user_data_vault import load_vault
    vault = load_vault(db, user_id)
    if vault is None:
        raise HTTPException(
            409,
            "시각이 본 나 리포트를 여시려면 온보딩이 먼저 필요합니다.",
        )

    history_context = _build_history_context(vault)

    # pi_engine 호출 — preview 도 풀 PI 생성 (visibility 만 가공)
    # force_new_version=False : is_current 있으면 재사용, 없으면 신규
    from services.pi_engine import PIEngineError
    try:
        report = _call_pi_engine_safely(
            db,
            user_id=user_id,
            baseline_r2_key=baseline_key,
            vault=vault,
            history_context=history_context,
            force_new_version=False,
        )
    except PIEngineError as e:
        logger.exception("PI v3 preview engine failed user=%s", user_id)
        raise HTTPException(500, f"PI preview 생성 실패: {e}")

    db.commit()

    balance = tokens_service.get_balance(db, user_id)
    return _build_v3_response(report, mode="preview", token_balance=balance)


@router_v3.post("/unlock", response_model=PIv3Report)
def unlock_pi_v3(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """50 토큰 차감 + 풀 PI 생성.

    긴급 보강 (2026-04-25):
      vault 풀 load → verdict_history + best_shot_history + aspiration_history 를
      pi_engine 에 history_context 로 흘림 (PI-A 통합 hook).
    환불 path:
      pi_engine 실패 시 차감된 50 토큰 즉시 환원.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]

    # baseline / vault 선결 — preview 와 동일 가드
    baseline_key, _, _ = _fetch_baseline_status(db, user_id)
    if not baseline_key:
        raise HTTPException(
            409,
            "정면 사진이 필요해요. 먼저 사진을 한 장 보여주세요.",
        )
    from services.user_data_vault import load_vault
    vault = load_vault(db, user_id)
    if vault is None:
        raise HTTPException(
            409,
            "시각이 본 나 리포트를 여시려면 온보딩이 먼저 필요합니다.",
        )

    # 토큰 차감 (1분 idempotency)
    balance_after = _debit_v3_unlock(db, user_id)

    # vault history_context 풀 build (긴급 보강 1)
    history_context = _build_history_context(vault)

    # pi_engine 호출 — force_new_version=True 로 매 unlock 시 신 version
    # 긴급 보강 2: PI-A v1 시그니처 (baseline_r2_key + PI-B/PI-C 결과)
    from services.pi_engine import PIEngineError
    try:
        report = _call_pi_engine_safely(
            db,
            user_id=user_id,
            baseline_r2_key=baseline_key,
            vault=vault,
            history_context=history_context,
            force_new_version=True,
        )
    except PIEngineError as e:
        logger.exception("PI v3 unlock engine failed user=%s", user_id)
        # 환불
        _refund_v3_unlock(db, user_id)
        db.commit()
        raise HTTPException(500, f"PI 생성 실패: {e}")
    except Exception as e:
        # PI-A v1 / PI-B / PI-C 의 비-PIEngineError 예외도 환불 + 500
        logger.exception("PI v3 unlock unexpected failure user=%s", user_id)
        _refund_v3_unlock(db, user_id)
        db.commit()
        raise HTTPException(500, f"PI 생성 실패: {e}")

    # pending flag clear
    _clear_pi_pending_flag(db, user_id)
    db.commit()

    return _build_v3_response(report, mode="full", token_balance=balance_after)


@router_v3.get("/list", response_model=PIv3VersionsList)
def list_pi_v3_versions(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """version history list — Monthly 후속 (지금 시점은 PI 1 버전)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]
    try:
        rows = db.execute(
            text(
                "SELECT report_id, version, is_current, unlocked_at, report_data "
                "FROM pi_reports WHERE user_id = :uid "
                "ORDER BY version DESC, created_at DESC LIMIT 20"
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        logger.debug("pi_reports list fetch skipped — migration pending?")
        return PIv3VersionsList(versions=[], current_report_id=None)

    versions: list[PIv3VersionEntry] = []
    current_id: Optional[str] = None
    for row in rows or []:
        try:
            rid = str(getattr(row, "report_id", "") or "")
            ver = int(getattr(row, "version", 1) or 1)
            is_curr = bool(getattr(row, "is_current", False))
            data = getattr(row, "report_data", None) or {}
            generated_at = getattr(row, "unlocked_at", None)
            iso_at = (
                generated_at.isoformat() if generated_at else
                (data.get("generated_at") or "")
            )
            # legacy placeholder 는 list 에서 제외
            if isinstance(data, dict) and data.get("status") in (
                "generating", "migrated_from_sigak_report",
            ):
                continue
            versions.append(PIv3VersionEntry(
                report_id=rid,
                version=ver,
                is_current=is_curr,
                generated_at=iso_at,
                is_preview=False,
            ))
            if is_curr:
                current_id = rid
        except Exception:
            logger.debug("pi_reports list row parse failed user=%s", user_id)
            continue
    return PIv3VersionsList(versions=versions, current_report_id=current_id)


@router_v3.get("/{report_id}", response_model=PIv3Report)
def get_pi_v3_report(
    report_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """특정 PI version 조회. 권한 검증 — user_id 일치 필수."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_id = user["id"]
    try:
        row = db.execute(
            text(
                "SELECT report_id, user_id, version, is_current, unlocked_at, "
                "       report_data, created_at "
                "FROM pi_reports WHERE report_id = :rid LIMIT 1"
            ),
            {"rid": report_id},
        ).first()
    except Exception:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")

    if row is None:
        raise HTTPException(404, "리포트를 찾을 수 없습니다")
    if str(getattr(row, "user_id", None)) != user_id:
        raise HTTPException(403, "접근 권한이 없습니다")

    data = getattr(row, "report_data", None) or {}
    if not isinstance(data, dict):
        raise HTTPException(500, "리포트 데이터 손상")
    if data.get("status") in ("generating", "migrated_from_sigak_report"):
        raise HTTPException(404, "리포트가 아직 생성되지 않았습니다")

    # PIReport 재조립 (PIv3Report 생성용)
    from schemas.pi_report import PIReport
    try:
        report = PIReport.model_validate(data)
    except Exception:
        logger.exception("PIReport parse failed report_id=%s", report_id)
        raise HTTPException(500, "리포트 파싱 실패")

    # PI v1 components 복원 — JSONB 안 components dict 를 attribute attach.
    # _compose_v3_sections 가 우선 사용해서 9 컴포넌트 풀 노출.
    # _load_current_report 와 동일 패턴 (pi_engine.py 정합).
    components = data.get("components")
    if isinstance(components, dict) and components:
        setattr(report, "_pi_v1_components", components)

    balance = tokens_service.get_balance(db, user_id)
    return _build_v3_response(report, mode="full", token_balance=balance)
