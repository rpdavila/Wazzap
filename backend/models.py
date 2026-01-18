from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base  # <- import Base from database.py

# -------------------------------
# USERS
# -------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    pin_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("ChatMember", back_populates="user")
    messages = relationship("Message", back_populates="sender")
    message_statuses = relationship("MessageStatus", back_populates="user")


# -------------------------------
# CHATS
# -------------------------------
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(16), nullable=False)  # "direct" or "group"
    title = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("ChatMember", back_populates="chat")
    messages = relationship("Message", back_populates="chat")


# -------------------------------
# CHAT MEMBERS
# -------------------------------
class ChatMember(Base):
    __tablename__ = "chat_members"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    active_chat_id = Column(Integer, nullable=True)

    chat = relationship("Chat", back_populates="members")
    user = relationship("User", back_populates="chats")


# -------------------------------
# MESSAGES
# -------------------------------
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(16), nullable=False)  # "text" or "media"
    text = Column(String(1024), nullable=True)
    media_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    statuses = relationship("MessageStatus", back_populates="message")


# -------------------------------
# MESSAGE STATUS
# -------------------------------
class MessageStatus(Base):
    __tablename__ = "message_status"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    received_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    message = relationship("Message", back_populates="statuses")
    user = relationship("User", back_populates="message_statuses")
