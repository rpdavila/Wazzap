# models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime

class ChatType(str, enum.Enum):
    direct = "direct"
    group = "group"

class MessageType(str, enum.Enum):
    text = "text"
    media = "media"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    pin_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    chats = relationship("ChatMember", back_populates="user")
    messages = relationship("Message", back_populates="sender")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ChatType), nullable=False)
    title = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship("ChatMember", back_populates="chat")
    messages = relationship("Message", back_populates="chat")

class ChatMember(Base):
    __tablename__ = "chat_members"
    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    active_chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True)
    chat = relationship("Chat", back_populates="members", foreign_keys=[chat_id])
    user = relationship("User", back_populates="chats", foreign_keys=[user_id])

class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True, index=True)  # UUID
    chat_id = Column(Integer, ForeignKey("chats.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    type = Column(Enum(MessageType), nullable=False)
    text = Column(String(500), nullable=True)
    media_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    statuses = relationship("MessageStatus", back_populates="message")

class MessageStatus(Base):
    __tablename__ = "message_statuses"
    message_id = Column(String(36), ForeignKey("messages.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    received_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    message = relationship("Message", back_populates="statuses")
