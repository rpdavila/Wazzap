from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ChatType(str, Enum):
    direct = "direct"
    group = "group"

class MessageType(str, Enum):
    text = "text"
    media = "media"

# --- User schemas ---
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64)

class UserCreate(UserBase):
    pin: str = Field(min_length=4, max_length=8)

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# --- Chat schemas ---
class ChatBase(BaseModel):
    type: ChatType
    title: Optional[str] = None

class ChatOut(ChatBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# --- ChatMember schemas ---
class ChatMemberBase(BaseModel):
    last_seen_at: Optional[datetime] = None
    active_chat_id: Optional[int] = None

class ChatMemberOut(ChatMemberBase):
    chat_id: int
    user_id: int

    class Config:
        orm_mode = True

# --- Message schemas ---
class MessageBase(BaseModel):
    type: MessageType
    text: Optional[str] = None
    media_url: Optional[str] = None

class MessageCreate(MessageBase):
    chat_id: int
    sender_id: int

class MessageOut(MessageBase):
    id: str
    chat_id: int
    sender_id: int
    created_at: datetime

    class Config:
        orm_mode = True

# --- MessageStatus schemas ---
class MessageStatusBase(BaseModel):
    received_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

class MessageStatusOut(MessageStatusBase):
    message_id: str
    user_id: int

    class Config:
        orm_mode = True
