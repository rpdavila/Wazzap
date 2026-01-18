from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, APIRouter, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db, engine, Base, SessionLocal, DATABASE_URL
from pathlib import Path
from models import ChatMember
from crud import (
    create_user,
    get_user_by_username,
    get_user,
    create_chat,
    get_chat,
    add_member_to_chat,
    get_chat_members,
    get_chat_members_with_users,
    remove_member_from_chat,
    create_message,
    get_messages_for_chat,
    list_chats_for_user,
    list_all_users,
    update_user,
    delete_user,
    get_unread_count,
    update_last_seen,
    mark_messages_as_read,
    get_message_status,
    get_read_statuses_for_message
)
from schema import (
    UserCreate, UserOut,
    ChatBase, ChatOut, GroupChatCreate,
    ChatMemberBase, ChatMemberOut, ChatMemberWithUser, AddMemberRequest,
    MessageCreate, MessageOut,
    AdminAuth, UserUpdate,
    LoginResponse, LogoutResponse, MediaUploadResponse,
    AdminAuthResponse, MessageResponse, ResetDatabaseResponse
)
import bcrypt
import secrets
import os
import threading
import sys
import json
import logging
from dotenv import load_dotenv
from pathlib import Path

import importlib
import sys
# Import and force reload connection_manager to pick up changes
# Always reload to ensure we get the latest version from disk
import connection_manager
if 'connection_manager' in sys.modules:
    importlib.reload(sys.modules['connection_manager'])
# Re-import to get the updated class
import connection_manager
ConnectionManager = connection_manager.ConnectionManager
# #region agent log
import inspect
reload_sig = inspect.signature(ConnectionManager.connect)
log_data = {
    "sessionId": "debug-session",
    "runId": "run1",
    "hypothesisId": "D",
    "location": "start_backend.py:39",
    "message": "After import/reload - checking ConnectionManager.connect signature",
    "data": {
        "method_signature": str(reload_sig),
        "param_count": len(reload_sig.parameters),
        "param_names": list(reload_sig.parameters.keys()),
        "has_user_id": "user_id" in reload_sig.parameters
    },
    "timestamp": int(__import__('time').time() * 1000)
}
with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
    f.write(__import__('json').dumps(log_data) + '\n')
# #endregion
from starlette.concurrency import run_in_threadpool

# Load .env from root directory first (takes precedence), then backend/.env as fallback
root_dir = Path(__file__).parent.parent
backend_dir = Path(__file__).parent
load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env", override=False)  # Don't override root .env values

# Create media uploads directory
MEDIA_DIR = Path(__file__).parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)

# ==================== LOGGING CONFIGURATION ====================
# Custom formatter for categorized logging
class CategoryFormatter(logging.Formatter):
    def format(self, record):
        # Extract category from extra dict, default to 'GENERAL'
        category = getattr(record, 'category', 'GENERAL')
        # Format the message with category prefix
        record.msg = f"[{category:10s}] {record.msg}"
        return super().format(record)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Create console handler with custom formatter
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CategoryFormatter(
    fmt='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
))
root_logger.addHandler(console_handler)

# Helper function to create category loggers
def create_category_logger(name, category):
    """Create a logger that automatically adds category to log records."""
    logger = logging.getLogger(name)
    
    class CategoryLogger:
        def __init__(self, logger, category):
            self.logger = logger
            self.category = category
        
        def _log(self, level, msg, *args, **kwargs):
            kwargs.setdefault('extra', {})['category'] = self.category
            getattr(self.logger, level)(msg, *args, **kwargs)
        
        def info(self, msg, *args, **kwargs):
            self._log('info', msg, *args, **kwargs)
        
        def warning(self, msg, *args, **kwargs):
            self._log('warning', msg, *args, **kwargs)
        
        def error(self, msg, *args, **kwargs):
            self._log('error', msg, *args, **kwargs)
        
        def debug(self, msg, *args, **kwargs):
            self._log('debug', msg, *args, **kwargs)
    
    return CategoryLogger(logger, category)

# Create category-specific loggers
api_logger = create_category_logger('api', 'API')
ws_logger = create_category_logger('websocket', 'WEBSOCKET')
db_logger = create_category_logger('database', 'DATABASE')
auth_logger = create_category_logger('auth', 'AUTH')

# Suppress verbose SQLAlchemy logging (only show warnings and errors)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)

# Suppress uvicorn access logs (we'll use our own)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

# In-memory session store (cleared on server restart)
# Format: {session_id: {"jwt": jwt_token, "user_id": user_id, "username": username}}
active_sessions: dict[str, dict] = {}

# Create manager instance after reload to ensure we use the latest class definition
manager = ConnectionManager()
# #region agent log
import inspect
manager_sig = inspect.signature(manager.connect)
log_data = {
    "sessionId": "debug-session",
    "runId": "run1",
    "hypothesisId": "E",
    "location": "start_backend.py:150",
    "message": "After manager creation - checking instance method signature",
    "data": {
        "method_signature": str(manager_sig),
        "param_count": len(manager_sig.parameters),
        "param_names": list(manager_sig.parameters.keys()),
        "has_user_id": "user_id" in manager_sig.parameters
    },
    "timestamp": int(__import__('time').time() * 1000)
}
with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
    f.write(__import__('json').dumps(log_data) + '\n')
# #endregion

