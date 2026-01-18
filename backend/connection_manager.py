# connection_manager.py
from fastapi import WebSocket
from typing import Dict, List, Set, Optional, Callable
from starlette.websockets import WebSocketState

class ConnectionManager:
    def __init__(self):
        # Dict[chat_id, List[WebSocket]] - for backward compatibility
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Dict[user_id, WebSocket] - track connections by user
        self.user_connections: Dict[int, WebSocket] = {}
        # Dict[chat_id, Set[user_id]] - track which users are members of which chats
        # This is populated when we broadcast, by getting chat members from DB

    async def connect(self, websocket: WebSocket, chat_id: int, user_id: Optional[int] = None):
        # Only accept if not already connected (handles both /api/ws and /ws/{chat_id}/{user_id} endpoints)
        if websocket.client_state != WebSocketState.CONNECTED:
            await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)
        
        # Track connection by user_id if provided
        if user_id is not None:
            self.user_connections[user_id] = websocket

    async def disconnect(self, websocket: WebSocket, chat_id: int = None, user_id: Optional[int] = None):
        if chat_id is None:
            # Disconnect from all chats
            chats_to_remove = []
            for cid, connections in list(self.active_connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:
                        chats_to_remove.append(cid)
            for cid in chats_to_remove:
                del self.active_connections[cid]
            # Use try/except as the socket might already be closed by the client
            try:
                await websocket.close()
            except Exception:
                pass
        else:
            if chat_id in self.active_connections and websocket in self.active_connections[chat_id]:
                self.active_connections[chat_id].remove(websocket)
                # Use try/except as the socket might already be closed by the client
                try:
                    await websocket.close()
                except Exception:
                    pass
                if not self.active_connections[chat_id]:
                    del self.active_connections[chat_id]
        
        # Remove user connection if provided
        if user_id is not None and user_id in self.user_connections:
            # Only remove if it's the same websocket
            if self.user_connections[user_id] == websocket:
                del self.user_connections[user_id]

    async def broadcast(self, chat_id: int, message: str, get_chat_members_fn: Optional[Callable] = None):
        """
        Broadcast message to all chat members.
        If get_chat_members_fn is provided, it will be called to get all chat members
        and send the message to all their connections (even if they haven't opened the chat).
        Otherwise, it falls back to only sending to connections that have opened the chat.
        """
        # #region agent log
        import json
        import time
        sent_connections = set()
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "H",
            "location": "connection_manager.py:60",
            "message": "broadcast method entry",
            "data": {
                "chat_id": chat_id,
                "has_get_members_fn": get_chat_members_fn is not None,
                "active_connections_count": len(self.active_connections.get(chat_id, [])),
                "user_connections_count": len(self.user_connections)
            },
            "timestamp": int(time.time() * 1000)
        }
        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
        # #endregion
        
        # Track which connections we've already sent to (by connection object id)
        sent_connection_ids = set()
        
        # First, send to all connections that have opened this chat (backward compatibility)
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                conn_id = id(connection)
                if conn_id not in sent_connection_ids:
                    try:
                        await connection.send_text(message)
                        sent_connection_ids.add(conn_id)
                        # #region agent log
                        log_data = {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "H",
                            "location": "connection_manager.py:85",
                            "message": "Sent to active connection",
                            "data": {"chat_id": chat_id, "connection_id": conn_id},
                            "timestamp": int(time.time() * 1000)
                        }
                        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data) + '\n')
                        # #endregion
                    except Exception as e:
                        # #region agent log
                        log_data = {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "H",
                            "location": "connection_manager.py:95",
                            "message": "Failed to send to active connection",
                            "data": {"chat_id": chat_id, "error": str(e)},
                            "timestamp": int(time.time() * 1000)
                        }
                        with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps(log_data) + '\n')
                        # #endregion
                        pass
        
        # Also send to all chat members' connections (if we have the function to get members)
        if get_chat_members_fn is not None:
            try:
                members = get_chat_members_fn(chat_id)
                # #region agent log
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H",
                    "location": "connection_manager.py:110",
                    "message": "Got chat members",
                    "data": {"chat_id": chat_id, "members_count": len(members)},
                    "timestamp": int(time.time() * 1000)
                }
                with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
                # #endregion
                for member in members:
                    user_id = member.user_id
                    if user_id in self.user_connections:
                        connection = self.user_connections[user_id]
                        conn_id = id(connection)
                        # Only send if not already sent (avoid duplicates)
                        if conn_id not in sent_connection_ids:
                            try:
                                await connection.send_text(message)
                                sent_connection_ids.add(conn_id)
                                # #region agent log
                                log_data = {
                                    "sessionId": "debug-session",
                                    "runId": "run1",
                                    "hypothesisId": "H",
                                    "location": "connection_manager.py:128",
                                    "message": "Sent to user connection",
                                    "data": {"chat_id": chat_id, "user_id": user_id, "connection_id": conn_id},
                                    "timestamp": int(time.time() * 1000)
                                }
                                with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                                    f.write(json.dumps(log_data) + '\n')
                                # #endregion
                            except Exception as e:
                                # #region agent log
                                log_data = {
                                    "sessionId": "debug-session",
                                    "runId": "run1",
                                    "hypothesisId": "H",
                                    "location": "connection_manager.py:140",
                                    "message": "Failed to send to user connection",
                                    "data": {"chat_id": chat_id, "user_id": user_id, "error": str(e)},
                                    "timestamp": int(time.time() * 1000)
                                }
                                with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                                    f.write(json.dumps(log_data) + '\n')
                                # #endregion
                                pass
            except Exception as e:
                # #region agent log
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H",
                    "location": "connection_manager.py:152",
                    "message": "Error in broadcast get_members",
                    "data": {"chat_id": chat_id, "error": str(e)},
                    "timestamp": int(time.time() * 1000)
                }
                with open(r'c:\Users\AX\PycharmProjects\Wazzap\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
                # #endregion
                # If getting chat members fails, fall back to existing behavior
                pass