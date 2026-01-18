import { config } from '../config.js';
import { auth } from '../stores/auth.js';
import { websocket } from '../stores/websocket.js';
import { chats } from '../stores/chats.js';
import { messages } from '../stores/messages.js';
import { activeChatId } from '../stores/chats.js';
import { get } from 'svelte/store';

let socket = null;
let heartbeatInterval = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function sendHeartbeat() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping' }));
  }
}

function startHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }
  heartbeatInterval = setInterval(sendHeartbeat, 30000); // 30 seconds
}

function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
}

function handleWebSocketEvent(event) {
  try {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
      case 'session.ready':
        reconnectAttempts = 0;
        break;
      
      case 'message.new':
        handleNewMessage(data);
        break;
      
      case 'message.status':
        handleMessageStatus(data);
        break;
      
      case 'presence.update':
        // Handle presence updates if needed
        break;
      
      case 'pong':
        // Heartbeat response
        break;
      
      default:
        console.warn('Unknown WebSocket event type:', data.type);
    }
  } catch (error) {
    console.error('Error parsing WebSocket message:', error);
  }
}

function handleNewMessage(data) {
  const { chat_id, message } = data;
  
  // Add message to store
  messages.addMessage(chat_id, message);
  
  // Update unread count in chats
  chats.update(chatsList => {
    const chat = chatsList.find(c => c.id === chat_id);
    if (chat) {
      if (get(activeChatId) !== chat_id) {
        chat.unread_count = (chat.unread_count || 0) + 1;
      }
    }
    return chatsList;
  });
  
  // Mark as read if this chat is currently open
  const currentChatId = get(activeChatId);
  if (currentChatId === chat_id) {
    markMessagesAsRead(chat_id, message.id);
  }
}

function handleMessageStatus(data) {
  const { chat_id, message_id, status } = data;
  messages.updateMessage(chat_id, message_id, { status });
}

function markMessagesAsRead(chatId, lastMessageId) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'message.read',
      chat_id: chatId,
      message_id: lastMessageId
    }));
  }
  
  // Update unread count
  chats.update(chatsList => {
    const chat = chatsList.find(c => c.id === chatId);
    if (chat) {
      chat.unread_count = 0;
    }
    return chatsList;
  });
}

export function connectWebSocket() {
  const authStore = get(auth);
  
  if (!authStore.jwt || !authStore.sessionId) {
    console.error('Cannot connect WebSocket: missing JWT or session_id');
    return;
  }

  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log('WebSocket already connected');
    return;
  }

  // config.wsUrl already includes /api/ws
  const wsUrl = `${config.wsUrl}?token=${encodeURIComponent(authStore.jwt)}&session_id=${encodeURIComponent(authStore.sessionId)}`;
  
  try {
    socket = new WebSocket(wsUrl);
    let connectionRejected = false;
    
    socket.onopen = () => {
      console.log('WebSocket connected');
      websocket.set({ connected: true, socket });
      reconnectAttempts = 0;
      startHeartbeat();
    };
    
    socket.onmessage = handleWebSocketEvent;
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Check if connection was rejected (e.g., 403 Forbidden)
      // This happens when the server rejects the connection before it opens
      if (socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        // Connection was rejected, likely due to invalid session
        console.log('WebSocket connection rejected, session may be invalid');
        connectionRejected = true;
      }
    };
    
    socket.onclose = (event) => {
      console.log('WebSocket closed', event.code, event.reason);
      websocket.set({ connected: false, socket: null });
      stopHeartbeat();
      
      // Check if session was invalidated (e.g., after server restart)
      // 1008 = Policy violation (server uses this for invalid session)
      // 1003 = Invalid data (can indicate 403 rejection during handshake)
      // Also check if connection was rejected before opening
      const isSessionInvalid = 
        (event.code === 1008 && event.reason && (
          event.reason.includes('Invalid session') || 
          event.reason.includes('Please log in again')
        )) ||
        (event.code === 1008 && connectionRejected) ||
        (event.code === 1003 && connectionRejected) ||
        (connectionRejected && event.code !== 1000);
      
      if (isSessionInvalid) {
        console.log('Session invalidated, clearing auth and redirecting to login...');
        // Store message for login page
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('session_revalidation_message', 'true');
        }
        auth.logout();
        return; // Don't attempt to reconnect
      }
      
      // Attempt to reconnect if not a normal closure
      if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        console.log(`Reconnecting in ${delay}ms...`);
        setTimeout(() => {
          if (get(auth).isAuthenticated) {
            connectWebSocket();
          }
        }, delay);
      }
    };
  } catch (error) {
    console.error('Error creating WebSocket:', error);
    websocket.set({ connected: false, socket: null });
  }
}

export function disconnectWebSocket() {
  stopHeartbeat();
  if (socket) {
    socket.close(1000, 'User logout');
    socket = null;
  }
  websocket.set({ connected: false, socket: null });
}

export function sendWebSocketMessage(type, data) {
  const ws = get(websocket);
  if (ws.socket && ws.socket.readyState === WebSocket.OPEN) {
    ws.socket.send(JSON.stringify({ type, ...data }));
    return true;
  }
  console.warn('Cannot send WebSocket message: not connected');
  return false;
}

export function markChatAsRead(chatId, lastMessageId) {
  markMessagesAsRead(chatId, lastMessageId);
}