app = FastAPI(
    title="Wazzap Backend API",
    description="""
    # Wazzap - Real-time Chat Application Backend API
    
    A comprehensive REST and WebSocket API for a real-time chat application with support for direct messages, group chats, media sharing, and user management.
    
    ## Features
    
    - **User Authentication**: PIN-based authentication system
    - **User Management**: Registration, profile management, and admin controls
    - **Chat System**: Direct messages and group chats
    - **Real-time Messaging**: WebSocket-based real-time communication
    - **Media Support**: Image and GIF upload and sharing
    - **Read Receipts**: Message read status tracking
    - **Admin Panel**: Administrative endpoints for user management
    
    ## API Documentation
    
    - **Swagger UI**: Available at `/docs` - Interactive API documentation
    - **ReDoc**: Available at `/redoc` - Alternative API documentation
    
    ## Authentication
    
    Users authenticate using a username and PIN (4-8 digits). Upon successful login, a JWT token and session ID are returned, which are required for WebSocket connections.
    
    ## WebSocket API
    
    The WebSocket endpoint is available at `/api/ws` with the following query parameters:
    - `token`: JWT token (obtained from `/api/auth/login`)
    - `session_id`: Session ID (obtained from `/api/auth/login`)
    
    ### WebSocket Message Types
    
    #### Client → Server:
    
    **`chat.open`** - Open a chat connection
    ```json
    {
      "type": "chat.open",
      "chat_id": 1,
      "user_id": 1
    }
    ```
    
    **`message.send`** - Send a message
    ```json
    {
      "type": "message.send",
      "chat_id": 1,
      "sender_id": 1,
      "content": "Hello!",
      "msg_type": "text",
      "media_url": null
    }
    ```
    
    **`message.read`** - Mark message as read
    ```json
    {
      "type": "message.read",
      "chat_id": 1,
      "message_id": 123
    }
    ```
    
    **`ping`** - Keep-alive ping (sent every 30 seconds)
    ```json
    {
      "type": "ping"
    }
    ```
    
    #### Server → Client:
    
    **`session.ready`** - Connection established
    ```json
    {
      "type": "session.ready",
      "session_id": "session-123"
    }
    ```
    
    **`message.new`** - New message received
    ```json
    {
      "type": "message.new",
      "chat_id": 1,
      "message": {
        "id": 123,
        "chat_id": 1,
        "sender_id": 1,
        "sender_username": "alice",
        "type": "text",
        "text": "Hello!",
        "content": "Hello!",
        "created_at": "2024-01-01T12:00:00",
        "timestamp": "2024-01-01T12:00:00",
        "read_by": [],
        "read_count": 0,
        "status": null
      }
    }
    ```
    
    **`message.read.update`** - Message read status update
    ```json
    {
      "type": "message.read.update",
      "chat_id": 1,
      "message_id": 123,
      "read_by": [2, 3],
      "read_count": 2,
      "read_by_user_id": 2
    }
    ```
    
    **`message.status`** - Message status confirmation
    ```json
    {
      "type": "message.status",
      "chat_id": 1,
      "message_id": 123,
      "status": "read"
    }
    ```
    
    **`chat.member.added`** - Notification when added to a group chat
    ```json
    {
      "type": "chat.member.added",
      "chat_id": 1,
      "chat_title": "My Group",
      "chat_type": "group"
    }
    ```
    
    **`pong`** - Response to ping
    ```json
    {
      "type": "pong"
    }
    ```
    
    ## Admin Mode
    
    Admin endpoints require PIN authentication (default: `0000`). Use the `/api/admin/auth` endpoint to authenticate and get an admin token.
    
    Admin endpoints allow:
    - Viewing all users
    - Creating, updating, and deleting users
    - Resetting the database (⚠️ destructive operation)
    
    ## Error Responses
    
    The API uses standard HTTP status codes:
    - `200`: Success
    - `400`: Bad Request (validation errors, duplicate usernames, etc.)
    - `401`: Unauthorized (invalid credentials or admin PIN)
    - `404`: Not Found (user, chat, or message not found)
    - `500`: Internal Server Error
    
    ## Rate Limiting
    
    Currently, there are no rate limits implemented. Consider implementing rate limiting for production use.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication endpoints (login, register, logout)"
        },
        {
            "name": "Users",
            "description": "User information and management endpoints"
        },
        {
            "name": "Chats",
            "description": "Chat management endpoints (create, list, get chat details, manage members)"
        },
        {
            "name": "Messages",
            "description": "Message endpoints (send, retrieve messages)"
        },
        {
            "name": "Media",
            "description": "Media upload and retrieval endpoints"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints (require admin PIN authentication)"
        }
    ]
)

# Create tables on startup
@app.on_event("startup")
def create_tables():
    """Create all database tables if they don't exist."""
    from models import User, Chat, ChatMember, Message, MessageStatus
    from sqlalchemy import inspect, text
    # Import all models to ensure they're registered with Base.metadata
    # This will create all tables defined in models.py if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Migrate sender_id column to allow NULL if needed (for system messages)
    # Check if the column exists and if it's nullable
    try:
        inspector = inspect(engine)
        if 'messages' in inspector.get_table_names():
            columns = {col['name']: col for col in inspector.get_columns('messages')}
            if 'sender_id' in columns and not columns['sender_id']['nullable']:
                # Column exists but is NOT NULL - need to alter it
                db_logger.info("Migrating messages.sender_id column to allow NULL for system messages...")
                with engine.begin() as conn:  # Use begin() for automatic transaction management
                    # Use raw SQL to alter the column
                    if DATABASE_URL.startswith("sqlite"):
                        # SQLite doesn't support ALTER COLUMN directly, need to recreate table
                        # For now, just log a warning - user should reset database
                        db_logger.warning("SQLite detected: sender_id column needs to be nullable. Please reset the database or manually alter the schema.")
                    else:
                        # MySQL/MariaDB/PostgreSQL
                        if DATABASE_URL.startswith("mysql") or DATABASE_URL.startswith("mariadb"):
                            conn.execute(text("ALTER TABLE messages MODIFY COLUMN sender_id INT NULL"))
                        elif DATABASE_URL.startswith("postgresql"):
                            conn.execute(text("ALTER TABLE messages ALTER COLUMN sender_id DROP NOT NULL"))
                    db_logger.info("Migration completed: sender_id now allows NULL")
    except Exception as e:
        db_logger.warning(f"Could not migrate sender_id column: {e}. System messages may fail. Consider resetting the database.")
    
    db_logger.info("Database tables initialized")
    # Clear all sessions on startup (sessions don't survive server restart)
    active_sessions.clear()
    auth_logger.info("All sessions cleared (server restart)")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")
# -------------------------------
# FOR TESTING PURPOSES
# -------------------------------

class DMCreate(BaseModel):
    user1_id: int
    user2_id: int

# -------------------------------
# AUTH
# -------------------------------
@api_router.post(
    "/auth/register",
    response_model=UserOut,
    summary="Register new user",
    description="""
    Register a new user account.
    
    **Request Body:**
    - `username`: Username (3-64 characters)
    - `pin`: PIN (4-8 digits, numbers only)
    
    **Response:**
    - Returns the newly created user object
    """,
    tags=["Authentication"]
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user.username)
    if existing:
        auth_logger.warning(f"Registration failed: username '{user.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")

    pin_hash = bcrypt.hashpw(user.pin.encode(), bcrypt.gensalt()).decode()
    new_user = create_user(db, user.username, pin_hash)
    auth_logger.info(f"User registered: {user.username} (ID: {new_user.id})")
    return new_user

@api_router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login user",
    description="""
    Authenticate a user with username and PIN.
    
    **Request Body:**
    - `username`: Username
    - `pin`: PIN (4-8 digits, numbers only)
    
    **Response:**
    - `jwt`: JWT token for authentication (use in WebSocket connection)
    - `session_id`: Session ID for WebSocket connection
    - `username`: Username
    - `user_id`: User ID
    
    **Errors:**
    - `400`: User not found or incorrect PIN
    """,
    tags=["Authentication"]
)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user:
        auth_logger.warning(f"Login failed: user '{user.username}' not found")
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(user.pin.encode(), db_user.pin_hash.encode()):
        auth_logger.warning(f"Login failed: incorrect PIN for user '{user.username}'")
        raise HTTPException(status_code=400, detail="Incorrect PIN")

    # Generate JWT token (simplified - in production use proper JWT library)
    jwt_token = secrets.token_urlsafe(32)
    session_id = secrets.token_urlsafe(16)
    
    # Store session in memory (will be cleared on server restart)
    active_sessions[session_id] = {
        "jwt": jwt_token,
        "user_id": db_user.id,
        "username": db_user.username
    }
    
    auth_logger.info(f"User logged in: {user.username} (ID: {db_user.id}), session_id={session_id}")
    return LoginResponse(
        jwt=jwt_token,
        session_id=session_id,
        username=db_user.username,
        user_id=db_user.id
    )

@api_router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    summary="Logout user",
    description="""
    Logout the current user session and invalidate the session.
    
    **Query Parameters:**
    - `session_id`: Session ID to invalidate
    
    **Response:**
    - Returns confirmation message
    
    **Note:**
    - Session is removed from active sessions
    - User will need to login again to access protected resources
    """,
    tags=["Authentication"]
)
def logout(session_id: str = Query(..., description="Session ID")):
    """Logout and invalidate the session."""
    if session_id in active_sessions:
        username = active_sessions[session_id].get("username", "unknown")
        del active_sessions[session_id]
        auth_logger.info(f"User logged out: {username}, session_id={session_id}")
    return LogoutResponse(message="Logout successful")


