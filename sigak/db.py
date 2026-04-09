"""SIGAK Database Models — 3-Axis Coordinate System (shape/volume/age)"""
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
#  Interview Data
# ─────────────────────────────────────────────

class InterviewData(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    interviewer_name = Column(String(50))

    # Core Questions
    self_perception = Column(Text)
    desired_image = Column(Text)
    reference_celebs = Column(Text)
    style_keywords = Column(Text)
    current_concerns = Column(Text)
    daily_routine = Column(Text)

    # Tier-Specific: Wedding
    wedding_date = Column(Date)
    wedding_concept = Column(Text)
    dress_preference = Column(Text)

    # Tier-Specific: Creator
    content_style = Column(Text)
    target_audience = Column(Text)
    brand_tone = Column(Text)

    # Raw
    raw_notes = Column(Text)
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

    # Photo References
    photo_urls = Column(JSON, default=list)

    # Structural Features
    face_shape = Column(String(20))
    jaw_angle = Column(Float)
    cheekbone_prominence = Column(Float)
    eye_width_ratio = Column(Float)
    eye_spacing_ratio = Column(Float)
    eye_ratio = Column(Float)
    eye_tilt = Column(Float)
    nose_length_ratio = Column(Float)
    nose_width_ratio = Column(Float)
    nose_bridge_height = Column(Float)
    lip_fullness = Column(Float)
    face_length_ratio = Column(Float)
    forehead_ratio = Column(Float)
    brow_arch = Column(Float)
    philtrum_ratio = Column(Float)
    brow_eye_distance = Column(Float)
    symmetry_score = Column(Float)
    golden_ratio_score = Column(Float)

    # CLIP Embedding
    clip_embedding = Column(Vector(768))

    # 3-Axis Coordinates (shape/volume/age)
    coord_shape = Column(Float)      # Soft(-1) ↔ Sharp(+1)
    coord_volume = Column(Float)     # Subtle(-1) ↔ Bold(+1)
    coord_age = Column(Float)        # Fresh(-1) ↔ Mature(+1)

    # Skin Analysis
    skin_tone_category = Column(String(20))
    skin_brightness = Column(Float)
    skin_warmth_score = Column(Float)
    skin_chroma = Column(Float)
    skin_hex_sample = Column(String(10))

    landmarks_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="analysis")


# ─────────────────────────────────────────────
#  Report
# ─────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Coordinate Summary (3-axis)
    current_coords = Column(JSON)        # {shape, volume, age}
    aspiration_coords = Column(JSON)
    gap_vector = Column(JSON)
    trend_position = Column(JSON)

    # Generated Content
    report_sections = Column(JSON)
    executive_summary = Column(Text)
    action_items = Column(JSON)

    # Delivery
    report_url = Column(String(500))
    pdf_url = Column(String(500))
    sent_at = Column(DateTime)
    viewed_at = Column(DateTime)

    # Feedback
    satisfaction_score = Column(Integer)
    usefulness_score = Column(Integer)
    feedback_text = Column(Text)
    would_repurchase = Column(Boolean)
    would_recommend = Column(Boolean)

    # B2B Opt-in
    b2b_opt_in = Column(Boolean, default=False)
    b2b_categories = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="report")


# ─────────────────────────────────────────────
#  Type Anchors (AI-generated, 8 types)
# ─────────────────────────────────────────────

class TypeAnchor(Base):
    __tablename__ = "type_anchors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_key = Column(String(20), nullable=False, unique=True)  # type_1 ~ type_8
    name_kr = Column(String(100), nullable=False)
    name_en = Column(String(100))
    gender = Column(String(10))

    clip_embedding = Column(Vector(768))

    # 3-Axis Coordinates
    coord_shape = Column(Float)
    coord_volume = Column(Float)
    coord_age = Column(Float)

    quadrant = Column(String(30))
    one_liner = Column(String(200))
    description_kr = Column(Text)
    photo_url = Column(String(500))
    tags = Column(JSON, default=list)


# ─────────────────────────────────────────────
#  DB Engine Setup
# ─────────────────────────────────────────────

def get_engine(database_url: str):
    return create_async_engine(database_url, echo=True)

def get_session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
