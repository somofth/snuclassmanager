import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import DB_PATH


class Base(DeclarativeBase):
    pass


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    room = Column(String, default="")
    day_of_week = Column(Integer, nullable=False)  # 0=월 ~ 6=일
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    recordings = relationship("Recording", back_populates="subject")
    materials = relationship("Material", back_populates="subject")
    assignments = relationship("Assignment", back_populates="subject")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_number = Column(Integer, nullable=True)  # 차시
    file_path = Column(String, nullable=False)
    summary = Column(Text, default="")
    recorded_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    subject = relationship("Subject", back_populates="recordings")
    assignments = relationship("Assignment", back_populates="recording")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_number = Column(Integer, nullable=True)  # 차시
    file_path = Column(String, nullable=False)
    file_name = Column(String, default="")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    subject = relationship("Subject", back_populates="materials")
    assignments = relationship("Assignment", back_populates="material")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    recording_id = Column(Integer, ForeignKey("recordings.id"), nullable=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    due_date = Column(String, default="")  # 자유 형식 (교수님 말씀 그대로)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    subject = relationship("Subject", back_populates="assignments")
    recording = relationship("Recording", back_populates="assignments")
    material = relationship("Material", back_populates="assignments")


# DB 초기화
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)

# 마이그레이션: 기존 DB에 session_number 컬럼 추가
_inspector = inspect(engine)
for _table in ("recordings", "materials"):
    _cols = [c["name"] for c in _inspector.get_columns(_table)]
    if "session_number" not in _cols:
        with engine.connect() as _conn:
            _conn.execute(text(f"ALTER TABLE {_table} ADD COLUMN session_number INTEGER"))
            _conn.commit()

SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()
