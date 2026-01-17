from sqlalchemy.orm import Session

from models import User, Chat, ChatMember, Message
from typing import Optional


# -------------------------------
# USERS
# -------------------------------
def create_user(db: Session, username: str, pin_hash: str) -> User:
    user = User(username=username, pin_hash=pin_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# -------------------------------
# CHATS
# -------------------------------
def create_chat(db: Session, chat_type: str, title: Optional[str] = None) -> Chat:
    chat = Chat(type=chat_type, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def get_chat(db: Session, chat_id: int) -> Optional[Chat]:
    return db.query(Chat).filter(Chat.id == chat_id).first()


def list_chats_for_user(db: Session, user_id: int) -> list[type[Chat]]:
    return (
        db.query(Chat)
        .join(ChatMember)
        .filter(ChatMember.user_id == user_id)
        .all()
    )


# -------------------------------
# CHAT MEMBERS
# -------------------------------
def add_member_to_chat(db: Session, chat_id: int, user_id: int) -> type[ChatMember] | ChatMember:
    existing = db.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()
    if existing:
        return existing

    member = ChatMember(chat_id=chat_id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def get_chat_members(db: Session, chat_id: int) -> list[type[ChatMember]]:
    return db.query(ChatMember).filter(ChatMember.chat_id == chat_id).all()


# -------------------------------
# MESSAGES
# -------------------------------
def create_message(
    db: Session,
    chat_id: int,
    sender_id: int,
    msg_type: str,
    text: Optional[str] = None,
    media_url: Optional[str] = None
) -> Message:
    message = Message(
        chat_id=chat_id,
        sender_id=sender_id,
        type=msg_type,
        text=text,
        media_url=media_url
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages_for_chat(db: Session, chat_id: int) -> list[type[Message]]:
    return db.query(Message).filter(Message.chat_id == chat_id).all()