# -------------------------------
# CURRENT USER
# -------------------------------
@api_router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="""
    Get the current user's information.
    
    Requires `user_id` as a query parameter.
    
    **Response:**
    - Returns `UserOut` object with user details
    """,
    tags=["Users"]
)
def get_me(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.get(
    "/users",
    response_model=list[UserOut],
    summary="Get all users",
    description="""
    Get a list of all users in the system.
    
    This endpoint is used by regular users to see who they can start a chat with.
    Returns a list of all registered users (excluding sensitive information like PIN hashes).
    
    **Use cases:**
    - Display available users in the dashboard
    - Allow users to search and find other users to chat with
    - Start new direct message conversations
    
    **Response:**
    - Returns a list of `UserOut` objects containing:
      - `id`: User ID
      - `username`: Username
      - `created_at`: Account creation timestamp
    """,
    tags=["Users"]
)
def get_all_users(db: Session = Depends(get_db)):
    """Get all users in the system (for regular users to see who they can chat with)."""
    return list_all_users(db)


# -------------------------------
# CHATS
# -------------------------------
@api_router.get(
    "/chats",
    response_model=list[ChatOut],
    summary="Get user's chats",
    description="""
    Get all chats for a specific user.
    
    **Query Parameters:**
    - `user_id`: User ID (optional)
    - `username`: Username (alternative to user_id, optional)
    
    At least one of `user_id` or `username` must be provided.
    """,
    tags=["Chats"]
)
def get_chats(
    user_id: int = Query(None, description="User ID"),
    username: str = Query(None, description="Username (alternative to user_id)"),
    db: Session = Depends(get_db)
):
    # If user_id not provided, try to get from username
    if user_id is None:
        if username:
            db_user = get_user_by_username(db, username)
            if db_user:
                user_id = db_user.id
            else:
                raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=400, detail="Either user_id or username must be provided")
    
    chats = list_chats_for_user(db, user_id)
    
    # Enrich direct message chats with other_user_name, unread_count, and last_message_at
    enriched_chats = []
    for chat in chats:
        # Calculate unread count for this user in this chat
        unread_count = get_unread_count(db, chat.id, user_id)
        
        # Get the last message timestamp for sorting
        from models import Message
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id
        ).order_by(desc(Message.created_at)).first()
        
        last_message_at = last_message.created_at if last_message else chat.created_at
        
        chat_dict = {
            "id": chat.id,
            "type": chat.type,
            "title": chat.title,
            "created_at": chat.created_at,
            "last_message_at": last_message_at.isoformat() if last_message_at else chat.created_at.isoformat() if chat.created_at else None,
            "other_user_name": None,
            "unread_count": unread_count
        }
        
        # For direct messages, find the other user's name
        if chat.type == "direct":
            members = get_chat_members(db, chat.id)
            for member in members:
                if member.user_id != user_id:
                    other_user = get_user(db, member.user_id)
                    if other_user:
                        chat_dict["other_user_name"] = other_user.username
                    break
        
        enriched_chats.append(chat_dict)
    
    # Sort chats by most recent message at the top
    def sort_key(c):
        last_msg = c.get("last_message_at") or c.get("created_at") or ""
        # Convert ISO string to comparable value (newer = larger)
        timestamp = last_msg.replace("T", " ").replace("Z", "").replace("+00:00", "") if last_msg else ""
        return timestamp
    
    enriched_chats.sort(key=sort_key, reverse=True)  # Reverse=True: newest first
    
    return enriched_chats

@api_router.get(
    "/chats/me",
    response_model=list[ChatOut],
    summary="Get my chats",
    description="""
    Get all chats for the current user.
    
    **Query Parameters:**
    - `user_id`: User ID (required)
    
    **Response:**
    - Returns a list of `ChatOut` objects sorted by most recent message (newest first)
    - Each chat includes:
      - Chat ID, type, and title
      - Other user name (for direct messages)
      - Unread message count
      - Last message timestamp
      - Creation timestamp
    """,
    tags=["Chats"]
)
def get_my_chats(user_id: int, db: Session = Depends(get_db)):
    chats = list_chats_for_user(db, user_id)
    
    # Enrich direct message chats with other_user_name, unread_count, and last_message_at
    enriched_chats = []
    for chat in chats:
        # Calculate unread count for this user in this chat
        unread_count = get_unread_count(db, chat.id, user_id)
        
        # Get the last message timestamp for sorting
        from models import Message
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id
        ).order_by(desc(Message.created_at)).first()
        
        last_message_at = last_message.created_at if last_message else chat.created_at
        
        chat_dict = {
            "id": chat.id,
            "type": chat.type,
            "title": chat.title,
            "created_at": chat.created_at,
            "last_message_at": last_message_at.isoformat() if last_message_at else chat.created_at.isoformat() if chat.created_at else None,
            "other_user_name": None,
            "unread_count": unread_count
        }
        
        # For direct messages, find the other user's name
        if chat.type == "direct":
            members = get_chat_members(db, chat.id)
            for member in members:
                if member.user_id != user_id:
                    other_user = get_user(db, member.user_id)
                    if other_user:
                        chat_dict["other_user_name"] = other_user.username
                    break
        
        enriched_chats.append(chat_dict)
    
    # Sort chats by most recent message at the top
    def sort_key(c):
        last_msg = c.get("last_message_at") or c.get("created_at") or ""
        # Convert ISO string to comparable value (newer = larger)
        timestamp = last_msg.replace("T", " ").replace("Z", "").replace("+00:00", "") if last_msg else ""
        return timestamp
    
    enriched_chats.sort(key=sort_key, reverse=True)  # Reverse=True: newest first
    
    return enriched_chats

@api_router.post(
    "/chats/dm",
    response_model=ChatOut,
    summary="Create direct message",
    description="""
    Create a new direct message chat between two users.
    
    **Request Body:**
    - `user1_id`: ID of the first user
    - `user2_id`: ID of the second user
    
    **Response:**
    - Returns the chat object (existing if DM already exists, or newly created)
    
    **Behavior:**
    - If a direct message chat already exists between these two users, returns the existing chat
    - Otherwise, creates a new direct message chat and adds both users as members
    - The chat type is set to "direct"
    """,
    tags=["Chats"]
)
def create_dm(dm: DMCreate, db: Session = Depends(get_db)):
    # #region agent log
    import json
    import time
    log_data = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "I",
        "location": "start_backend.py:571",
        "message": "create_dm called",
        "data": {
            "user1_id": dm.user1_id,
            "user2_id": dm.user2_id
        },
        "timestamp": int(time.time() * 1000)
    }
    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_data) + '\n')
    # #endregion
    
    # Check if DM already exists between these two users
    from crud import find_existing_dm
    existing_chat = find_existing_dm(db, dm.user1_id, dm.user2_id)
    
    # #region agent log
    log_data = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "I",
        "location": "start_backend.py:585",
        "message": "DM existence check result",
        "data": {
            "user1_id": dm.user1_id,
            "user2_id": dm.user2_id,
            "existing_chat_id": existing_chat.id if existing_chat else None,
            "will_create_new": existing_chat is None
        },
        "timestamp": int(time.time() * 1000)
    }
    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_data) + '\n')
    # #endregion
    
    if existing_chat:
        # Return existing chat instead of creating a new one
        return existing_chat
    
    # Create new DM if it doesn't exist
    chat = create_chat(db, "direct", None)
    add_member_to_chat(db, chat.id, dm.user1_id)
    add_member_to_chat(db, chat.id, dm.user2_id)
    
    # #region agent log
    log_data = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "I",
        "location": "start_backend.py:602",
        "message": "New DM created",
        "data": {
            "user1_id": dm.user1_id,
            "user2_id": dm.user2_id,
            "new_chat_id": chat.id
        },
        "timestamp": int(time.time() * 1000)
    }
    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_data) + '\n')
    # #endregion
    
    return chat

