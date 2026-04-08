"""
SIGAK Overlay Zone Definitions — InsightFace 2d106det 실측 매핑

시각 검증 완료 (2026-04-08, landmark_map_106_crop.png 기반):
  [0-32]   얼굴 윤곽 (0=턱중앙, 1-16=우측 관자→턱, 17-32=좌측 관자→턱)
  [33-37]  오른쪽 눈 윤곽 (5점)
  [38-42]  왼쪽 눈썹 (5점)
  [43-51]  코 브릿지 상단 (이마~미간, 9점)
  [52-54]  코끝/콧볼 (입술 바로 위, 3점)
  [55-59]  윗입술 윤곽 (5점)
  [60-64]  아랫입술 중앙 (5점)
  [65-67]  입술 하단 좌측 보조 (3점)
  [68-70]  입술 하단 우측 보조 (3점)
  [71-82]  코 전체 넓은 영역 (12점)
  [83-93]  왼쪽 눈 윤곽 (11점)
  [94-95]  왼쪽 눈 동공 (2점)
  [96-105] 왼쪽 이마 확장 (10점)
"""


# ─────────────────────────────────────────────
#  Zone → Landmark Polygon 정의
# ─────────────────────────────────────────────

ZONE_LANDMARKS = {
    # ── 볼 사과존 (blush) ──
    # 오른쪽: 우측 윤곽(볼) + 오른쪽 눈 아래 + 코 옆
    "cheek_apple_right": {
        "indices": [11, 12, 13, 14, 15, 2, 52, 37, 33],
        "type": "blush",
        "feather_ratio": 0.30,
        "shape": "ellipse",
        "clip_to_face": True,
    },
    # 왼쪽: 좌측 윤곽(볼) + 왼쪽 눈 아래 + 코 옆
    "cheek_apple_left": {
        "indices": [27, 28, 29, 30, 31, 18, 53, 83, 93],
        "type": "blush",
        "feather_ratio": 0.30,
        "shape": "ellipse",
        "clip_to_face": True,
    },

    # ── 눈 밑 (highlight) ──
    # 오른쪽: 오른쪽 눈(33-37) 하단 + 볼 상단
    "under_eye_right": {
        "indices": [33, 37, 11, 12],
        "type": "highlight",
        "feather_ratio": 0.15,
        "shape": "polygon",
        "clip_to_face": True,
    },
    # 왼쪽: 왼쪽 눈(83-93) 하단 + 볼 상단
    "under_eye_left": {
        "indices": [83, 93, 96, 27, 28],
        "type": "highlight",
        "feather_ratio": 0.15,
        "shape": "polygon",
        "clip_to_face": True,
    },

    # ── 입술 (tint) ──
    # outer: 윗입술(55-59) + 아랫입술(60-67)
    # inner: 아랫입술 보조(68-70) — hole로 사용
    "lip": {
        "indices_outer": [55, 56, 57, 58, 59, 65, 66, 67, 60, 61, 62, 63, 64],
        "indices_inner": [68, 69, 70],
        "type": "tint",
        "feather_ratio": 0.06,
        "shape": "polygon_with_hole",
        "clip_to_face": False,
    },

    # ── 턱선 쉐딩 (shading) ──
    # 오른쪽: 윤곽 하단(턱~볼)
    "jawline_right": {
        "indices": [2, 3, 4, 5, 6, 7, 8, 0, 14, 15, 16],
        "type": "shading",
        "feather_ratio": 0.25,
        "shape": "polygon",
        "clip_to_face": True,
    },
    # 왼쪽: 윤곽 하단(턱~볼)
    "jawline_left": {
        "indices": [18, 19, 20, 21, 22, 23, 24, 0, 30, 31, 32],
        "type": "shading",
        "feather_ratio": 0.25,
        "shape": "polygon",
        "clip_to_face": True,
    },

    # ── 콧대 하이라이트 ──
    "nose_bridge": {
        "indices": [71, 72, 73, 74, 75, 76, 77],
        "type": "highlight",
        "feather_ratio": 0.20,
        "shape": "polygon",
        "clip_to_face": False,
    },
}


# ─────────────────────────────────────────────
#  Face Type → 자동 추가 Zone
# ─────────────────────────────────────────────

FACE_TYPE_SHADING = {
    "하트형": ["jawline_right", "jawline_left"],
    "각진형": ["jawline_right", "jawline_left"],
    "타원형": [],
    "긴형": ["jawline_right", "jawline_left"],
    "둥근형": ["jawline_right", "jawline_left"],
}


# ─────────────────────────────────────────────
#  Zone Name → 실제 Landmark Zone 리스트 변환
# ─────────────────────────────────────────────

def resolve_zones(zone_name: str, face_type: str = "") -> list[str]:
    """
    overlay_plan의 zone_name을 실제 ZONE_LANDMARKS 키 리스트로 변환.
    좌우 분리 zone은 양쪽 모두 반환.
    """
    mapping = {
        "cheek_apple": ["cheek_apple_right", "cheek_apple_left"],
        "under_eye": ["under_eye_right", "under_eye_left"],
        "lip": ["lip"],
        "nose_bridge": ["nose_bridge"],
        "overall": FACE_TYPE_SHADING.get(face_type, []),
        "jawline": ["jawline_right", "jawline_left"],
    }
    return mapping.get(zone_name, [])


# ─────────────────────────────────────────────
#  Face Contour Indices (face mask 생성용)
# ─────────────────────────────────────────────

# 얼굴 외곽: 윤곽(0-32) + 이마 확장(96-105) + 눈썹(38-42) + 코 상단(43-48)
# convexHull이 전체 얼굴(이마 포함)을 감싸도록 충분한 포인트 포함
FACE_CONTOUR_INDICES = list(range(0, 33)) + list(range(96, 106)) + list(range(38, 43)) + list(range(43, 49))
