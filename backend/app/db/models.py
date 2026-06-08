import uuid
from datetime import datetime       
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from pgvector.sqlalchemy import Vector
from backend.app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Thread(Base):
    __tablename__ = "threads"

    thread_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    tickers = Column(JSON, nullable=False)
    status = Column(String(50), default="initiated", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