@api_router.post(
    "/chats/group",
    response_model=ChatOut,
    summary="Create group chat",
    description="""
    Create a new group chat with a title and initial members.
    
    **Request Body:**
    - `title`: Group chat title (1-128 characters)
    - `member_ids`: List of user IDs to add to the group (minimum 1 member)
    
    **Response:**
    - Returns the newly created `ChatOut` object
    
    **Note:**
    - All specified members are automatically added to the chat
    - The chat type is set to "group"
    """,
    tags=["Chats"]
)
def create_group(group_data: GroupChatCreate, db: Session = Depends(get_db)):
    # Create the group chat
    chat_obj = create_chat(db, "group", group_data.title)
    
    # Add all members to the chat
    for user_id in group_data.member_ids:
        add_member_to_chat(db, chat_obj.id, user_id)
    
    return chat_obj

@api_router.get(
    "/chats/{chat_id}",
    response_model=ChatOut,
    summary="Get chat by ID",
    description="""
    Get details of a specific chat by its ID.
    
    **Path Parameters:**
    - `chat_id`: ID of the chat to retrieve
    
    **Response:**
    - Returns `ChatOut` object with chat details including:
      - Chat type (direct or group)
      - Title (for group chats)
      - Creation timestamp
      - Other user name (for direct messages)
      - Unread message count
    """,
    tags=["Chats"]
)
def get_chat_by_id(chat_id: int, db: Session = Depends(get_db)):
    chat = get_chat(db, chat_id)  # Fixed: use get_chat instead of create_chat
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


# -------------------------------
# CHAT MEMBERS (Show participants in a chat)
# -------------------------------
@api_router.get(
    "/chats/{chat_id}/members",
    summary="Get chat members",
    description="""
    Get all members of a specific chat with their user information.
    
    **Path Parameters:**
    - `chat_id`: ID of the chat
    
    **Response:**
    - Returns a list of chat members with:
      - User ID and username
      - Last seen timestamp
      - Active chat ID
      - Chat membership details
    
    **Errors:**
    - `404`: Chat not found
    """,
    tags=["Chats"]
)
def get_members(chat_id: int, db: Session = Depends(get_db)):
    # Check if chat exists
    chat = get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Return members with user information
    return get_chat_members_with_users(db, chat_id)

