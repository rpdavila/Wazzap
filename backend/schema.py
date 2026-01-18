from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


# -----------------------
# ENUMS
# -----------------------
class ChatType(str, Enum):
    direct = "direct"
    group = "group"


class MessageType(str, Enum):
    text = "text"
    media = "media"


# -----------------------
# USER SCHEMAS
# -----------------------
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64)


class UserCreate(UserBase):
    pin: str = Field(min_length=4, max_length=8, description="PIN must be 4-8 digits (numbers only)")
    
    @field_validator('pin')
    @classmethod
    def validate_pin_numeric(cls, v: str) -> str:
        """Validate that PIN contains only digits."""
        if not v.isdigit():
            raise ValueError('PIN must contain only numbers (0-9)')
        return v


class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# CHAT SCHEMAS
# -----------------------
class ChatBase(BaseModel):
    type: ChatType
    title: Optional[str] = None


class ChatOut(ChatBase):
    id: int
    created_at: datetime
    other_user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# CHAT MEMBER SCHEMAS
# -----------------------
class ChatMemberBase(BaseModel):
    last_seen_at: Optional[datetime] = None
    active_chat_id: Optional[int] = None


class ChatMemberOut(ChatMemberBase):
    chat_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# MESSAGE SCHEMAS
# -----------------------
class MessageBase(BaseModel):
    type: MessageType
    text: Optional[str] = None
    media_url: Optional[str] = None


class MessageCreate(MessageBase):
    chat_id: int
    sender_id: int


class MessageOut(MessageBase):
    id: int  # changed to int to match SQLAlchemy model
    chat_id: int
    sender_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# MESSAGE STATUS SCHEMAS
# -----------------------
class MessageStatusBase(BaseModel):
    received_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


class MessageStatusOut(MessageStatusBase):
    message_id: int  # changed to int to match SQLAlchemy model
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# ADMIN SCHEMAS
# -----------------------
class AdminAuth(BaseModel):
    pin: str = Field(min_length=4, max_length=8, description="Admin PIN (default: 0000)")
    
    @field_validator('pin')
    @classmethod
    def validate_pin_numeric(cls, v: str) -> str:
        """Validate that PIN contains only digits."""
        if not v.isdigit():
            raise ValueError('PIN must contain only numbers (0-9)')
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=64)
    pin: Optional[str] = Field(None, min_length=4, max_length=8, description="New PIN to set (numbers only)")
    
    @field_validator('pin')
    @classmethod
    def validate_pin_numeric(cls, v: Optional[str]) -> Optional[str]:
        """Validate that PIN contains only digits."""
        if v is not None and not v.isdigit():
            raise ValueError('PIN must contain only numbers (0-9)')
        return v