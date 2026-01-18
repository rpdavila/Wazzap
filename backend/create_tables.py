from database import Base, engine
from models import User, Chat, ChatMember, Message, MessageStatus  # <- import all models

# Create all tables
Base.metadata.create_all(bind=engine)

