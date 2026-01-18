import pytest
from fastapi.testclient import TestClient
from start_backend import app
from database import get_db, Base, engine
from sqlalchemy.orm import sessionmaker
# -------------------------------
# Test Will delete all tables after each test Run create_tables.py after test
# -------------------------------
# -------------------------------
# Test database setup (optional)
# -------------------------------
# Using the same database for simplicity, in real cases use a test DB
SessionTesting = sessionmaker(bind=engine)
db = SessionTesting()

# -------------------------------
# Test client
# -------------------------------
client = TestClient(app)

# -------------------------------
# Fixtures
# -------------------------------
@pytest.fixture(scope="function", autouse=True)
def cleanup_tables():
    # Clear tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# -------------------------------
# Test flow
# -------------------------------
def test_chat_flow():
    # -------------------------
    # 1️⃣ Register users
    # -------------------------
    users = [
        {"username": "alice", "pin": "1234"},
        {"username": "bob", "pin": "5678"}
    ]
    user_ids = []

    for u in users:
        resp = client.post("/auth/register", json=u)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        user_ids.append(data["id"])

    # -------------------------
    # 2️⃣ Login users
    # -------------------------
    for u in users:
        resp = client.post("/auth/login", json=u)
        assert resp.status_code == 200
        assert "Welcome" in resp.json()["message"]

    # -------------------------
    # 3️⃣ Create a DM
    # -------------------------
    dm_payload = {"user1_id": user_ids[0], "user2_id": user_ids[1]}
    dm_resp = client.post("/chats/dm", json=dm_payload)
    assert dm_resp.status_code == 200
    chat_id = dm_resp.json()["id"]

    # -------------------------
    # 4️⃣ Send messages
    # -------------------------
    messages = [
        {"chat_id": chat_id, "sender_id": user_ids[0], "type": "text", "text": "Hello Bob!"},
        {"chat_id": chat_id, "sender_id": user_ids[1], "type": "text", "text": "Hey Alice!"}
    ]

    for m in messages:
        resp = client.post(f"/chats/{chat_id}/messages", json=m)
        assert resp.status_code == 200
        assert "id" in resp.json()

    # -------------------------
    # 5️⃣ Fetch messages
    # -------------------------
    msgs_resp = client.get(f"/chats/{chat_id}/messages")
    assert msgs_resp.status_code == 200
    msgs_data = msgs_resp.json()
    assert len(msgs_data) == 2
    assert msgs_data[0]["text"] == "Hello Bob!"
    assert msgs_data[1]["text"] == "Hey Alice!"
