import json
import pytest
import time
from fastapi.testclient import TestClient
from start_backend import app
from database import SessionLocal
from crud import create_user, create_chat, add_member_to_chat

def test_websocket_chat_flow():
    client = TestClient(app)
    db = SessionLocal()
    
    # Generate a unique username to avoid IntegrityError
    unique_username = f"user_{int(time.time())}"
    
    try:
        # 1. Setup: Create a user and a chat
        user = create_user(db, username=unique_username, pin_hash="fake_hash")
        chat = create_chat(db, chat_type="direct")
        add_member_to_chat(db, chat.id, user.id)
        
        # 2. Connect to the websocket
        with client.websocket_connect(f"/ws/{chat.id}/{user.id}") as websocket:
            
            # 3. Send a message
            message_payload = {
                "type": "text",
                "content": "Hello World",
                "media_url": None
            }
            websocket.send_text(json.dumps(message_payload))
            
            # 4. Receive and validate the broadcast
            response_data = websocket.receive_text()
            response_json = json.loads(response_data)
            
            assert response_json["content"] == "Hello World"
            assert response_json["sender_id"] == user.id
            assert response_json["chat_id"] == chat.id
            assert "message_id" in response_json

            # 5. Test disconnecting via control message
            quit_payload = {
                "type": "control",
                "content": "quit"
            }
            websocket.send_text(json.dumps(quit_payload))
            
    finally:
        db.close()

def test_websocket_unauthorized_user():
    client = TestClient(app)
    # Use IDs that definitely don't exist
    with client.websocket_connect("/ws/99999/99999") as websocket:
        data = websocket.receive_text()
        assert "error" in json.loads(data)
