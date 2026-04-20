"""SIGAK Database -- Sync SQLAlchemy for MVP"""
import os
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, create_engine, text as sqlalchemy_text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import uuid
import re
from sqlalchemy.dialects.postgresql import JSONB

DATABASE_URL = os.getenv("DATABASE_URL", "")
# 모든 변형을 psycopg2용 postgresql:// 로 정규화
DATABASE_URL = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", DATABASE_URL)

# 시작 시 URL 존재 여부 로깅 (비밀번호 제외)
if DATABASE_URL:
    _safe = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "set"
    print(f"[DB] DATABASE_URL detected: ...@{_safe}")
else:
    print("[DB] DATABASE_URL not set")

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    kakao_id = Column(String, unique=True, nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    kakao_nickname = Column(String(100), nullable=True)
    kakao_profile_image = Column(String(500), nullable=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    gender = Column(String(10), default="female")
    tier = Column(String(20), default="standard")
    status = Column(String(20), default="booked")
    extra_data = Column(JSON, default=dict)  # everything else from user dict
    casting_opted_in = Column(Boolean, default=False)
    casting_opted_at = Column(DateTime, nullable=True)
    casting_opted_out_at = Column(DateTime, nullable=True)
    # MVP v1.2 onboarding persistence (flat JSONB matching SubmitRequest keys)
    onboarding_completed = Column(Boolean, default=False, server_default="false", nullable=False)
    onboarding_data = Column(JSONB, nullable=True)
    # MVP v2.0 terms (2026-04-20): 약관/개인정보/민감정보/국외이전/만14세 + 선택 마케팅.
    # consent_data에 {timestamp, ip, terms_version, terms, privacy, sensitive, overseas_transfer, age_confirmed, marketing} 저장.
    consent_completed = Column(Boolean, default=False, server_default="false", nullable=False)
    consent_data = Column(JSONB, nullable=True)
    # MVP v1.2 시각 리포트 해제 플래그. 30토큰 소비 시 TRUE.
    # 시각 재설정 시 FALSE로 되돌아가지만, release는 idempotent라 재해제 시 추가 차감 없음.
    sigak_report_released = Column(Boolean, default=False, server_default="false", nullable=False)
    # MVP v1.2 Phase C: LLM #2 (interpret_interview) cache — hash invalidates when onboarding_data changes
    interview_interpretation = Column(JSONB, nullable=True)
    interview_interpretation_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    orders = relationship("Order", back_populates="user")
    reports = relationship("Report", back_populates="user")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)  # ord_xxx format
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tier = Column(String(20), nullable=False)
    order_type = Column(String(20), default="new")  # "new" or "upgrade"
    amount = Column(Integer, nullable=False)
    status = Column(String(20), default="pending_payment")
    report_id = Column(String, nullable=True)
    interview_data = Column(JSON, nullable=True)
    analysis_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)
    user = relationship("User", back_populates="orders")


class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    access_level = Column(String(20), default="standard")
    pending_level = Column(String(20), nullable=True)
    report_data = Column(JSON, nullable=True)  # the entire formatted report
    raw_data = Column(JSON, nullable=True)  # coords, gap, content etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    upgraded_at = Column(DateTime, nullable=True)
    feedback = Column(JSON, nullable=True)
    user = relationship("User", back_populates="reports")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)       # report_ready, upgrade_complete, system
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Engine + Session setup
engine = None
SessionLocal = None


def _migrate_columns(eng):
    """기존 테이블에 누락된 컬럼 추가 (ALTER TABLE)."""
    migrations = [
        # users 테이블: 카카오 로그인 + 캐스팅 컬럼
        ("users", "kakao_id", "VARCHAR UNIQUE"),
        ("users", "email", "VARCHAR(255)"),
        ("users", "kakao_nickname", "VARCHAR(100)"),
        ("users", "kakao_profile_image", "VARCHAR(500)"),
        ("users", "casting_opted_in", "BOOLEAN DEFAULT FALSE"),
        ("users", "casting_opted_at", "TIMESTAMP"),
        ("users", "casting_opted_out_at", "TIMESTAMP"),
        # MVP v2.0 consent (ad-hoc 안전망, Alembic이 먼저 돌면 중복이지만 IF NOT EXISTS로 통과)
        ("users", "consent_completed", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("users", "consent_data", "JSONB"),
        # MVP v1.2 시각 리포트 해제 플래그
        ("users", "sigak_report_released", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ]
    with eng.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(
                    sqlalchemy_text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")
                )
            except Exception as e:
                print(f"[MIGRATE] {table}.{column} skip: {e}")
        conn.commit()
    print("[DB] Column migration complete")


def init_db():
    """Initialize database engine and create tables. Call on startup."""
    global engine, SessionLocal
    if not DATABASE_URL:
        print("[DB] DATABASE_URL not set, skipping DB init")
        return False
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        _migrate_columns(engine)
        print("[DB] Tables created/verified")
        return True
    except Exception as e:
        print(f"[DB] init failed: {e}")
        engine = None
        SessionLocal = None
        return False


def get_db():
    """Get a database session. Returns None if DB not initialized."""
    if SessionLocal is None:
        return None
    db = SessionLocal()
    return db
