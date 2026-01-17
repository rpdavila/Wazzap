import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from start_backend import app

# Create a single connection
SQLALCHEMY_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite thread fix
    echo=True
)
connection = engine.connect()
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=connection
)

# Override get_db to use the same connection
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create all tables once on the connection
Base.metadata.create_all(bind=connection)

client = TestClient(app)

# Optional: clean tables before each test
@pytest.fixture(autouse=True)
def cleanup_tables():
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(table.delete())
    yield

# -------------------------------
# Test chat flow
# -------------------------------
def test_chat_flow_isolated():
    # Register users
    users = [
        {"username": "alice", "pin": "1234"},
        {"username": "bob", "pin": "5678"}
    ]
    user_ids = []

    for u in users:
        resp = client.post("/auth/register", json=u)
        assert resp.status_code == 200
        data = resp.json()
        user_ids.append(data["id"])

    # Login users
    for u in users:
        resp = client.post("/auth/login", json=u)
        assert resp.status_code == 200
        assert "Welcome" in resp.json()["message"]

    # Create DM
    dm_payload = {"user1_id": user_ids[0], "user2_id": user_ids[1]}
    dm_resp = client.post("/chats/dm", json=dm_payload)
    assert dm_resp.status_code == 200
    chat_id = dm_resp.json()["id"]

    # Send messages
    messages = [
        {"chat_id": chat_id, "sender_id": user_ids[0], "type": "text", "text": "Hello Bob!"},
        {"chat_id": chat_id, "sender_id": user_ids[1], "type": "text", "text": "Hey Alice!"}
    ]

    for m in messages:
        resp = client.post(f"/chats/{chat_id}/messages", json=m)
        assert resp.status_code == 200
        assert "id" in resp.json()

    # Fetch messages
    msgs_resp = client.get(f"/chats/{chat_id}/messages")
    assert msgs_resp.status_code == 200
    msgs_data = msgs_resp.json()
    assert len(msgs_data) == 2
    assert msgs_data[0]["text"] == "Hello Bob!"
    assert msgs_data[1]["text"] == "Hey Alice!"
