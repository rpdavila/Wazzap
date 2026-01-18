import { config } from '../config.js';
import { auth } from '../stores/auth.js';
import { websocket } from '../stores/websocket.js';
import { chats } from '../stores/chats.js';
import { messages } from '../stores/messages.js';
import { activeChatId } from '../stores/chats.js';
import { api } from './api.js';
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
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:75',message:'handleNewMessage entry',data:{chat_id:data.chat_id,message_id:data.message?.id,sender_id:data.message?.sender_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
  // #endregion
  
  const { chat_id, message } = data;
  const authStore = get(auth);
  
  // Check if this message is from the current user (sender)
  const isOwnMessage = message.sender_id === authStore.userId || 
                       message.sender_username === authStore.username;
  
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:82',message:'Message ownership check',data:{isOwnMessage,currentUserId:authStore.userId,messageSenderId:message.sender_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
  // #endregion
  
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
  
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:91',message:'Chat existence check',data:{chat_id,chatExists,currentChatsCount:currentChats.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
  // #endregion
  
  // If chat doesn't exist, reload chats list to get the new chat
  // Use backend-provided unread counts (they're persistent and accurate)
  if (!chatExists) {
    try {
      const chatsList = await api.getChats();
      // Use backend-provided unread_count (it's calculated from database)
      // Don't preserve client-side counts - backend is the source of truth
      chats.set(chatsList);
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:97',message:'Chat list reloaded with preserved unread counts',data:{newChatsCount:chatsList.length,preservedUnreadCounts:Array.from(unreadCountsMap.entries())},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
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
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:139',message:'Before unread count update',data:{chat_id,currentActiveChatId,isOwnMessage},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
  // #endregion
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
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:152',message:'Unread count updated',data:{chat_id,oldUnreadCount,newUnreadCount:chat.unread_count,willIncrement:!isOwnMessage && currentActiveChatId !== chat_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
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
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:200',message:'handleMessageReadUpdate entry',data:{chat_id:data.chat_id,message_id:data.message_id,read_by:data.read_by,read_count:data.read_count,data_keys:Object.keys(data)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'L'})}).catch(()=>{});
  // #endregion
  
  const { chat_id, message_id, read_by, read_count } = data;
  const authStore = get(auth);
  
  // #region agent log
  const currentMessages = get(messages);
  const message = currentMessages[chat_id]?.find(m => m.id === message_id);
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:210',message:'Before message update',data:{chat_id,message_id,message_found:!!message,message_sender_id:message?.sender_id,current_user_id:authStore.userId,is_own_message:message?.sender_id === authStore.userId,read_count,read_by},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'L'})}).catch(()=>{});
  // #endregion
  
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
  
  // #region agent log
  const updatedMessages = get(messages);
  const updatedMessage = updatedMessages[chat_id]?.find(m => m.id === message_id);
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:225',message:'After message update',data:{chat_id,message_id,new_status,updated_message_status:updatedMessage?.status,updated_read_count:updatedMessage?.read_count},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'L'})}).catch(()=>{});
  // #endregion
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
  // #region agent log
  fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:227',message:'markMessagesAsRead called',data:{chatId,lastMessageId,chatIdIsNull:chatId === null || chatId === undefined,lastMessageIdIsNull:lastMessageId === null || lastMessageId === undefined,chatIdType:typeof chatId,lastMessageIdType:typeof lastMessageId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
  // #endregion
  
  // Validate parameters - be strict about types
  if (chatId === null || chatId === undefined || chatId === '' || lastMessageId === null || lastMessageId === undefined || lastMessageId === '') {
    console.error('markMessagesAsRead called with invalid parameters:', { chatId, lastMessageId, chatIdType: typeof chatId, lastMessageIdType: typeof lastMessageId });
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:235',message:'markMessagesAsRead validation failed',data:{chatId,lastMessageId,chatIdType:typeof chatId,lastMessageIdType:typeof lastMessageId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
    // #endregion
    return;
  }
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    const payload = {
      type: 'message.read',
      chat_id: chatId,
      message_id: lastMessageId
    };
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:245',message:'Sending message.read WebSocket event',data:{payload,chat_id:payload.chat_id,message_id:payload.message_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
    // #endregion
    socket.send(JSON.stringify(payload));
  } else {
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'websocket.js:250',message:'WebSocket not ready',data:{socketExists:!!socket,readyState:socket?.readyState},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
    // #endregion
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
      
      // Check if session was explicitly invalidated (not just server restart)
      // 1008 = Policy violation (server uses this for explicitly invalid session)
      // 1001 = Going Away (server uses this for server restarts - session expired)
      // 1003 = Invalid data (can indicate 403 rejection during handshake)
      const isSessionExplicitlyInvalid = 
        (event.code === 1008 && event.reason && (
          event.reason.includes('Invalid session') || 
          event.reason.includes('Invalid token') ||
          event.reason.includes('Please log in again')
        ));
      
      // For server restarts (1001 = Going Away, 1006 = abnormal closure), try to reconnect
      // Only logout if we get an explicit "Invalid session" or "Invalid token" message (1008)
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
