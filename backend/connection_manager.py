# connection_manager.py
from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Dict[chat_id, List[WebSocket]]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections and websocket in self.active_connections[chat_id]:
            self.active_connections[chat_id].remove(websocket)
            # Use try/except as the socket might already be closed by the client
            try:
                await websocket.close()
            except Exception:
                pass
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, chat_id: int, message: str):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                await connection.send_text(message)
