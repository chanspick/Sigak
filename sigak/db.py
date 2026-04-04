"""SIGAK Database Models"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, JSON, Enum as SAEnum, create_engine,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pgvector.sqlalchemy import Vector

Base = declarative_base()


# ─────────────────────────────────────────────
#  Users + Bookings
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    instagram = Column(String(100))
    tier = Column(String(20), nullable=False)        # basic | creator | wedding
    booking_date = Column(Date, nullable=False)
    booking_time = Column(String(5), nullable=False)  # "14:00"
    price = Column(Integer, nullable=False)

    # Wedding-specific
    partner_name = Column(String(100))
    partner_phone = Column(String(20))

    # Creator-specific
    channel_url = Column(String(300))

    status = Column(String(20), default="booked")
    # booked → interviewed → analyzing → reported → feedback_done
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    interview = relationship("InterviewData", back_populates="user", uselist=False)
    analysis = relationship("FaceAnalysis", back_populates="user", uselist=False)
    report = relationship("Report", back_populates="user", uselist=False)


# ─────────────────────────────────────────────
#  Interview Data (알바 입력)
# ─────────────────────────────────────────────

class InterviewData(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    interviewer_name = Column(String(50))

    # ── Core Questions ──
    self_perception = Column(Text)       # "본인이 생각하는 자기 이미지는?"
    desired_image = Column(Text)         # "되고 싶은 이미지/추구미는?" (자유형)
    reference_celebs = Column(Text)      # "닮고 싶은/닮았다는 말 듣는 셀럽은?"
    style_keywords = Column(Text)        # "본인 스타일을 키워드로 표현하면?"
    current_concerns = Column(Text)      # "현재 외모에서 바꾸고 싶은 점?"
    daily_routine = Column(Text)         # "평소 메이크업/스타일링 루틴?"

    # ── Tier-Specific ──
    # Wedding
    wedding_date = Column(Date)
    wedding_concept = Column(Text)       # "원하는 웨딩 컨셉?"
    dress_preference = Column(Text)      # "드레스 라인 선호?"

    # Creator
    content_style = Column(Text)         # "콘텐츠 장르/분위기?"
    target_audience = Column(Text)       # "타겟 시청자층?"
    brand_tone = Column(Text)            # "채널이 추구하는 톤?"

    # ── Raw ──
    raw_notes = Column(Text)             # 알바 자유 메모
    zoom_recording_url = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interview")


# ─────────────────────────────────────────────
#  Face Analysis (CV Pipeline Output)
# ─────────────────────────────────────────────

class FaceAnalysis(Base):
    __tablename__ = "face_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # ── Photo References ──
    photo_urls = Column(JSON, default=list)  # ["s3://sigak/user_id/front.jpg", ...]

    # ── MediaPipe Structural Features ──
    face_shape = Column(String(20))      # oval, round, square, heart, oblong
    jaw_angle = Column(Float)            # degrees — sharp(< 120) to soft(> 140)
    cheekbone_prominence = Column(Float) # 0–1 ratio
    eye_width_ratio = Column(Float)      # eye width / face width
    eye_spacing_ratio = Column(Float)    # inner eye dist / face width
    nose_length_ratio = Column(Float)    # nose / face height
    nose_width_ratio = Column(Float)     # nose width / face width
    lip_fullness = Column(Float)         # lip height / face height
    forehead_ratio = Column(Float)       # forehead / face height
    symmetry_score = Column(Float)       # 0–1
    golden_ratio_score = Column(Float)   # proximity to phi ratios

    # ── CLIP Embedding ──
    clip_embedding = Column(Vector(512))

    # ── 4-Axis Coordinates (output of anchor projection) ──
    coord_structure = Column(Float)      # -1 (sharp) → +1 (soft)
    coord_impression = Column(Float)     # -1 (warm) → +1 (cool)
    coord_maturity = Column(Float)       # -1 (fresh) → +1 (mature)
    coord_intensity = Column(Float)      # -1 (natural) → +1 (bold)

    # ── Skin Analysis ──
    skin_tone_category = Column(String(20))   # cool / warm / neutral
    skin_brightness = Column(Float)            # 0–1

    landmarks_json = Column(JSON)        # raw 468-point landmarks for debug

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="analysis")


# ─────────────────────────────────────────────
#  Report
# ─────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # ── Coordinate Summary ──
    current_coords = Column(JSON)        # {structure, impression, maturity, intensity}
    aspiration_coords = Column(JSON)     # same shape
    gap_vector = Column(JSON)            # same shape (differences)
    trend_position = Column(JSON)        # where current trend center is

    # ── Generated Content ──
    report_sections = Column(JSON)       # Full structured report data
    # Sections: overview, face_structure, skin_analysis, coordinate_map,
    #           gap_analysis, action_plan, trend_context, references

    executive_summary = Column(Text)     # 1-paragraph summary
    action_items = Column(JSON)          # [{category, recommendation, priority}]

    # ── Delivery ──
    report_url = Column(String(500))
    pdf_url = Column(String(500))
    sent_at = Column(DateTime)
    viewed_at = Column(DateTime)

    # ── Feedback (H2 + H3 validation) ──
    satisfaction_score = Column(Integer)  # 1–5
    usefulness_score = Column(Integer)    # 1–5
    feedback_text = Column(Text)
    would_repurchase = Column(Boolean)
    would_recommend = Column(Boolean)

    # ── B2B Opt-in (H4) ──
    b2b_opt_in = Column(Boolean, default=False)
    b2b_categories = Column(JSON)        # ["광고", "드라마", "뷰티"]

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="report")


# ─────────────────────────────────────────────
#  Celeb Reference Anchors (pre-populated)
# ─────────────────────────────────────────────

class CelebAnchor(Base):
    __tablename__ = "celeb_anchors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    category = Column(String(30))        # idol, actor, model, influencer
    gender = Column(String(10))

    clip_embedding = Column(Vector(512))

    # Pre-computed coordinates
    coord_structure = Column(Float)
    coord_impression = Column(Float)
    coord_maturity = Column(Float)
    coord_intensity = Column(Float)

    photo_url = Column(String(500))
    tags = Column(JSON, default=list)    # ["시크", "쿨톤", "모던"]

    # Which axis poles this celeb anchors
    # e.g. {"structure": "sharp", "impression": "cool"}
    anchor_roles = Column(JSON, default=dict)


# ─────────────────────────────────────────────
#  DB Engine Setup
# ─────────────────────────────────────────────

def get_engine(database_url: str):
    return create_async_engine(database_url, echo=True)

def get_session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
