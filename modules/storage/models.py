import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from modules.storage.database import Base


class NewsItem(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    source = Column(String(255))
    title = Column(String(1000))
    url = Column(String(2000), unique=True)
    summary = Column(Text)
    content = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class PersonaNote(Base):
    __tablename__ = "persona_notes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500))
    content = Column(Text, nullable=False)
    tags = Column(String(500), default="")  # comma-separated
    is_seed = Column(Boolean, default=False)  # true for built-in Jonas profile
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(36))
    role = Column(String(20))  # "user" | "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