@api_router.post(
    "/chats/{chat_id}/members",
    response_model=ChatMemberWithUser,
    summary="Add member to chat",
    description="""
    Add a user as a member to a group chat.
    
    **Path Parameters:**
    - `chat_id`: ID of the group chat
    
    **Request Body:**
    - `user_id`: ID of the user to add to the chat
    
    **Response:**
    - Returns `ChatMemberWithUser` object with member and user details
    
    **Behavior:**
    - Creates a system message indicating the user was added
    - Broadcasts notification to the added user via WebSocket
    - Triggers frontend chat list refresh for the added user
    
    **Errors:**
    - `404`: Chat or user not found
    - `400`: Can only add members to group chats
    """,
    tags=["Chats"]
)
def add_member(
    chat_id: int, 
    member_request: AddMemberRequest, 
    background_tasks: BackgroundTasks,
    performed_by_user_id: int = Query(..., description="ID of the user performing the action"),
    db: Session = Depends(get_db)
):
    # Check if chat exists
    chat = get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Only allow adding members to group chats
    if chat.type != "group":
        raise HTTPException(status_code=400, detail="Can only add members to group chats")
    
    # Check if user exists
    user = get_user(db, member_request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add member to chat
    member = add_member_to_chat(db, chat_id, member_request.user_id)
    
    # Create a system message indicating the user was added
    try:
        added_user = get_user(db, member_request.user_id)
        added_username = added_user.username if added_user else f"User {member_request.user_id}"
        
        # Get the username of the user who performed the action
        performed_by_user = get_user(db, performed_by_user_id)
        performed_by_username = performed_by_user.username if performed_by_user else f"User {performed_by_user_id}"
        
        # Create a system message
        system_message = create_message(
            db=db,
            chat_id=chat_id,
            sender_id=None,  # System message
            msg_type="system",
            text=f"{added_username} was added to the group by {performed_by_username}"
        )
        
        # Broadcast the system message to all chat members
        broadcast_data = json.dumps({
            "type": "message.new",
            "chat_id": chat_id,
            "message": {
                "id": system_message.id,
                "chat_id": chat_id,
                "sender_id": None,
                "sender_username": None,
                "type": "system",
                "text": system_message.text,
                "content": system_message.text,
                "created_at": system_message.created_at.isoformat() if system_message.created_at else None,
                "timestamp": system_message.created_at.isoformat() if system_message.created_at else None,
                "read_by": [],
                "read_count": 0,
                "status": None
            }
        })
        
        # Broadcast in background
        async def broadcast_message():
            def get_members_for_broadcast(chat_id):
                return get_chat_members(db, chat_id)
            await manager.broadcast(chat_id, broadcast_data, get_members_for_broadcast)
        
        background_tasks.add_task(broadcast_message)
    except Exception as e:
        ws_logger.warning(f"Failed to create system message for member addition: {e}")
        # Rollback the session to clear any pending transaction state
        db.rollback()
    
    # Notify the added user via WebSocket that they've been added to a group chat
    # This will trigger their frontend to reload the chat list
    async def send_notification():
        try:
            # Get chat details for the notification
            chat_title = chat.title or f"Group Chat {chat_id}"
            
            # Send notification to the added user
            notification_data = json.dumps({
                "type": "chat.member.added",
                "chat_id": chat_id,
                "chat_title": chat_title,
                "chat_type": chat.type
            })
            
            # Use the connection manager's send_to_user method
            success = await manager.send_to_user(member_request.user_id, notification_data)
            if success:
                ws_logger.info(f"Notified user {member_request.user_id} about being added to chat {chat_id}")
            else:
                ws_logger.debug(f"User {member_request.user_id} not connected via WebSocket, cannot send notification")
        except Exception as e:
            # Don't fail if notification fails
            ws_logger.warning(f"Could not send notification to user {member_request.user_id}: {e}")
    
    # Schedule the notification as a background task
    background_tasks.add_task(send_notification)
    
    # Return member with user information
    return ChatMemberWithUser(
        chat_id=member.chat_id,
        user_id=member.user_id,
        username=user.username,
        last_seen_at=member.last_seen_at,
        active_chat_id=member.active_chat_id
    )

@api_router.delete(
    "/chats/{chat_id}/members/{user_id}",
    response_model=MessageResponse,
    summary="Remove member from chat",
    description="""
    Remove a user from a group chat.
    
    **Path Parameters:**
    - `chat_id`: ID of the group chat
    - `user_id`: ID of the user to remove
    
    **Response:**
    - Returns success message
    
    **Behavior:**
    - Creates a system message indicating the user was removed
    - Broadcasts the system message to all remaining chat members
    
    **Errors:**
    - `404`: Chat, user, or member not found
    - `400`: Can only remove members from group chats
    """,
    tags=["Chats"]
)
def remove_member(
    chat_id: int, 
    user_id: int, 
    background_tasks: BackgroundTasks,
    performed_by_user_id: int = Query(..., description="ID of the user performing the action"),
    db: Session = Depends(get_db)
):
    # Check if chat exists
    chat = get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Only allow removing members from group chats
    if chat.type != "group":
        raise HTTPException(status_code=400, detail="Can only remove members from group chats")
    
    # Check if user exists
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove member from chat
    success = remove_member_from_chat(db, chat_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found in chat")
    
    # Create a system message indicating the user was removed
    try:
        removed_user = get_user(db, user_id)
        removed_username = removed_user.username if removed_user else f"User {user_id}"
        
        # Get the username of the user who performed the action
        performed_by_user = get_user(db, performed_by_user_id)
        performed_by_username = performed_by_user.username if performed_by_user else f"User {performed_by_user_id}"
        
        # Create a system message
        system_message = create_message(
            db=db,
            chat_id=chat_id,
            sender_id=None,  # System message
            msg_type="system",
            text=f"{removed_username} was removed from the group by {performed_by_username}"
        )
        
        # Broadcast the system message to all chat members
        broadcast_data = json.dumps({
            "type": "message.new",
            "chat_id": chat_id,
            "message": {
                "id": system_message.id,
                "chat_id": chat_id,
                "sender_id": None,
                "sender_username": None,
                "type": "system",
                "text": system_message.text,
                "content": system_message.text,
                "created_at": system_message.created_at.isoformat() if system_message.created_at else None,
                "timestamp": system_message.created_at.isoformat() if system_message.created_at else None,
                "read_by": [],
                "read_count": 0,
                "status": None
            }
        })
        
        # Broadcast in background
        async def broadcast_message():
            def get_members_for_broadcast(chat_id):
                return get_chat_members(db, chat_id)
            await manager.broadcast(chat_id, broadcast_data, get_members_for_broadcast)
        
        background_tasks.add_task(broadcast_message)
    except Exception as e:
        ws_logger.warning(f"Failed to create system message for member removal: {e}")
        # Rollback the session to clear any pending transaction state
        db.rollback()
    
    return MessageResponse(message="Member removed successfully")


@api_router.delete(
    "/chats/{chat_id}/leave",
    response_model=MessageResponse,
    summary="Leave or delete chat",
    description=""" 
    Remove the current user from a chat (leave group chat or delete direct message).
    
    **Path Parameters:**
    - `chat_id`: ID of the chat to leave/delete
    
    **Query Parameters:**
    - `user_id`: ID of the user leaving the chat
    
    **Response:**
    - Returns success message
    
    **Behavior:**
    - For group chats: Removes the user from the chat and creates a system message
    - For direct messages: Removes the user from the chat (effectively deleting it for that user)
    - Broadcasts the system message to all remaining chat members (for group chats)
    
    **Errors:**
    - `404`: Chat or user not found
    - `400`: User is not a member of this chat
    """,
    tags=["Chats"]
)
def leave_chat(
    chat_id: int,
    user_id: int = Query(..., description="ID of the user leaving the chat"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    # Check if chat exists
    chat = get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check if user exists
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is a member of the chat
    member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=400, detail="User is not a member of this chat")
    
    # Remove member from chat
    success = remove_member_from_chat(db, chat_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove user from chat")
    
    # Create a system message for group chats
    if chat.type == "group":
        try:
            removed_username = user.username if user else f"User {user_id}"
            
            # Create a system message
            system_message = create_message(
                db=db,
                chat_id=chat_id,
                sender_id=None,  # System message
                msg_type="system",
                text=f"{removed_username} left the group"
            )
            
            # Broadcast the system message to all chat members
            broadcast_data = json.dumps({
                "type": "message.new",
                "chat_id": chat_id,
                "message": {
                    "id": system_message.id,
                    "chat_id": chat_id,
                    "sender_id": None,
                    "sender_username": None,
                    "type": "system",
                    "text": system_message.text,
                    "content": system_message.text,
                    "created_at": system_message.created_at.isoformat() if system_message.created_at else None,
                    "timestamp": system_message.created_at.isoformat() if system_message.created_at else None,
                    "read_by": [],
                    "read_count": 0,
                    "status": None
                }
            })
            
            # Broadcast in background
            async def broadcast_message():
                def get_members_for_broadcast(chat_id):
                    return get_chat_members(db, chat_id)
                await manager.broadcast(chat_id, broadcast_data, get_members_for_broadcast)
            
            if background_tasks:
                background_tasks.add_task(broadcast_message)
        except Exception as e:
            ws_logger.warning(f"Failed to create system message for chat leave: {e}")
            # Rollback the session to clear any pending transaction state
            db.rollback()
    
    return MessageResponse(message="Chat left successfully")


# -------------------------------
# MESSAGES
# -------------------------------
@api_router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageOut,
    summary="Send message",
    description="""
    Send a message to a chat via REST API.
    
    **Path Parameters:**
    - `chat_id`: ID of the chat to send the message to
    
    **Request Body:**
    - `chat_id`: Chat ID (must match path parameter)
    - `sender_id`: Sender's user ID
    - `type`: Message type - `text` or `media`
    - `text`: Message text content (required for text messages)
    - `media_url`: Media URL (required for media messages)
    
    **Response:**
    - Returns `MessageOut` object with message details
    
    **Note:**
    - For real-time messaging, use WebSocket endpoint `/api/ws` with `message.send` event
    - This REST endpoint is useful for server-side message creation or testing
    """,
    tags=["Messages"]
)
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    message = create_message(
        db,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        msg_type=msg.type.value,
        text=msg.text,
        media_url=msg.media_url
    )
    api_logger.info(f"Message sent: chat_id={msg.chat_id}, sender_id={msg.sender_id}, type={msg.type.value}")
    return message

@api_router.get(
    "/chats/{chat_id}/messages",
    summary="Get chat messages",
    description="""
    Get all messages for a specific chat with read status information.
    
    **Path Parameters:**
    - `chat_id`: ID of the chat
    
    **Query Parameters:**
    - `user_id`: User ID (optional) - If provided, includes read status for this user
    
    **Response:**
    - Returns a list of enriched message objects with:
      - Message content (text or media_url)
      - Sender information
      - Read status (if user_id provided)
      - Read count and list of users who have read the message
      - Timestamps
    
    **Message Status:**
    - `sent`: Message sent but not read by anyone
    - `read`: Message has been read (by at least one recipient for sent messages, or by current user for received messages)
    - `unread`: Message not yet read by current user
    """,
    tags=["Messages"]
)
def get_chat_messages(
    chat_id: int,
    user_id: int = Query(None, description="User ID to get read status for"),
    db: Session = Depends(get_db)
):
    messages = get_messages_for_chat(db, chat_id)
    
    # Get all chat members to check read status
    members = get_chat_members(db, chat_id)
    member_ids = [m.user_id for m in members]
    
    # Enrich messages with sender_username, content field, and read status
    enriched_messages = []
    for msg in messages:
        sender = get_user(db, msg.sender_id)
        
        # Get read status for this message (all users who have read it)
        read_by = get_read_statuses_for_message(db, msg.id)
        # Remove sender from read_by (sender doesn't count as "read")
        read_by = [uid for uid in read_by if uid != msg.sender_id]
        
        # Determine status for current user (if provided)
        user_read_status = None
        if user_id:
            if user_id == msg.sender_id:
                # For own messages, show if read by others
                user_read_status = "read" if len(read_by) > 0 else "sent"
            else:
                # For received messages, show if read by current user
                status = get_message_status(db, msg.id, user_id)
                user_read_status = "read" if (status and status.read_at) else "unread"
        
        message_dict = {
            "id": msg.id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "sender_username": sender.username if sender else None,
            "type": msg.type,
            "text": msg.text,
            "media_url": msg.media_url,
            "content": msg.text if msg.type == "text" else msg.media_url,
            "created_at": msg.created_at,
            "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            "read_by": read_by,  # List of user IDs who have read this message
            "read_count": len(read_by),  # Number of users who have read this message
            "status": user_read_status  # Status for current user (if user_id provided)
        }
        enriched_messages.append(message_dict)
    
    return enriched_messages


# -------------------------------
# MEDIA UPLOAD
# -------------------------------
@api_router.post(
    "/media/upload",
    response_model=MediaUploadResponse,
    summary="Upload media",
    description="""
    Upload a media file (image or GIF) for use in chat messages.
    
    **Request:**
    - `file`: Media file to upload (multipart/form-data)
      - Supported formats: Images (JPG, PNG, GIF, etc.)
      - File size limits may apply
    
    **Response:**
    - `media_url`: Full URL to access the uploaded media file
    - `filename`: Unique filename of the uploaded file
    
    **Usage:**
    1. Upload media file using this endpoint
    2. Use the returned `media_url` in message creation (via REST or WebSocket)
    3. Set message type to `media` when sending
    
    **Note:**
    - Files are stored with unique UUID-based filenames
    - Media files are accessible via `/api/media/{filename}` endpoint
    """,
    tags=["Media"]
)
def upload_media(request: Request, file: UploadFile = File(...)):
    # #region agent log
    import json as json_lib
    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"start_backend.py:633","message":"upload_media called","data":{"filename":file.filename,"content_type":file.content_type},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    # #endregion
    
    # Generate unique filename
    import uuid
    file_ext = Path(file.filename).suffix if file.filename else '.jpg'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = MEDIA_DIR / unique_filename
    
    # Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        # #region agent log
        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"start_backend.py:648","message":"File saved to disk","data":{"filePath":str(file_path),"fileSize":len(content)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
    except Exception as e:
        # #region agent log
        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"start_backend.py:651","message":"File save error","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Generate media URL (absolute URL if request available, otherwise relative)
    if request:
        base_url = str(request.base_url).rstrip('/')
        media_url = f"{base_url}/api/media/{unique_filename}"
    else:
        # Fallback: use config API URL or relative path
        api_url = os.getenv("API_URL", "http://localhost:8000")
        media_url = f"{api_url}/api/media/{unique_filename}"
    result = {"media_url": media_url, "filename": unique_filename}
    # #region agent log
    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"start_backend.py:665","message":"upload_media returning","data":{"result":result,"hasMediaUrl":"media_url" in result,"mediaUrl":media_url},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    # #endregion
    return result


# -------------------------------
# ADMIN
# -------------------------------
ADMIN_PIN = "0000"

def verify_admin_pin(pin: str) -> bool:
    """Verify admin PIN."""
    return pin == ADMIN_PIN

@api_router.post(
    "/admin/auth",
    response_model=AdminAuthResponse,
    summary="Admin authentication",
    description="""
    Authenticate as admin using PIN to get an admin token.
    
    **Request Body:**
    - `pin`: Admin PIN (default: 0000)
    
    **Response:**
    - `admin_token`: Admin authentication token
    - `message`: Authentication confirmation message
    
    **Note:**
    - Admin token can be used for admin operations
    - Default admin PIN is `0000` (change in production!)
    """,
    tags=["Admin"]
)
def admin_auth(auth_data: AdminAuth, db: Session = Depends(get_db)):
    """Authenticate as admin using PIN."""
    if not verify_admin_pin(auth_data.pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    # Generate admin token
    admin_token = secrets.token_urlsafe(32)
    return AdminAuthResponse(admin_token=admin_token, message="Admin authentication successful")

@api_router.get(
    "/admin/users",
    response_model=list[UserOut],
    summary="List all users (Admin)",
    description="List all users in the system. Requires admin PIN (default: 0000).",
    tags=["Admin"]
)
def list_users(
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """List all users in the system. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    return list_all_users(db)

@api_router.get(
    "/admin/users/{user_id}",
    response_model=UserOut,
    summary="Get user by ID (Admin)",
    description="""
    Get detailed information about a specific user by their ID.
    
    **Query Parameters:**
    - `admin_pin`: Admin PIN (default: 0000)
    
    **Path Parameters:**
    - `user_id`: ID of the user to retrieve
    
    **Response:**
    - Returns `UserOut` object with user details
    
    **Errors:**
    - `401`: Invalid admin PIN
    - `404`: User not found
    """,
    tags=["Admin"]
)
def get_user_admin(
    user_id: int,
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """Get user details by ID. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.put(
    "/admin/users/{user_id}",
    response_model=UserOut,
    summary="Update user (Admin)",
    description="""
    Update user information (username and/or PIN).
    
    **Query Parameters:**
    - `admin_pin`: Admin PIN (default: 0000)
    
    **Path Parameters:**
    - `user_id`: ID of the user to update
    
    **Request Body:**
    - `username`: New username (optional, 3-64 characters)
    - `pin`: New PIN (optional, 4-8 digits, numbers only)
    
    **Response:**
    - Returns updated `UserOut` object
    
    **Errors:**
    - `401`: Invalid admin PIN
    - `404`: User not found
    - `400`: Username already exists
    """,
    tags=["Admin"]
)
def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """Update user information. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if username already exists (if changing username)
    if user_update.username and user_update.username != user.username:
        existing = get_user_by_username(db, user_update.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash new PIN if provided
    pin_hash = None
    if user_update.pin:
        pin_hash = bcrypt.hashpw(user_update.pin.encode(), bcrypt.gensalt()).decode()
    
    updated_user = update_user(
        db,
        user_id,
        username=user_update.username,
        pin_hash=pin_hash
    )
    return updated_user

@api_router.delete(
    "/admin/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete user (Admin)",
    description="""
    Delete a user from the system. This action cannot be undone.
    
    **Query Parameters:**
    - `admin_pin`: Admin PIN (default: 0000)
    
    **Path Parameters:**
    - `user_id`: ID of the user to delete
    
    **Response:**
    - Returns success message
    
    **Errors:**
    - `401`: Invalid admin PIN
    - `404`: User not found
    """,
    tags=["Admin"]
)
def delete_user_admin(
    user_id: int,
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """Delete a user from the system. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return MessageResponse(message="User deleted successfully")

@api_router.post(
    "/admin/users",
    response_model=UserOut,
    summary="Create user (Admin)",
    description="""
    Create a new user account via admin interface.
    
    **Query Parameters:**
    - `admin_pin`: Admin PIN (default: 0000)
    
    **Request Body:**
    - `username`: Username (3-64 characters)
    - `pin`: PIN (4-8 digits, numbers only)
    
    **Response:**
    - Returns the newly created `UserOut` object
    
    **Errors:**
    - `401`: Invalid admin PIN
    - `400`: Username already exists
    """,
    tags=["Admin"]
)
def create_user_admin(
    user: UserCreate,
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """Create a new user. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    existing = get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    pin_hash = bcrypt.hashpw(user.pin.encode(), bcrypt.gensalt()).decode()
    new_user = create_user(db, user.username, pin_hash)
    return new_user

@api_router.post(
    "/admin/reset-database",
    response_model=ResetDatabaseResponse,
    summary="Reset database (Admin)",
    description="""
    Drop all tables and recreate them. ⚠️ **DESTRUCTIVE OPERATION** ⚠️
    
    This will delete ALL data in the database including:
    - All users
    - All chats
    - All messages
    - All media references
    
    **Query Parameters:**
    - `admin_pin`: Admin PIN (default: 0000)
    
    **Response:**
    - Returns confirmation message and status
    
    **Warning:**
    - This operation cannot be undone
    - Server will automatically restart after reset
    - All active sessions will be invalidated
    
    **Errors:**
    - `401`: Invalid admin PIN
    - `500`: Error during database reset
    """,
    tags=["Admin"]
)
def reset_database(
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """Drop all tables and recreate them. Requires admin PIN. Server will restart."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    try:
        # Close the current database session
        db.close()
        
        # Dispose of all engine connections to ensure clean state
        engine.dispose()
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        
        # Schedule server restart after a short delay to allow response to be sent
        def restart_server():
            import time
            time.sleep(1)  # Give time for response to be sent
            os._exit(0)  # Exit the process, start.py will restart it
        
        threading.Thread(target=restart_server, daemon=True).start()
        
        return ResetDatabaseResponse(
            message="Database reset successfully. Server will restart shortly.",
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting database: {str(e)}")


# -------------------------------
# ROOT
# -------------------------------
@app.get(
    "/",
    summary="Root endpoint",
    description="Health check endpoint. Returns API status.",
    tags=["Root"]
)
def read_root():
    """Root endpoint for health check."""
    return {"message": "Wazzap Backend Running!"}

# Include API router
app.include_router(api_router)

# Mount static files for media
app.mount("/api/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# -------------------------------
# WEBSOCKET
# -------------------------------

from fastapi import WebSocket, WebSocketDisconnect
import json


@app.websocket(
    "/api/ws",
    name="WebSocket Chat Connection"
)
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token obtained from /api/auth/login"),
    session_id: str = Query(..., description="Session ID obtained from /api/auth/login")
):
    # Validate session - reject if session doesn't exist (e.g., after server restart)
    # Use 1001 (Going Away) for server restarts - this allows frontend to reconnect
    # Use 1008 (Policy Violation) only for explicitly invalid sessions
    if session_id not in active_sessions:
        ws_logger.warning(f"WebSocket connection rejected: session not found (likely server restart), session_id={session_id}")
        await websocket.close(code=1001, reason="Session expired due to server restart. Please reconnect.")
        return
    
    session = active_sessions[session_id]
    if session["jwt"] != token:
        ws_logger.warning(f"WebSocket connection rejected: invalid token for session_id={session_id}")
        await websocket.close(code=1008, reason="Invalid token. Please log in again.")
        return
    
    await websocket.accept()
    
    # Create database session for this WebSocket connection
    db = SessionLocal()
    
    try:
        # Track user connection
        user_id = session['user_id']
        
        # Send session ready confirmation
        await websocket.send_text(json.dumps({
            "type": "session.ready",
            "session_id": session_id
        }))
        ws_logger.info(f"WebSocket connected: session_id={session_id}, user_id={user_id}")
        
        # #region agent log
        import inspect
        import os
        import connection_manager
        connect_sig = inspect.signature(manager.connect)
        connect_file = inspect.getfile(manager.connect)
        connect_module_file = inspect.getfile(connection_manager.ConnectionManager)
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A",
            "location": "start_backend.py:928",
            "message": "Before manager.connect call - checking method signature",
            "data": {
                "method_signature": str(connect_sig),
                "method_file": connect_file,
                "module_file": connect_module_file,
                "args_count": len(connect_sig.parameters),
                "param_names": list(connect_sig.parameters.keys()),
                "user_id": user_id,
                "chat_id": 0,
                "manager_type": str(type(manager)),
                "has_user_id_param": "user_id" in connect_sig.parameters
            },
            "timestamp": int(__import__('time').time() * 1000)
        }
        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(__import__('json').dumps(log_data) + '\n')
        # #endregion
        
        # Register user connection (connect to a dummy chat_id 0 to track the user)
        try:
            await manager.connect(websocket, 0, user_id)
        except TypeError as e:
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "start_backend.py:928",
                "message": "TypeError caught in manager.connect",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "args_passed": 3,
                    "user_id": user_id
                },
                "timestamp": int(__import__('time').time() * 1000)
            }
            with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(__import__('json').dumps(log_data) + '\n')
            # #endregion
            raise
        
        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                # Normal disconnection - let it propagate to outer handler
                raise
            except Exception as e:
                # Log other errors but don't break - continue listening
                ws_logger.error(f"Error receiving WebSocket message: {e}", exc_info=True)
                # Don't break on other errors - continue the loop to keep connection alive
                continue
            
            # Parse incoming JSON
            try:
                payload = json.loads(data)
                msg_type = payload.get("type")
                
                # Handle different message types
                if msg_type == "chat.open":
                    chat_id = payload.get("chat_id")
                    user_id = payload.get("user_id")
                    # Validate user is member of chat
                    chat = await run_in_threadpool(get_chat, db, chat_id)
                    members = await run_in_threadpool(get_chat_members, db, chat_id)
                    member_ids = [m.user_id for m in members]
                    
                    if not chat or user_id not in member_ids:
                        ws_logger.warning(f"Chat open failed: chat_id={chat_id}, user_id={user_id} (not found or not a member)")
                        await websocket.send_text(json.dumps({"error": "Chat not found or not a member"}))
                        continue
                    
                    await manager.connect(websocket, chat_id, user_id)
                    ws_logger.info(f"Chat opened: chat_id={chat_id}, user_id={user_id}")
                    
                elif msg_type == "message.send":
                    chat_id = payload.get("chat_id")
                    sender_id = payload.get("sender_id")
                    content = payload.get("content")
                    media_url = payload.get("media_url")
                    msg_type_content = payload.get("msg_type", "text")
                    
                    try:
                        # Create message in database
                        message = await run_in_threadpool(
                            create_message,
                            db,
                            chat_id=chat_id,
                            sender_id=sender_id,
                            msg_type=msg_type_content,
                            text=content if msg_type_content == "text" else None,
                            media_url=media_url if msg_type_content == "media" else None
                        )
                        
                        # Get sender username for broadcast
                        sender = await run_in_threadpool(get_user, db, sender_id)
                        sender_username = sender.username if sender else None
                        
                        # Get initial read status (empty for new messages)
                        read_by = []
                        
                        # Broadcast to chat members
                        broadcast_data = {
                            "type": "message.new",
                            "chat_id": chat_id,
                            "message": {
                                "id": message.id,
                                "chat_id": chat_id,
                                "sender_id": sender_id,
                                "sender_username": sender_username,
                                "type": msg_type_content,
                                "text": content,
                                "media_url": media_url,
                                "content": content if msg_type_content == "text" else media_url,
                                "created_at": message.created_at.isoformat() if hasattr(message, 'created_at') else None,
                                "timestamp": message.created_at.isoformat() if hasattr(message, 'created_at') else None,
                                "read_by": read_by,
                                "read_count": 0,
                                "status": None  # Will be set by frontend based on user
                            }
                        }
                        # Broadcast to all chat members (including those who haven't opened the chat)
                        def get_members_for_broadcast(chat_id):
                            return get_chat_members(db, chat_id)
                        await manager.broadcast(chat_id, json.dumps(broadcast_data), get_members_for_broadcast)
                        preview = content[:30] + "..." if content and len(content) > 30 else content or "[media]"
                        ws_logger.info(f"Message sent via WS: chat_id={chat_id}, sender_id={sender_id}, preview='{preview}'")
                    except Exception as e:
                        ws_logger.error(f"Error processing message.send: {e}", exc_info=True)
                        try:
                            await websocket.send_text(json.dumps({"error": "Failed to send message"}))
                        except Exception:
                            pass
                    
                elif msg_type == "message.read":
                    chat_id = payload.get("chat_id")
                    message_id = payload.get("message_id")
                    
                    # #region agent log
                    import json as json_module
                    import time
                    log_data = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "K",
                        "location": "start_backend.py:1230",
                        "message": "message.read handler entry",
                        "data": {
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "user_id": user_id,
                            "chat_id_is_none": chat_id is None,
                            "message_id_is_none": message_id is None
                        },
                        "timestamp": int(time.time() * 1000)
                    }
                    with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps(log_data) + '\n')
                    # #endregion
                    
                    # Validate required parameters
                    if not chat_id or not message_id:
                        ws_logger.warning(f"message.read missing required parameters: chat_id={chat_id}, message_id={message_id}")
                        await websocket.send_text(json.dumps({
                            "error": "Missing chat_id or message_id",
                            "type": "error"
                        }))
                        continue
                    
                    # Update last_seen_at in database
                    await run_in_threadpool(update_last_seen, db, chat_id, user_id, message_id)
                    # Mark messages as read in MessageStatus table
                    marked_message_ids = await run_in_threadpool(
                        mark_messages_as_read, db, chat_id, user_id, message_id
                    )
                    
                    # Broadcast read status updates to all chat members
                    # Get all chat members
                    members = await run_in_threadpool(get_chat_members, db, chat_id)
                    
                    # For each marked message, get read status and broadcast update
                    for marked_msg_id in marked_message_ids:
                        # Get all read statuses for this message in one query
                        # This returns a list of user IDs who have read the message
                        read_by_all = await run_in_threadpool(get_read_statuses_for_message, db, marked_msg_id)
                        # Remove the current user from read_by (they just read it, but we show who else has read it)
                        read_by = [uid for uid in read_by_all if uid != user_id]
                        
                        # #region agent log
                        log_data = {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "L",
                            "location": "start_backend.py:1277",
                            "message": "Broadcasting read status update",
                            "data": {
                                "chat_id": chat_id,
                                "message_id": marked_msg_id,
                                "read_by_all": read_by_all,
                                "read_by": read_by,
                                "read_count": len(read_by_all),
                                "read_by_user_id": user_id,
                                "marked_message_ids_count": len(marked_message_ids)
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json_module.dumps(log_data) + '\n')
                        # #endregion
                        
                        # Broadcast to all chat members
                        broadcast_data = {
                            "type": "message.read.update",
                            "chat_id": chat_id,
                            "message_id": marked_msg_id,
                            "read_by": read_by,
                            "read_count": len(read_by_all),  # Total count including current user
                            "read_by_user_id": user_id
                        }
                        def get_members_for_broadcast(chat_id):
                            return get_chat_members(db, chat_id)
                        await manager.broadcast(chat_id, json.dumps(broadcast_data), get_members_for_broadcast)
                        
                        # #region agent log
                        log_data = {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "L",
                            "location": "start_backend.py:1300",
                            "message": "Read status broadcast sent",
                            "data": {
                                "chat_id": chat_id,
                                "message_id": marked_msg_id,
                                "broadcast_data": broadcast_data
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json_module.dumps(log_data) + '\n')
                        # #endregion
                    
                    # Also send confirmation to the sender
                    await websocket.send_text(json.dumps({
                        "type": "message.status",
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "status": "read"
                    }))
                    
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue
                
    except WebSocketDisconnect:
        # Disconnect from all chats
        try:
            user_id = session.get('user_id') if 'session' in locals() else None
            await manager.disconnect(websocket, None, user_id)
        except Exception as e:
            ws_logger.error(f"Error disconnecting WebSocket: {e}")
        ws_logger.info(f"WebSocket disconnected: session_id={session_id}")
    except Exception as e:
        ws_logger.error(f"Unexpected error in WebSocket endpoint: {e}", exc_info=True)
        try:
            user_id = session.get('user_id') if 'session' in locals() else None
            await manager.disconnect(websocket, None, user_id)
        except Exception:
            pass
    finally:
        # Close database session
        try:
            db.close()
        except Exception as e:
            ws_logger.error(f"Error closing database session: {e}")

# Legacy WebSocket endpoint for backward compatibility
@app.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint_legacy(websocket: WebSocket, chat_id: int, user_id: int):
    # Create database session for this WebSocket connection
    db = SessionLocal()
    
    try:
        # Offload initial validation to threads
        chat = await run_in_threadpool(get_chat, db, chat_id)
        members = await run_in_threadpool(get_chat_members, db, chat_id)
        member_ids = [m.user_id for m in members]

        if not chat or user_id not in member_ids:
            await websocket.accept()
            if not chat:
                await websocket.send_text(json.dumps({"error": "Chat not found"}))
            else:
                if user_id not in member_ids:
                    await websocket.send_text(json.dumps({"error": "Not a member"}))
                    return

            # Removed unnecessary close() and return
            # await websocket.close()
            return

        await manager.connect(websocket, chat_id)

        while True:
            data = await websocket.receive_text()

            # Parse incoming JSON
            try:
                payload = json.loads(data)
                msg_type = payload.get("type", "text")  # "text" or "media"
                content = payload.get("content", None)
                media_url = payload.get("media_url", None)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            # Allow client to quit
            if msg_type == "control" and content == "quit":
                await manager.disconnect(websocket, chat_id)
                ws_logger.info(f"User {user_id} disconnected from chat {chat_id}")
                break

            # New check: User still member?
            members = await run_in_threadpool(get_chat_members, db, chat_id)
            member_ids = [m.user_id for m in members]
            if user_id not in member_ids:
                await websocket.send_text(json.dumps({"error": "Not a member"}))
                continue

            # Offload DB insertion to a thread
            message = await run_in_threadpool(
                create_message,
                db,
                chat_id=chat_id,
                sender_id=user_id,
                msg_type=msg_type,
                text=content if msg_type == "text" else None,
                media_url=media_url if msg_type == "media" else None
            )

            # Broadcast message to chat members
            broadcast_data = {
                "chat_id": chat_id,
                "sender_id": user_id,
                "type": msg_type,
                "content": content,
                "media_url": media_url,
                "message_id": message.id
            }
            await manager.broadcast(chat_id, json.dumps(broadcast_data))
            preview = content[:30] + "..." if content and len(content) > 30 else content or "[media]"
            ws_logger.info(f"Message sent (legacy WS): chat_id={chat_id}, user_id={user_id}, preview='{preview}'")

    except WebSocketDisconnect:
        await manager.disconnect(websocket, chat_id)
        ws_logger.info(f"User {user_id} disconnected from chat {chat_id}")
    finally:
        # Close database session
        db.close()