"""SIGAK Database -- Sync SQLAlchemy for MVP"""
import os
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import re

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
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    gender = Column(String(10), default="female")
    tier = Column(String(20), default="standard")
    status = Column(String(20), default="booked")
    extra_data = Column(JSON, default=dict)  # everything else from user dict
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


# Engine + Session setup
engine = None
SessionLocal = None


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
