from sqlalchemy.orm import Session

from models import User, Chat, ChatMember, Message, MessageStatus
from typing import Optional
from datetime import datetime


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


def find_existing_dm(db: Session, user1_id: int, user2_id: int) -> Optional[Chat]:
    """
    Find an existing direct message chat between two users.
    Returns the chat if found, None otherwise.
    """
    # Get all direct message chats for user1
    user1_chats = (
        db.query(Chat)
        .join(ChatMember)
        .filter(ChatMember.user_id == user1_id)
        .filter(Chat.type == "direct")
        .all()
    )
    
    # Check each chat to see if it contains both users
    for chat in user1_chats:
        members = get_chat_members(db, chat.id)
        member_ids = {m.user_id for m in members}
        # Check if both users are in this chat and it only has 2 members (1:1 chat)
        if len(member_ids) == 2 and user1_id in member_ids and user2_id in member_ids:
            return chat
    
    return None


def get_unread_count(db: Session, chat_id: int, user_id: int) -> int:
    """
    Calculate unread message count for a user in a chat.
    Counts messages created after the user's last_seen_at timestamp
    that are not from the user themselves.
    """
    # Get the user's last_seen_at for this chat
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id
    ).first()
    
    if not chat_member:
        return 0
    
    # Count messages created after last_seen_at (or all messages if last_seen_at is None)
    # that are not from the user
    query = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender_id != user_id
    )
    
    if chat_member.last_seen_at:
        query = query.filter(Message.created_at > chat_member.last_seen_at)
    
    return query.count()


def update_last_seen(db: Session, chat_id: int, user_id: int, last_message_id: Optional[int] = None) -> None:
    """
    Update the user's last_seen_at timestamp for a chat.
    If last_message_id is provided, use that message's created_at timestamp.
    Otherwise, use the current time.
    """
    from datetime import datetime
    
    # Validate chat_id is not None
    if chat_id is None:
        raise ValueError("chat_id cannot be None")
    
    chat_member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id
    ).first()
    
    if not chat_member:
        # Create chat member if it doesn't exist (shouldn't happen, but be safe)
        # Ensure chat_id is set correctly
        chat_member = ChatMember(chat_id=chat_id, user_id=user_id)
        db.add(chat_member)
    
    if last_message_id:
        # Get the message's created_at timestamp
        message = db.query(Message).filter(Message.id == last_message_id).first()
        if message:
            chat_member.last_seen_at = message.created_at
        else:
            chat_member.last_seen_at = datetime.utcnow()
    else:
        chat_member.last_seen_at = datetime.utcnow()
    
    db.commit()
    db.refresh(chat_member)


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
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()


def get_message_status(db: Session, message_id: int, user_id: int) -> Optional[type[MessageStatus]]:
    """Get message status for a specific user and message."""
    return db.query(MessageStatus).filter(
        MessageStatus.message_id == message_id,
        MessageStatus.user_id == user_id
    ).first()


def get_read_statuses_for_message(db: Session, message_id: int) -> list[int]:
    """Get list of user IDs who have read a specific message."""
    statuses = db.query(MessageStatus).filter(
        MessageStatus.message_id == message_id,
        MessageStatus.read_at.isnot(None)
    ).all()
    return [s.user_id for s in statuses]


def create_or_update_message_status(
    db: Session,
    message_id: int,
    user_id: int,
    read_at: Optional[datetime] = None
) -> type[MessageStatus]:
    """
    Create or update message status for a user.
    If read_at is provided, marks the message as read.
    """
    from datetime import datetime
    
    status = get_message_status(db, message_id, user_id)
    
    if not status:
        status = MessageStatus(
            message_id=message_id,
            user_id=user_id,
            received_at=datetime.utcnow(),
            read_at=read_at if read_at else None
        )
        db.add(status)
    else:
        if read_at and not status.read_at:
            status.read_at = read_at
    
    db.commit()
    db.refresh(status)
    return status


def mark_messages_as_read(
    db: Session,
    chat_id: int,
    user_id: int,
    last_message_id: int
) -> list[int]:
    """
    Mark all messages in a chat up to last_message_id as read for a user.
    Returns list of message IDs that were marked as read.
    """
    from datetime import datetime
    
    # Get all messages in the chat up to and including last_message_id
    messages = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.id <= last_message_id,
        Message.sender_id != user_id  # Don't mark own messages as read
    ).all()
    
    marked_message_ids = []
    read_at = datetime.utcnow()
    
    for message in messages:
        status = create_or_update_message_status(db, message.id, user_id, read_at)
        marked_message_ids.append(message.id)
    
    return marked_message_ids


# -------------------------------
# ADMIN - USERS
# -------------------------------
def list_all_users(db: Session) -> list[User]:
    """List all users in the system."""
    return db.query(User).all()


def update_user(db: Session, user_id: int, username: Optional[str] = None, pin_hash: Optional[str] = None) -> Optional[User]:
    """Update user information."""
    user = get_user(db, user_id)
    if not user:
        return None
    
    if username is not None:
        user.username = username
    if pin_hash is not None:
        user.pin_hash = pin_hash
    
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user from the system."""
    user = get_user(db, user_id)
    if not user:
        return False
    
    db.delete(user)
    db.commit()
    return True