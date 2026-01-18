from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
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
    list_chats_for_user
)
from schema import (
    UserCreate, UserOut,
    ChatBase, ChatOut,
    ChatMemberBase, ChatMemberOut,
    MessageCreate, MessageOut,
)
import bcrypt

from connection_manager import ConnectionManager
from starlette.concurrency import run_in_threadpool

manager = ConnectionManager()

app = FastAPI(title="Wazzap Backend")
# -------------------------------
# FOR TESTING PURPOSES
# -------------------------------

class DMCreate(BaseModel):
    user1_id: int
    user2_id: int

# -------------------------------
# AUTH
# -------------------------------
@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    pin_hash = bcrypt.hashpw(user.pin.encode(), bcrypt.gensalt()).decode()
    new_user = create_user(db, user.username, pin_hash)
    return new_user

@app.post("/auth/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(user.pin.encode(), db_user.pin_hash.encode()):
        raise HTTPException(status_code=400, detail="Incorrect PIN")

    return {"message": f"Welcome {db_user.username}!"}

@app.post("/auth/logout")
def logout():
    return {"message": "Logout successful"}


# -------------------------------
# CURRENT USER
# -------------------------------
@app.get("/me", response_model=UserOut)
def get_me(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# -------------------------------
# CHATS
# -------------------------------
@app.get("/chats/me", response_model=list[ChatOut])
def get_my_chats(user_id: int, db: Session = Depends(get_db)):
    return list_chats_for_user(db, user_id)

@app.post("/chats/dm", response_model=ChatOut)
def create_dm(dm: DMCreate, db: Session = Depends(get_db)):
    # Check if DM exists, else create
    chat = create_chat(db, "direct", None)
    add_member_to_chat(db, chat.id, dm.user1_id)
    add_member_to_chat(db, chat.id, dm.user2_id)
    return chat

@app.post("/chats/group", response_model=ChatOut)
def create_group(chat: ChatBase, db: Session = Depends(get_db)):
    chat_obj = create_chat(db, chat.type.value, chat.title)
    return chat_obj

@app.get("/chats/{chat_id}", response_model=ChatOut)
def get_chat_by_id(chat_id: int, db: Session = Depends(get_db)):
    chat = get_chat(db, chat_id)  # Fixed: use get_chat instead of create_chat
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


# -------------------------------
# CHAT MEMBERS (Show participants in a chat)
# -------------------------------
@app.get("/chats/{chat_id}/members", response_model=list[ChatMemberOut])
def get_members(chat_id: int, db: Session = Depends(get_db)):
    return get_chat_members(db, chat_id)  # Fixed: use get_chat_members

@app.post("/chats/{chat_id}/members", response_model=ChatMemberOut)
def add_member(chat_id: int, member: ChatMemberBase, db: Session = Depends(get_db)):
    return add_member_to_chat(db, chat_id, member.user_id)


# -------------------------------
# MESSAGES
# -------------------------------
@app.post("/chats/{chat_id}/messages", response_model=MessageOut)
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

@app.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
def get_chat_messages(chat_id: int, db: Session = Depends(get_db)):
    return get_messages_for_chat(db, chat_id)


# -------------------------------
# MEDIA UPLOAD
# -------------------------------
@app.post("/media/upload")
def upload_media(file: UploadFile = File(...)):
    # TODO: save to disk/cloud
    return {"filename": file.filename}


# -------------------------------
# ROOT
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "Wazzap Backend Running!"}

# -------------------------------
# WEBSOCKET
# -------------------------------

from fastapi import WebSocket, WebSocketDisconnect
import json


@app.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, user_id: int, db: Session = Depends(get_db)):
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

    try:
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
