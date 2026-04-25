"""Type Reference 어댑터 — Phase I PI-C.

type_anchors[matched_type_id] features → bullet 3-5.
cluster_labels[type 소속 cluster] → cluster_label 한 단어.
vault_phrases echo → reason.
순수 함수.
"""
from __future__ import annotations

from schemas.pi_report import TypeReferenceContent


_REASON_MAX_CHARS = 120


def build_type_reference(
    matched_type_id: str,
    type_anchors: dict | None,
    cluster_labels: dict | None,
    vault_phrases: list[str] | None,
) -> TypeReferenceContent:
    """매칭 타입 + 클러스터 + vault echo → TypeReferenceContent.

    Args:
        matched_type_id: "type_1" 등.
        type_anchors: data/type_anchors.json 전체 dict.
        cluster_labels: data/cluster_labels.json 전체 dict.
        vault_phrases: 유저 발화 원어. echo 로 reason 합성.
    """
    safe_id = (matched_type_id or "").strip()
    safe_anchors = type_anchors if isinstance(type_anchors, dict) else {}
    safe_clusters = cluster_labels if isinstance(cluster_labels, dict) else {}
    safe_phrases = [p for p in (vault_phrases or []) if isinstance(p, str) and p.strip()]

    anchor_root = safe_anchors.get("anchors", {})
    type_meta = anchor_root.get(safe_id) or {}

    matched_name = str(type_meta.get("name_kr") or "")
    bullets_raw = type_meta.get("features_bullet") or []
    features_bullet: list[str] = [
        str(item) for item in bullets_raw if isinstance(item, str) and item.strip()
    ][:5]

    # cluster_label — type_id 가 어느 cluster.members 에 있는지 탐색
    cluster_label = ""
    for cluster in safe_clusters.get("clusters", []):
        members = cluster.get("members", [])
        if safe_id in members:
            cluster_label = str(cluster.get("label_kr") or cluster.get("id") or "")
            break

    # reason — vault echo + type 한 줄 매칭
    if matched_name:
        if safe_phrases:
            phrase_str = " · ".join(f"\"{p}\"" for p in safe_phrases[:2])
            reason = f"본인이 말한 {phrase_str} 결이 {matched_name} 타입과 닿아 있어요."
        else:
            one_liner = str(type_meta.get("one_liner") or "")
            if one_liner:
                reason = f"{matched_name} — {one_liner}"
            else:
                reason = f"분석 결과 {matched_name} 결로 매칭됐어요."
    else:
        # Day 1 fallback
        reason = "타입 매칭은 더 많은 데이터가 쌓이면 또렷해져요."

    if len(reason) > _REASON_MAX_CHARS:
        reason = reason[: _REASON_MAX_CHARS - 1].rstrip() + "…"

    return TypeReferenceContent(
        matched_type_id=safe_id,
        matched_type_name=matched_name,
        reason=reason,
        features_bullet=features_bullet[:5] if len(features_bullet) >= 3 else features_bullet,
        cluster_label=cluster_label,
    )
