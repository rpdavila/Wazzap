import { config } from '../config.js';
import { auth } from '../stores/auth.js';
import { websocket } from '../stores/websocket.js';
import { chats } from '../stores/chats.js';
import { messages } from '../stores/messages.js';
import { activeChatId } from '../stores/chats.js';
import { api } from './api.js';
import { get } from 'svelte/store';
import { debugLog } from '../utils/debugLog.js';

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
      
      case 'message.read.update':
        handleMessageReadUpdate(data);
        break;
      
      case 'chat.member.added':
        handleChatMemberAdded(data);
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

// Request notification permission on load
if (typeof window !== 'undefined' && 'Notification' in window) {
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

async function handleNewMessage(data) {
  debugLog('websocket.js:75', 'handleNewMessage entry', { chat_id: data.chat_id, message_id: data.message?.id, sender_id: data.message?.sender_id }, 'F');
  
  const { chat_id, message } = data;
  const authStore = get(auth);
  
  // Check if this message is from the current user (sender)
  const isOwnMessage = message.sender_id === authStore.userId || 
                       message.sender_username === authStore.username;
  
  debugLog('websocket.js:82', 'Message ownership check', { isOwnMessage, currentUserId: authStore.userId, messageSenderId: message.sender_id }, 'F');
  
  // Set initial status for the message
  // For own messages: "sent" (will update to "read" when others read it)
  // For received messages: "unread" if chat is not active, otherwise will be marked as read
  if (!message.status) {
    if (isOwnMessage) {
      message.status = 'sent';
      message.read_by = message.read_by || [];
      message.read_count = message.read_count || 0;
    } else {
      const currentActiveChatId = get(activeChatId);
      message.status = (currentActiveChatId === chat_id) ? 'unread' : 'unread';
      message.read_by = message.read_by || [];
      message.read_count = message.read_count || 0;
    }
  }
  
  // Add message to store
  messages.addMessage(chat_id, message);
  
  // Check if chat exists in the chats list
  const currentChats = get(chats);
  const chatExists = currentChats.some(c => c.id === chat_id);
  
  // If chat doesn't exist, reload chats list to get the new chat
  // Use backend-provided unread counts (they're persistent and accurate)
  if (!chatExists) {
    try {
      const chatsList = await api.getChats();
      // Use backend-provided unread_count (it's calculated from database)
      // Don't preserve client-side counts - backend is the source of truth
      chats.set(chatsList);
    } catch (err) {
      console.error('Failed to reload chats:', err);
    }
  }
  
  // Automatically connect to this chat if not already connected
  // This ensures we receive future messages for this chat
  if (socket && socket.readyState === WebSocket.OPEN) {
    sendWebSocketMessage('chat.open', {
      chat_id: chat_id,
      user_id: authStore.userId
    });
  }
  
  // Update unread count in chats (only for messages from others)
  // Do this AFTER any chat list reload to ensure we're working with the latest data
  const currentActiveChatId = get(activeChatId);
  chats.update(chatsList => {
    const chat = chatsList.find(c => c.id === chat_id);
    if (chat) {
      const oldUnreadCount = chat.unread_count || 0;
      // Only increment unread count if:
      // 1. This is not the current user's message
      // 2. The chat is not currently open
      if (!isOwnMessage && currentActiveChatId !== chat_id) {
        chat.unread_count = oldUnreadCount + 1;
      }
    }
    return [...chatsList]; // Return new array to trigger reactivity
  });
  
  // Show browser notification for messages from others when tab is not focused
  if (!isOwnMessage && typeof window !== 'undefined' && 'Notification' in window) {
    const isTabFocused = document.hasFocus();
    if (!isTabFocused && Notification.permission === 'granted') {
      const chat = currentChats.find(c => c.id === chat_id);
      const chatTitle = chat?.title || chat?.other_user_name || `Chat ${chat_id}`;
      const messagePreview = message.content?.substring(0, 50) || '[Media]';
      
      new Notification(`${message.sender_username || 'Someone'} - ${chatTitle}`, {
        body: messagePreview,
        icon: '/favicon.ico',
        tag: `chat-${chat_id}`,
        requireInteraction: false
      });
    }
  }
  
  // Mark as read if this chat is currently open AND it's not the current user's message
  // (You can't "read" your own messages)
  const currentChatId = get(activeChatId);
  if (currentChatId === chat_id && !isOwnMessage) {
    markMessagesAsRead(chat_id, message.id);
  }
}

function handleMessageStatus(data) {
  const { chat_id, message_id, status } = data;
  messages.updateMessage(chat_id, message_id, { status });
}

function handleMessageReadUpdate(data) {
  const { chat_id, message_id, read_by, read_count } = data;
  const authStore = get(auth);
  
  const currentMessages = get(messages);
  const message = currentMessages[chat_id]?.find(m => m.id === message_id);
  
  // Update message with read status
  const newStatus = (() => {
    if (message && message.sender_id === authStore.userId) {
      // For own messages: "read" if read_count > 0, "sent" otherwise
      return read_count > 0 ? 'read' : 'sent';
    }
    return message?.status; // Keep existing status for received messages
  })();
  
  messages.updateMessage(chat_id, message_id, {
    read_by: read_by || [],
    read_count: read_count || 0,
    status: newStatus
  });
}

async function handleChatMemberAdded(data) {
  console.log('Received chat.member.added notification:', data);
  const { chat_id, chat_title, chat_type } = data;
  
  // Reload the chat list to include the new group chat
  try {
    const chatsList = await api.getChats();
    console.log('Reloading chat list, new chats:', chatsList.length);
    chats.set(chatsList);
    console.log('Chat list reloaded after being added to group chat:', chat_id, chat_title);
  } catch (err) {
    console.error('Failed to reload chats after being added to group:', err);
  }
}

function markMessagesAsRead(chatId, lastMessageId) {
  // Validate parameters - be strict about types
  if (chatId === null || chatId === undefined || chatId === '' || lastMessageId === null || lastMessageId === undefined || lastMessageId === '') {
    console.error('markMessagesAsRead called with invalid parameters:', { chatId, lastMessageId, chatIdType: typeof chatId, lastMessageIdType: typeof lastMessageId });
    return;
  }
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    const payload = {
      type: 'message.read',
      chat_id: chatId,
      message_id: lastMessageId
    };
    socket.send(JSON.stringify(payload));
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
        // Connection was rejected - could be invalid session or server restart
        // Don't mark as invalid immediately, let onclose handle it based on the close code
        console.log('WebSocket connection rejected');
        connectionRejected = true;
      }
    };
    
    socket.onclose = (event) => {
      console.log('WebSocket closed', event.code, event.reason);
      websocket.set({ connected: false, socket: null });
      stopHeartbeat();
      
      // Check if session was explicitly invalidated
      // 1008 = Policy violation (server uses this for explicitly invalid session)
      // 1001 = Going Away (server uses this for server restarts - session expired)
      // 1003 = Invalid data (can indicate 403 rejection during handshake)
      // 1006 = Abnormal closure (can happen when connection is rejected with 403 before handshake completes)
      // After server restart, session is gone - user must log in again
      const isSessionExplicitlyInvalid = 
        (event.code === 1008 && event.reason && (
          event.reason.includes('Invalid session') || 
          event.reason.includes('Invalid token') ||
          event.reason.includes('Please log in again')
        )) ||
        (event.code === 1001 && (
          !event.reason || // Code 1001 from backend indicates session expired
          event.reason.includes('Session expired') ||
          event.reason.includes('server restart') ||
          event.reason.includes('Please reconnect')
        )) ||
        // If connection was rejected (403) and we get abnormal closure,
        // it's likely a session invalidation (FastAPI may convert 403 to 1006)
        (connectionRejected && event.code === 1006 && !event.wasClean);
      
      // If session is invalid (either 1008 with invalid token, or 1001 with session expired),
      // logout and redirect to login - don't try to reconnect
      if (isSessionExplicitlyInvalid) {
        console.log('Session explicitly invalidated, clearing auth and redirecting to login...');
        // Store message for login page
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('session_revalidation_message', 'true');
        }
        auth.logout();
        return; // Don't attempt to reconnect
      }
      
      // Attempt to reconnect if not a normal closure
      // This handles server restarts, network issues, etc.
      if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        console.log(`WebSocket closed (code: ${event.code}). Reconnecting in ${delay}ms... (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
        setTimeout(() => {
          if (get(auth).isAuthenticated) {
            connectWebSocket();
          }
        }, delay);
      } else if (reconnectAttempts >= maxReconnectAttempts) {
        console.error('Max reconnection attempts reached. Please refresh the page.');
        // Don't logout, just show that connection failed
        // User can manually refresh if needed
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
