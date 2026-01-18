from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
from pathlib import Path

# Load variables from .env
# Try root directory first (parent of backend), then backend directory
root_dir = Path(__file__).parent.parent
backend_dir = Path(__file__).parent
# Load from root .env first, then backend/.env (root takes precedence)
load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env", override=False)  # Don't override root .env values

# Get the DATABASE_URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL not set in .env")

# Get SQL_ECHO from environment (default: False for less verbose logging)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# Create engine with SQLite-specific connection args if sqlite db
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}  # Allow SQLite to work with FastAPI

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=SQL_ECHO,  # Only echo SQL if explicitly enabled via SQL_ECHO=true
    future=True,
    connect_args=connect_args
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
