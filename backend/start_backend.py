from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, engine, Base, SessionLocal
from crud import (
    create_user,
    get_user_by_username,
    get_user,
    create_chat,
    get_chat,
    add_member_to_chat,
    get_chat_members,
    create_message,
    get_messages_for_chat,
    list_chats_for_user,
    list_all_users,
    update_user,
    delete_user
)
from schema import (
    UserCreate, UserOut,
    ChatBase, ChatOut,
    ChatMemberBase, ChatMemberOut,
    MessageCreate, MessageOut,
    AdminAuth, UserUpdate
)
import bcrypt
import secrets
import os
from dotenv import load_dotenv

from connection_manager import ConnectionManager
from starlette.concurrency import run_in_threadpool

load_dotenv()

manager = ConnectionManager()

app = FastAPI(
    title="Wazzap Backend API",
    description="""
    Wazzap - Real-time Chat Application Backend API
    
    ## Features
    - User authentication with PIN
    - Direct and group chats
    - Real-time messaging via WebSocket
    - Media upload support
    
    ## WebSocket API
    
    The WebSocket endpoint is available at `/api/ws` with the following query parameters:
    - `token`: JWT token (obtained from `/api/auth/login`)
    - `session_id`: Session ID (obtained from `/api/auth/login`)
    
    ### WebSocket Message Types
    
    #### Client → Server:
    - `chat.open`: Open a chat connection
      ```json
      {
        "type": "chat.open",
        "chat_id": 1,
        "user_id": 1
      }
      ```
    
    - `message.send`: Send a message
      ```json
      {
        "type": "message.send",
        "chat_id": 1,
        "sender_id": 1,
        "content": "Hello!",
        "msg_type": "text"
      }
      ```
    
    - `message.read`: Mark message as read
      ```json
      {
        "type": "message.read",
        "chat_id": 1,
        "message_id": 123
      }
      ```
    
    - `ping`: Keep-alive ping
      ```json
      {
        "type": "ping"
      }
      ```
    
    #### Server → Client:
    - `session.ready`: Connection established
      ```json
      {
        "type": "session.ready",
        "session_id": "session-123"
      }
      ```
    
    - `message.new`: New message received
      ```json
      {
        "type": "message.new",
        "chat_id": 1,
        "message": {
          "id": 123,
          "chat_id": 1,
          "sender_id": 1,
          "type": "text",
          "text": "Hello!",
          "created_at": "2024-01-01T12:00:00"
        }
      }
      ```
    
    - `message.status`: Message status update
      ```json
      {
        "type": "message.status",
        "chat_id": 1,
        "message_id": 123,
        "status": "read"
      }
      ```
    
    - `pong`: Response to ping
      ```json
      {
        "type": "pong"
      }
      ```
    
    ## Admin Mode
    
    Admin endpoints require PIN authentication (default: 0000).
    Use the `/api/admin/auth` endpoint to authenticate and get an admin token.
    """,
    version="1.0.0"
)

