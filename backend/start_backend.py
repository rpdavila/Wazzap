from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
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
