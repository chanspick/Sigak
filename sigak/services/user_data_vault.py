"""UserDataVault — 유저 전수 데이터 중앙 집계 (Phase G5).

CLAUDE.md §4.2 정의. 여러 테이블에 흩어진 유저 데이터를 한 객체로 집계.

MVP 범위 (Phase G skeleton):
- load_vault(db, user_id) — user_profiles / ig_feed_cache / conversations 경량 조합
- get_user_taste_profile() — compute UserTasteProfile (coordinate + strength)

Phase J/K/M 진행 시 확장:
- aspiration_history (Phase J)
- best_shot_history (Phase K)
- monthly_reports (Phase M)
- pi_versions (Phase I)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from pydantic import BaseModel, ConfigDict, Field

from schemas.user_history import (
    AspirationHistoryEntry,
    BestShotHistoryEntry,
    ConversationHistoryEntry,
    HistoryIgSnapshot,
    PiHistoryEntry,
    UserHistory,
    VerdictHistoryEntry,
)
from schemas.user_taste import (
    ConversationSignals,
    PhotoReference,
    TrajectoryPoint,
    UserTasteProfile,
    compute_strength_score,
)
from services.coordinate_system import (
    GapVector,
    VisualCoordinate,
    neutral_coordinate,
)
from services.user_profiles import get_profile


logger = logging.getLogger(__name__)


class UserBasicInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    ig_handle: Optional[str] = None
    name: Optional[str] = None


class PiVersionEntry(BaseModel):
    """pi_reports row 경량 요약 — CLAUDE.md §4.2 pi_versions list 항목."""
    model_config = ConfigDict(extra="ignore")
    report_id: str
    version: int = 1
    is_current: bool = False
    created_at: Optional[datetime] = None
    unlocked_at: Optional[datetime] = None


class MonthlyReportEntry(BaseModel):
    """monthly_reports row 경량 요약 — CLAUDE.md §4.2 monthly_reports list 항목."""
    model_config = ConfigDict(extra="ignore")
    report_id: str
    year_month: str
    status: str
    scheduled_for: Optional[datetime] = None
    generated_at: Optional[datetime] = None


class UserDataVault(BaseModel):
    """유저 데이터 중앙 집계. 읽기 전용 스냅샷.

    MVP 필드:
      basic_info       — users + user_profiles 조합
      ig_feed_cache    — user_profiles.ig_feed_cache (IgFeedAnalysis 포함)
      structured_fields — user_profiles.structured_fields (Sia 대화 결과)
      conversation_count — 완료된 Sia 세션 수

    확장 예약 필드 (Phase I/J/K/M 진행 시 populate):
      aspiration_count  — 추구미 분석 수행 횟수
      best_shot_count   — Best Shot 수행 횟수
      pi_version_count  — PI 리포트 생성 횟수
      monthly_report_count — 이달의 시각 수행 횟수
    """
    model_config = ConfigDict(extra="ignore")

    basic_info: UserBasicInfo
    ig_feed_cache: Optional[dict] = None
    structured_fields: dict[str, Any] = Field(default_factory=dict)
    conversation_count: int = 0

    aspiration_count: int = 0
    best_shot_count: int = 0
    pi_version_count: int = 0
    monthly_report_count: int = 0

    # CLAUDE.md §4.2 spec 이행 — users.user_history JSONB hydrated view.
    # STEP 4 hook 이 여기에 append 하고, vault 는 읽기 전용으로 노출.
    user_history: UserHistory = Field(default_factory=UserHistory)

    # 최신 aspiration 의 GapVector — UserTasteProfile.aspiration_vector 연결용.
    # load_vault 에서 aspiration_analyses.result_data 에서 파싱.
    latest_aspiration_gap: Optional[GapVector] = None

    # CLAUDE.md §4.2 pi_versions / monthly_reports 리스트 — 테이블 조회 결과.
    # Phase I (PI 엔진) / Phase M (이달의 시각) 이 정식 구현되기 전에도
    # "있는 row 들" 을 vault 가 노출해서 UI 분기 가능하게 함.
    pi_versions: list[PiVersionEntry] = Field(default_factory=list)
    monthly_reports: list[MonthlyReportEntry] = Field(default_factory=list)

    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ─────────────────────────────────────────────
    #  History list access — CLAUDE.md §4.2 spec shapes
    # ─────────────────────────────────────────────

    @property
    def feed_snapshots(self) -> list[HistoryIgSnapshot]:
        """conversations[].ig_snapshot 을 평탄화 — 시계열 IG 피드 히스토리."""
        out: list[HistoryIgSnapshot] = []
        for c in self.user_history.conversations:
            if c.ig_snapshot is not None:
                out.append(c.ig_snapshot)
        return out

    @property
    def aspiration_history(self) -> list[AspirationHistoryEntry]:
        return list(self.user_history.aspiration_analyses)

    @property
    def best_shot_history(self) -> list[BestShotHistoryEntry]:
        return list(self.user_history.best_shot_sessions)

    @property
    def verdict_history(self) -> list[VerdictHistoryEntry]:
        return list(self.user_history.verdict_sessions)

    @property
    def conversation_history(self) -> list[ConversationHistoryEntry]:
        return list(self.user_history.conversations)

    @property
    def pi_history(self) -> list[PiHistoryEntry]:
        """Phase I — PI 결과 narrative summaries (Backward echo source)."""
        return list(self.user_history.pi_history)

    # ─────────────────────────────────────────────
    #  UserTasteProfile composition
    # ─────────────────────────────────────────────

    def get_user_taste_profile(self) -> UserTasteProfile:
        """MVP 구현 — IG Vision + structured_fields 기반 경량 UserTasteProfile.

        Phase I 이후 PhotoReference / trajectory / aspiration_vector 채움.
        """
        signals = self._compose_conversation_signals()
        position = self._compose_current_position()
        evidence = self._compose_preference_evidence()
        phrases = self._compose_user_original_phrases()

        filled_field_count = sum(
            1 for v in (
                signals.body_shape,
                signals.current_concerns,
                signals.specific_context,
                signals.trial_history,
            ) if v
        )
        # desired_image_keywords 도 하나의 필드로 취급
        if signals.desired_image_keywords:
            filled_field_count += 1

        strength = compute_strength_score(
            has_ig_analysis=bool(
                self.ig_feed_cache
                and self.ig_feed_cache.get("analysis")
            ),
            conversation_field_count=filled_field_count,
            aspiration_count=self.aspiration_count,
            best_shot_count=self.best_shot_count,
            monthly_report_count=self.monthly_report_count,
        )

        # Phase I — Backward echo: 최신 PI 결과를 latest_pi 로 carry
        # → sia_writer._render_taste_profile_slim 에서 dump → 4 기능 모두 자동 echo
        latest_pi: Optional[PiHistoryEntry] = None
        pi_list = self.user_history.pi_history
        if pi_list:
            latest_pi = pi_list[0]

        return UserTasteProfile(
            user_id=self.basic_info.user_id,
            snapshot_at=self.snapshot_at,
            current_position=position,
            aspiration_vector=self.latest_aspiration_gap,
            preference_evidence=evidence,
            conversation_signals=signals,
            trajectory=self._compose_trajectory(strength),
            user_original_phrases=phrases,
            latest_pi=latest_pi,
            strength_score=strength,
        )

    def _compose_trajectory(self, current_strength: float) -> list[TrajectoryPoint]:
        """user_history.trajectory_events → TrajectoryPoint 리스트.

        append_history() 가 4 기능 진입 시 자동 누적. 좌표 산출 가능 시점만
        coordinate 채워짐 (현재는 aspiration 만). score_at_time 은 기록 시점에
        산출 불가하므로 vault 조립 시 가장 최근 이벤트에 한해 현재 strength 로
        fallback.
        """
        events = getattr(self.user_history, "trajectory_events", None) or []
        if not events:
            return []

        out: list[TrajectoryPoint] = []
        for idx, ev in enumerate(events):
            if ev is None:
                continue
            try:
                coord: Optional[VisualCoordinate] = None
                snap = getattr(ev, "coordinate_snapshot", None)
                if isinstance(snap, dict):
                    try:
                        coord = VisualCoordinate(
                            shape=float(snap.get("shape", 0.5)),
                            volume=float(snap.get("volume", 0.5)),
                            age=float(snap.get("age", 0.5)),
                        )
                    except (TypeError, ValueError):
                        coord = None
                # 가장 최신 이벤트(idx=0) 만 현재 strength fallback —
                # 과거 이벤트는 당시 strength 알 수 없음.
                score = ev.score_at_time
                if score is None and idx == 0:
                    score = current_strength
                out.append(TrajectoryPoint(
                    captured_at=ev.captured_at,
                    coordinate=coord,
                    source=ev.event_type,
                    reference_id=ev.reference_id,
                    score_at_time=score,
                ))
            except Exception:
                logger.debug("trajectory event parse failed idx=%d", idx)
                continue
        return out

    # ─────────────────────────────────────────────
    #  Internal composers — structured_fields 에서 추출
    # ─────────────────────────────────────────────

    def _compose_conversation_signals(self) -> ConversationSignals:
        sf = self.structured_fields or {}
        # CLAUDE.md §6.10 JSON 스키마 필드명 반영.
        desired_raw = sf.get("desired_image") or sf.get("desired_image_keywords") or []
        if isinstance(desired_raw, str):
            keywords = [desired_raw] if desired_raw else []
        elif isinstance(desired_raw, list):
            keywords = [k for k in desired_raw if isinstance(k, str) and k.strip()]
        else:
            keywords = []

        return ConversationSignals(
            body_shape=_str_or_none(sf.get("body_shape")),
            current_concerns=_str_or_none(sf.get("current_concerns")),
            specific_context=_str_or_none(sf.get("specific_context")),
            trial_history=_str_or_none(sf.get("trial_history")),
            desired_image_keywords=keywords,
            agreement_count=int(sf.get("agreement_count") or 0),
            pushback_count=int(sf.get("pushback_count") or 0),
        )

    def _compose_current_position(self) -> Optional[VisualCoordinate]:
        """structured_fields.coordinate 가 있으면 사용, 없으면 None.

        Phase H 에서 Haiku 가 대화 중 매 메시지마다 shape/volume/age delta 산출
        → structured_fields["coordinate"] = {"shape": .., "volume": .., "age": ..}
        저장 예정. 현재 Phase A-F 는 coordinate 미산출이라 대부분 None.
        """
        sf = self.structured_fields or {}
        coord_raw = sf.get("coordinate") or sf.get("current_position")
        if not isinstance(coord_raw, dict):
            return None
        try:
            return VisualCoordinate(
                shape=float(coord_raw.get("shape", 0.5)),
                volume=float(coord_raw.get("volume", 0.5)),
                age=float(coord_raw.get("age", 0.5)),
            )
        except (TypeError, ValueError):
            return None

    def _compose_preference_evidence(self) -> list[PhotoReference]:
        """현 vault 상태에서 확보 가능한 사진 레퍼런스.

        MVP 소스:
          1. ig_feed_cache.latest_posts (IG 피드 최신)
          2. user_history.best_shot_sessions[*].selected (Best Shot 선별 A컷)

        R2 업로드 완료된 URL 우선 (latest_posts 는 STEP 2 후 R2 URL 로 교체됨,
        Best Shot selected 는 저장 시점부터 R2).
        """
        refs: list[PhotoReference] = []

        # 1. IG feed
        if self.ig_feed_cache:
            posts = self.ig_feed_cache.get("latest_posts") or []
            for p in posts[:10]:
                url = p.get("display_url") if isinstance(p, dict) else None
                if not url:
                    continue
                refs.append(PhotoReference(
                    photo_id=_photo_id_from_caption(p),
                    stored_url=url,
                    source="ig_feed",
                    captured_at=_parse_iso(p.get("timestamp")),
                    sia_comment=None,
                    coordinate=None,
                ))

        # 2. Best Shot selected — 최신 세션부터 5장까지
        for bs_idx, session in enumerate(self.user_history.best_shot_sessions[:1]):
            for sel_idx, sel in enumerate(session.selected[:5]):
                refs.append(PhotoReference(
                    photo_id=f"bs_{session.session_id}_{sel_idx}",
                    stored_url=sel.r2_url,
                    source="best_shot_upload",
                    captured_at=session.created_at,
                    sia_comment=sel.sia_comment,
                    coordinate=None,
                ))

        return refs

    def _compose_user_original_phrases(self) -> list[str]:
        """CLAUDE.md R2 원칙 — 리포트 재활용 키워드.

        Phase H 에서 Haiku 가 user_original_phrase 필드 extraction.
        MVP 에선 structured_fields 에 저장된 자유 텍스트 들을 그대로 반영.
        """
        sf = self.structured_fields or {}
        collected = sf.get("user_original_phrases")
        if isinstance(collected, list):
            return [p for p in collected if isinstance(p, str) and p.strip()]
        # 대체 소스 — current_concerns / trial_history 원문 일부
        out: list[str] = []
        for key in ("current_concerns", "trial_history", "specific_context"):
            v = sf.get(key)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
        return out


# ─────────────────────────────────────────────
#  Loader — DB 에서 vault 조립
# ─────────────────────────────────────────────

def load_vault(db, user_id: str) -> Optional[UserDataVault]:
    """DB 에서 유저 전수 데이터를 읽어 vault 조립.

    db is None 시 (테스트 환경) None 반환.
    user_profiles row 없으면 None.
    """
    if db is None:
        return None

    profile = get_profile(db, user_id)
    if profile is None:
        return None

    basic = UserBasicInfo(
        user_id=user_id,
        gender=profile.get("gender"),
        birth_date=_date_to_str(profile.get("birth_date")),
        ig_handle=profile.get("ig_handle"),
        name=_fetch_user_name(db, user_id),
    )

    # 상품별 카운트 — MVP 는 0. Phase I/J/K/M 진행 시 각 테이블 COUNT(*) 연결.
    counts = _fetch_product_counts(db, user_id)

    structured_fields = dict(profile.get("structured_fields") or {})
    ig_feed_cache = profile.get("ig_feed_cache")
    # Phase H-lite: Sia 가 structured_fields["coordinate"] 를 아직 산출하지 않는
    # MVP 단계에서, IG Vision analysis 가 있으면 derive_coordinate_from_analysis
    # 로 fallback 좌표를 주입. Phase H Sia 직접 산출물이 생기면 그쪽이 우선.
    _inject_coordinate_fallback(structured_fields, ig_feed_cache)

    # users.user_history JSONB → UserHistory 객체. STEP 4 append hook 의 누적본.
    user_history = _fetch_user_history(db, user_id)

    # 최신 aspiration GapVector — UserTasteProfile.aspiration_vector 연결용.
    latest_gap = _fetch_latest_aspiration_gap(db, user_id)

    # pi_versions / monthly_reports — 테이블 직접 조회, 경량 요약.
    pi_versions = _fetch_pi_versions(db, user_id)
    monthly_reports = _fetch_monthly_reports(db, user_id)

    return UserDataVault(
        basic_info=basic,
        ig_feed_cache=ig_feed_cache,
        structured_fields=structured_fields,
        conversation_count=counts.get("conversation_count", 0),
        aspiration_count=counts.get("aspiration_count", 0),
        best_shot_count=counts.get("best_shot_count", 0),
        pi_version_count=counts.get("pi_version_count", 0),
        monthly_report_count=counts.get("monthly_report_count", 0),
        user_history=user_history,
        latest_aspiration_gap=latest_gap,
        pi_versions=pi_versions,
        monthly_reports=monthly_reports,
    )


def _fetch_pi_versions(db, user_id: str) -> list[PiVersionEntry]:
    """pi_reports 전수 목록 (최신 created_at 순). 테이블/컬럼 없으면 []."""
    try:
        rows = db.execute(
            text(
                "SELECT report_id, version, is_current, created_at, unlocked_at "
                "FROM pi_reports WHERE user_id = :uid "
                "ORDER BY version DESC, created_at DESC "
                "LIMIT 10"
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        logger.debug("pi_reports fetch skipped for user=%s", user_id)
        return []

    out: list[PiVersionEntry] = []
    for row in rows or []:
        try:
            out.append(PiVersionEntry(
                report_id=str(getattr(row, "report_id", "")),
                version=int(getattr(row, "version", 1) or 1),
                is_current=bool(getattr(row, "is_current", False)),
                created_at=getattr(row, "created_at", None),
                unlocked_at=getattr(row, "unlocked_at", None),
            ))
        except Exception:
            logger.debug("pi_reports row parse failed for user=%s", user_id)
    return out


def _fetch_monthly_reports(db, user_id: str) -> list[MonthlyReportEntry]:
    """monthly_reports 전수 (최신 year_month 순). 테이블/컬럼 없으면 []."""
    try:
        rows = db.execute(
            text(
                "SELECT report_id, year_month, status, scheduled_for, generated_at "
                "FROM monthly_reports WHERE user_id = :uid "
                "ORDER BY year_month DESC "
                "LIMIT 10"
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        logger.debug("monthly_reports fetch skipped for user=%s", user_id)
        return []

    out: list[MonthlyReportEntry] = []
    for row in rows or []:
        try:
            out.append(MonthlyReportEntry(
                report_id=str(getattr(row, "report_id", "")),
                year_month=str(getattr(row, "year_month", "") or ""),
                status=str(getattr(row, "status", "") or ""),
                scheduled_for=getattr(row, "scheduled_for", None),
                generated_at=getattr(row, "generated_at", None),
            ))
        except Exception:
            logger.debug("monthly_reports row parse failed for user=%s", user_id)
    return out


def _fetch_user_name(db, user_id: str) -> Optional[str]:
    """users.name 조회. 컬럼 / row 없으면 None (예외 흡수)."""
    try:
        row = db.execute(
            text("SELECT name FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).first()
        if row is None:
            return None
        name = row.name
        if isinstance(name, str) and name.strip():
            return name.strip()
        return None
    except Exception:
        logger.debug("users.name fetch failed for user=%s", user_id)
        return None


def _fetch_user_history(db, user_id: str) -> UserHistory:
    """users.user_history JSONB → UserHistory 파싱.

    컬럼 없음 (migration 미적용) / row 없음 / 파싱 실패 = 빈 UserHistory.
    """
    try:
        row = db.execute(
            text("SELECT user_history FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).first()
    except Exception:
        # 컬럼 없음 (migration 미적용) — MVP 환경에서 흔함
        logger.debug("users.user_history column absent for user=%s", user_id)
        return UserHistory()

    if row is None:
        return UserHistory()

    raw = row.user_history
    if not isinstance(raw, dict):
        return UserHistory()

    try:
        return UserHistory.model_validate(raw)
    except Exception:
        logger.warning(
            "user_history JSONB validation failed user=%s — returning empty",
            user_id,
        )
        return UserHistory()


def _fetch_latest_aspiration_gap(db, user_id: str) -> Optional[GapVector]:
    """최신 aspiration_analyses.result_data.gap_vector 파싱.

    테이블 없음 / 데이터 없음 / 파싱 실패 = None.
    """
    try:
        row = db.execute(
            text(
                "SELECT result_data FROM aspiration_analyses "
                "WHERE user_id = :uid "
                "ORDER BY created_at DESC "
                "LIMIT 1"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        logger.debug("aspiration_analyses fetch skipped for user=%s", user_id)
        return None

    if row is None or not row.result_data:
        return None

    result_raw = row.result_data
    if not isinstance(result_raw, dict):
        return None

    gap_raw = result_raw.get("gap_vector")
    if not isinstance(gap_raw, dict):
        return None

    try:
        return GapVector.model_validate(gap_raw)
    except Exception:
        logger.debug("GapVector parse failed for user=%s", user_id)
        return None


def _inject_coordinate_fallback(
    structured_fields: dict[str, Any],
    ig_feed_cache: Optional[dict],
) -> None:
    """structured_fields["coordinate"] 가 비어있고 IG analysis 가 있으면 fallback 주입.

    CLAUDE.md 좌표 불가침 규칙 준수 — 기존 함수 바디는 손대지 않고,
    vault 조립 시점에 structured_fields 복사본에만 추가.

    우선순위:
      1. structured_fields["coordinate"] (Sia Phase H 직접 산출, 미래) — 건드리지 않음
      2. ig_feed_cache.analysis → derive_coordinate_from_analysis (MVP fallback)
      3. 둘 다 없으면 주입 안 함 → _compose_current_position 이 None 반환
    """
    if structured_fields.get("coordinate") or structured_fields.get("current_position"):
        return
    if not isinstance(ig_feed_cache, dict):
        return
    analysis_raw = ig_feed_cache.get("analysis")
    if not isinstance(analysis_raw, dict):
        return
    try:
        from schemas.user_profile import IgFeedAnalysis
        from services.aspiration_common import derive_coordinate_from_analysis
        analysis = IgFeedAnalysis.model_validate(analysis_raw)
        coord = derive_coordinate_from_analysis(analysis)
    except Exception:
        logger.debug("coordinate fallback derivation failed", exc_info=True)
        return
    structured_fields["coordinate"] = {
        "shape": coord.shape,
        "volume": coord.volume,
        "age": coord.age,
        "source": "ig_analysis_fallback",
    }


def _fetch_product_counts(db, user_id: str) -> dict[str, int]:
    """상품별 수행 횟수. MVP — 존재하는 테이블만 카운트. 없으면 0."""
    counts = {
        "conversation_count": 0,
        "aspiration_count": 0,
        "best_shot_count": 0,
        "pi_version_count": 0,
        "monthly_report_count": 0,
    }
    # 현재 존재하는 테이블만 안전 카운트
    try:
        row = db.execute(
            text("SELECT COUNT(*) FROM conversations WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        counts["conversation_count"] = int(row or 0)
    except Exception:
        # 테이블 없음 or 스키마 불일치 — 무시
        logger.debug("conversations count skipped for user=%s", user_id)

    try:
        row = db.execute(
            text("SELECT COUNT(*) FROM pi_reports WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        counts["pi_version_count"] = int(row or 0)
    except Exception:
        logger.debug("pi_reports count skipped for user=%s", user_id)

    # Phase J/K/M 완료 — 상품 누적 수행 횟수를 strength_score 에 반영.
    try:
        row = db.execute(
            text(
                "SELECT COUNT(*) FROM aspiration_analyses "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).scalar()
        counts["aspiration_count"] = int(row or 0)
    except Exception:
        logger.debug("aspiration_analyses count skipped for user=%s", user_id)

    try:
        # 완료된 세션만 집계 — failed/aborted 제외.
        row = db.execute(
            text(
                "SELECT COUNT(*) FROM best_shot_sessions "
                "WHERE user_id = :uid AND status = 'ready'"
            ),
            {"uid": user_id},
        ).scalar()
        counts["best_shot_count"] = int(row or 0)
    except Exception:
        logger.debug("best_shot_sessions count skipped for user=%s", user_id)

    try:
        row = db.execute(
            text(
                "SELECT COUNT(*) FROM monthly_reports WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).scalar()
        counts["monthly_report_count"] = int(row or 0)
    except Exception:
        logger.debug("monthly_reports count skipped for user=%s", user_id)

    return counts


# ─────────────────────────────────────────────
#  helpers
# ─────────────────────────────────────────────

def _str_or_none(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _date_to_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _parse_iso(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _photo_id_from_caption(p: dict) -> str:
    """latest_posts 원본에 id 없을 때 안정적 id 생성."""
    if not isinstance(p, dict):
        return "photo_unknown"
    # timestamp + caption 앞 8자 해시 정도면 충분. 간단하게 str 조합.
    ts = p.get("timestamp") or "nots"
    return f"photo_{ts}"