# Create tables on startup
@app.on_event("startup")
def create_tables():
    """Create all database tables if they don't exist."""
    from models import User, Chat, ChatMember, Message, MessageStatus
    # Import all models to ensure they're registered with Base.metadata
    # This will create all tables defined in models.py if they don't exist
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized (created if they didn't exist)")

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
@api_router.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    pin_hash = bcrypt.hashpw(user.pin.encode(), bcrypt.gensalt()).decode()
    new_user = create_user(db, user.username, pin_hash)
    return new_user

@api_router.post("/auth/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(user.pin.encode(), db_user.pin_hash.encode()):
        raise HTTPException(status_code=400, detail="Incorrect PIN")

    # Generate JWT token (simplified - in production use proper JWT library)
    jwt_token = secrets.token_urlsafe(32)
    session_id = secrets.token_urlsafe(16)
    
    return {
        "jwt": jwt_token,
        "session_id": session_id,
        "username": db_user.username,
        "user_id": db_user.id
    }

@api_router.post("/auth/logout")
def logout():
    return {"message": "Logout successful"}


# -------------------------------
# CURRENT USER
# -------------------------------
@api_router.get("/me", response_model=UserOut)
def get_me(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# -------------------------------
# CHATS
# -------------------------------
@api_router.get("/chats", response_model=list[ChatOut])
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
    
    return list_chats_for_user(db, user_id)

@api_router.get("/chats/me", response_model=list[ChatOut])
def get_my_chats(user_id: int, db: Session = Depends(get_db)):
    return list_chats_for_user(db, user_id)

@api_router.post("/chats/dm", response_model=ChatOut)
def create_dm(dm: DMCreate, db: Session = Depends(get_db)):
    # Check if DM exists, else create
    chat = create_chat(db, "direct", None)
    add_member_to_chat(db, chat.id, dm.user1_id)
    add_member_to_chat(db, chat.id, dm.user2_id)
    return chat

@api_router.post("/chats/group", response_model=ChatOut)
def create_group(chat: ChatBase, db: Session = Depends(get_db)):
    chat_obj = create_chat(db, chat.type.value, chat.title)
    return chat_obj

@api_router.get("/chats/{chat_id}", response_model=ChatOut)
def get_chat_by_id(chat_id: int, db: Session = Depends(get_db)):
    chat = get_chat(db, chat_id)  # Fixed: use get_chat instead of create_chat
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


# -------------------------------
# CHAT MEMBERS (Show participants in a chat)
# -------------------------------
@api_router.get("/chats/{chat_id}/members", response_model=list[ChatMemberOut])
def get_members(chat_id: int, db: Session = Depends(get_db)):
    return get_chat_members(db, chat_id)  # Fixed: use get_chat_members

@api_router.post("/chats/{chat_id}/members", response_model=ChatMemberOut)
def add_member(chat_id: int, member: ChatMemberBase, db: Session = Depends(get_db)):
    return add_member_to_chat(db, chat_id, member.user_id)


# -------------------------------
# MESSAGES
# -------------------------------
@api_router.post("/chats/{chat_id}/messages", response_model=MessageOut)
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    message = create_message(
        db,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        msg_type=msg.type.value,
        text=msg.text,
        media_url=msg.media_url
    )
    return message

@api_router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
def get_chat_messages(chat_id: int, db: Session = Depends(get_db)):
    return get_messages_for_chat(db, chat_id)


# -------------------------------
# MEDIA UPLOAD
# -------------------------------
@api_router.post("/media/upload")
def upload_media(file: UploadFile = File(...)):
    # TODO: save to disk/cloud
    return {"filename": file.filename}


# -------------------------------
# ADMIN
# -------------------------------
ADMIN_PIN = "0000"

def verify_admin_pin(pin: str) -> bool:
    """Verify admin PIN."""
    return pin == ADMIN_PIN

@api_router.post("/admin/auth")
def admin_auth(auth_data: AdminAuth, db: Session = Depends(get_db)):
    """Authenticate as admin using PIN."""
    if not verify_admin_pin(auth_data.pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    # Generate admin token
    admin_token = secrets.token_urlsafe(32)
    return {
        "admin_token": admin_token,
        "message": "Admin authentication successful"
    }

@api_router.get("/admin/users", response_model=list[UserOut])
def list_users(
    admin_pin: str = Query(..., description="Admin PIN"),
    db: Session = Depends(get_db)
):
    """List all users in the system. Requires admin PIN."""
    if not verify_admin_pin(admin_pin):
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    
    return list_all_users(db)

@api_router.get("/admin/users/{user_id}", response_model=UserOut)
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

@api_router.put("/admin/users/{user_id}", response_model=UserOut)
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

@api_router.delete("/admin/users/{user_id}")
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
    
    return {"message": "User deleted successfully"}

@api_router.post("/admin/users", response_model=UserOut)
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


# -------------------------------
# ROOT
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "Wazzap Backend Running!"}

# Include API router
app.include_router(api_router)

# -------------------------------
# WEBSOCKET
# -------------------------------

from fastapi import WebSocket, WebSocketDisconnect
import json


@app.websocket("/api/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token"),
    session_id: str = Query(..., description="Session ID")
):
    # For now, we'll accept the connection and handle chat_id/user_id from messages
    # In production, you'd validate the token and extract user_id from it
    await websocket.accept()
    
    # Create database session for this WebSocket connection
    db = SessionLocal()
    
    try:
        # Send session ready confirmation
        await websocket.send_text(json.dumps({
            "type": "session.ready",
            "session_id": session_id
        }))
        
        while True:
            data = await websocket.receive_text()
            
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
                        await websocket.send_text(json.dumps({"error": "Chat not found or not a member"}))
                        continue
                    
                    await manager.connect(websocket, chat_id)
                    
                elif msg_type == "message.send":
                    chat_id = payload.get("chat_id")
                    sender_id = payload.get("sender_id")
                    content = payload.get("content")
                    media_url = payload.get("media_url")
                    msg_type_content = payload.get("msg_type", "text")
                    
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
                    
                    # Broadcast to chat members
                    broadcast_data = {
                        "type": "message.new",
                        "chat_id": chat_id,
                        "message": {
                            "id": message.id,
                            "chat_id": chat_id,
                            "sender_id": sender_id,
                            "type": msg_type_content,
                            "text": content,
                            "media_url": media_url,
                            "created_at": message.created_at.isoformat() if hasattr(message, 'created_at') else None
                        }
                    }
                    await manager.broadcast(chat_id, json.dumps(broadcast_data))
                    
                elif msg_type == "message.read":
                    chat_id = payload.get("chat_id")
                    message_id = payload.get("message_id")
                    # Handle read receipt
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
        await manager.disconnect(websocket, None)
        print(f"WebSocket disconnected: session {session_id}")
    finally:
        # Close database session
        db.close()

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
                print(f"User {user_id} disconnected from chat {chat_id}")
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

    except WebSocketDisconnect:
        await manager.disconnect(websocket, chat_id)
        print(f"User {user_id} disconnected from chat {chat_id}")
    finally:
        # Close database session
        db.close()