from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from crud import (
    create_user,
    get_user_by_username,
    create_chat,
    add_member_to_chat,
    create_message,
    get_messages_for_chat,
    list_chats_for_user
)
from schema import UserCreate, UserOut, ChatBase, ChatOut, ChatMemberBase, ChatMemberOut, MessageCreate, MessageOut
import bcrypt

app = FastAPI(title="Wazzap Backend")

# -------------------------------
# USER ENDPOINTS
# -------------------------------

@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    pin_hash = bcrypt.hashpw(user.pin.encode(), bcrypt.gensalt()).decode()
    new_user = create_user(db, user.username, pin_hash)
    return new_user


@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(user.pin.encode(), db_user.pin_hash.encode()):
        raise HTTPException(status_code=400, detail="Incorrect PIN")

    return {"message": f"Welcome {db_user.username}!"}

# -------------------------------
# CHAT ENDPOINTS
# -------------------------------

@app.post("/chats", response_model=ChatOut)
def create_new_chat(chat: ChatBase, db: Session = Depends(get_db)):
    new_chat = create_chat(db, chat.type.value, chat.title)
    return new_chat


@app.post("/chats/{chat_id}/members", response_model=ChatMemberOut)
def add_member(chat_id: int, member: ChatMemberBase, db: Session = Depends(get_db)):
    new_member = add_member_to_chat(db, chat_id, member.user_id)
    return new_member


@app.get("/users/{user_id}/chats", response_model=list[ChatOut])
def get_user_chats(user_id: int, db: Session = Depends(get_db)):
    return list_chats_for_user(db, user_id)

# -------------------------------
# MESSAGE ENDPOINTS
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
# ROOT
# -------------------------------

@app.get("/")
def read_root():
    return {"message": "Wazzap Backend Running!"}
