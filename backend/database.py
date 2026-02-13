"""Database Models and Setup for EVE Project Console"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import os

Base = declarative_base()


class Library(Base):
    """Library/Project model"""
    __tablename__ = "libraries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    root_path = Column(String(1024), nullable=False, unique=True)
    type = Column(String(50), nullable=False)  # project or library
    tags = Column(JSON, default=list)
    file_count = Column(Integer, default=0)
    last_indexed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FileEntry(Base):
    """File entry model"""
    __tablename__ = "file_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    library_id = Column(String, nullable=False, index=True)
    path = Column(String(2048), nullable=False)  # Full path
    rel_path = Column(String(2048), nullable=False)  # Relative to library root
    ext = Column(String(50), nullable=False, index=True)
    size_bytes = Column(Integer, default=0)
    last_modified = Column(DateTime, nullable=False)
    kind = Column(String(50), nullable=False)  # code, doc, spec, config, other
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
DB_PATH = "storage/eve.db"

def get_engine():
    """Create database engine"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db():
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_db():
    """Get database session (FastAPI dependency)"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
