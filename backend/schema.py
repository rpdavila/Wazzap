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


class GroupChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128, description="Group chat title")
    member_ids: list[int] = Field(min_length=1, description="List of user IDs to add to the group")


class ChatOut(ChatBase):
    id: int
    created_at: datetime
    other_user_name: Optional[str] = None
    unread_count: Optional[int] = 0  # Number of unread messages for the current user

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


class ChatMemberWithUser(ChatMemberOut):
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    user_id: int


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
    pin: str = Field(min_length=4, max_length=8, description="Admin PIN")
    
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


# -----------------------
# RESPONSE SCHEMAS
# -----------------------
class LoginResponse(BaseModel):
    jwt: str = Field(description="JWT token for authentication")
    session_id: str = Field(description="Session ID for WebSocket connection")
    username: str = Field(description="Username")
    user_id: int = Field(description="User ID")


class LogoutResponse(BaseModel):
    message: str = Field(default="Logout successful", description="Logout confirmation message")


class MediaUploadResponse(BaseModel):
    media_url: str = Field(description="URL to access the uploaded media file")
    filename: str = Field(description="Unique filename of the uploaded file")


class AdminAuthResponse(BaseModel):
    admin_token: str = Field(description="Admin authentication token")
    message: str = Field(default="Admin authentication successful", description="Authentication confirmation")


class MessageResponse(BaseModel):
    message: str = Field(description="Response message")


class ResetDatabaseResponse(BaseModel):
    message: str = Field(description="Reset confirmation message")
    status: str = Field(description="Reset status (success)")