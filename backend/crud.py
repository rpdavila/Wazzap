from sqlalchemy.orm import Session
from models import User, Chat, ChatMember, Message, MessageStatus
from datetime import datetime, UTC
import uuid

# -------------------------------
# USER CRUD
# -------------------------------

def create_user(db: Session, username: str, pin_hash: str) -> User:
    user = User(username=username, pin_hash=pin_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str) -> type[User] | None:
    return db.query(User).filter(User.username == username).first()

def get_user(db: Session, user_id: int) -> type[User] | None:
    return db.query(User).filter(User.id == user_id).first()

# -------------------------------
# CHAT CRUD
# -------------------------------

def create_chat(db: Session, chat_type: str, title: str = None) -> Chat:
    chat = Chat(type=chat_type, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

def get_chat(db: Session, chat_id: int) -> type[Chat] | None:
    return db.query(Chat).filter(Chat.id == chat_id).first()

def list_chats_for_user(db: Session, user_id: int) -> list[type[Chat]]:
    return db.query(Chat).join(ChatMember).filter(ChatMember.user_id == user_id).all()

# -------------------------------
# CHAT MEMBER CRUD
# -------------------------------

def add_member_to_chat(db: Session, chat_id: int, user_id: int) -> ChatMember:
    member = ChatMember(chat_id=chat_id, user_id=user_id, last_seen_at=datetime.now(UTC))
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def get_chat_members(db: Session, chat_id: int) -> list[type[ChatMember]]:
    return db.query(ChatMember).filter(ChatMember.chat_id == chat_id).all()

# -------------------------------
# MESSAGE CRUD
# -------------------------------

def create_message(
    db: Session,
    chat_id: int,
    sender_id: int,
    msg_type: str,
    text: str = None,
    media_url: str = None
) -> Message:
    message = Message(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        sender_id=sender_id,
        type=msg_type,
        text=text,
        media_url=media_url,
        created_at=datetime.now(UTC)
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_messages_for_chat(db: Session, chat_id: int) -> list[type[Message]]:
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()

# -------------------------------
# MESSAGE STATUS CRUD
# -------------------------------

def mark_message_received(db: Session, message_id: str, user_id: int):
    status = MessageStatus(message_id=message_id, user_id=user_id, received_at=datetime.now(UTC))
    db.add(status)
    db.commit()
    db.refresh(status)
    return status

def mark_message_read(db: Session, message_id: str, user_id: int):
    status = db.query(MessageStatus).filter(
        MessageStatus.message_id == message_id,
        MessageStatus.user_id == user_id
    ).first()
    if status:
        status.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(status)
    return status
