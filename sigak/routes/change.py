"""변화 엔드포인트 — v2 BM.

GET /api/v1/change — 유저의 모든 verdict 시계열 (추구미 대비 좌표 이동 추적용).

무료 엔드포인트. 3건 미만이면 빈 entries (프론트가 empty state 렌더).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from deps import db_session, get_current_user


router = APIRouter(prefix="/api/v1/change", tags=["change"])


class AxisPoint(BaseModel):
    shape: float
    volume: float
    age: float


class ChangeEntry(BaseModel):
    verdict_id: str
    created_at: str
    winner_coords: Optional[AxisPoint] = None  # 우승 사진의 좌표
    target_coords: Optional[AxisPoint] = None  # 해당 시점의 추구미 좌표
    diagnosis_unlocked: bool = False


class ChangeResponse(BaseModel):
    entries: list[ChangeEntry]
    count: int


def _to_axis(d: Optional[dict]) -> Optional[AxisPoint]:
    if not isinstance(d, dict):
        return None
    try:
        return AxisPoint(
            shape=float(d.get("shape", 0.0)),
            volume=float(d.get("volume", 0.0)),
            age=float(d.get("age", 0.0)),
        )
    except (TypeError, ValueError):
        return None


@router.get("", response_model=ChangeResponse)
def get_change(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """유저 전체 verdict 시계열 반환. created_at ASC (차트 왼쪽→오른쪽).

    coordinates_snapshot 구조:
      {
        "target": {shape, volume, age},
        "photos": [{photo_id, coords: {shape, volume, age}}, ...]
      }
    photos[0]이 winner (score 기준 정렬 후 첫 번째, 저장 시 ranked 순서대로).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    rows = db.execute(
        text(
            "SELECT id, winner_photo_id, coordinates_snapshot, diagnosis_unlocked, "
            "       created_at "
            "FROM verdicts "
            "WHERE user_id = :uid "
            "ORDER BY created_at ASC"
        ),
        {"uid": user["id"]},
    ).fetchall()

    entries: list[ChangeEntry] = []
    for row in rows:
        snapshot = row.coordinates_snapshot or {}
        target = _to_axis(snapshot.get("target"))

        # winner_photo_id에 해당하는 coords 찾기. 없으면 photos[0] 폴백.
        winner_coords: Optional[AxisPoint] = None
        photos = snapshot.get("photos") or []
        if isinstance(photos, list):
            for p in photos:
                if (
                    isinstance(p, dict)
                    and p.get("photo_id") == row.winner_photo_id
                ):
                    winner_coords = _to_axis(p.get("coords"))
                    break
            if winner_coords is None and photos:
                first = photos[0]
                if isinstance(first, dict):
                    winner_coords = _to_axis(first.get("coords"))

        entries.append(
            ChangeEntry(
                verdict_id=row.id,
                created_at=row.created_at.isoformat() if row.created_at else "",
                winner_coords=winner_coords,
                target_coords=target,
                diagnosis_unlocked=bool(row.diagnosis_unlocked),
            )
        )

    return ChangeResponse(entries=entries, count=len(entries))
