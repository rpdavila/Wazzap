import { writable } from 'svelte/store';

// Store messages by chat ID
const messagesByChat = {};

function createMessagesStore() {
  const { subscribe, set, update } = writable(messagesByChat);

  return {
    subscribe,
    setMessages: (chatId, messageList) => {
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'messages.js:11',message:'setMessages called',data:{chatId,messageListLength:messageList.length,existingMessagesCount:(messagesByChat[chatId] || []).length,allChatIds:Object.keys(messagesByChat)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
      messagesByChat[chatId] = messageList;
      set(messagesByChat);
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'messages.js:13',message:'setMessages completed',data:{chatId,messageListLength:messageList.length,storedMessagesCount:messagesByChat[chatId]?.length || 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
    },
    addMessage: (chatId, message) => {
      if (!messagesByChat[chatId]) {
        messagesByChat[chatId] = [];
      }
      messagesByChat[chatId].push(message);
      set(messagesByChat);
    },
    updateMessage: (chatId, messageId, updates) => {
      if (messagesByChat[chatId]) {
        const index = messagesByChat[chatId].findIndex(m => m.id === messageId);
        if (index !== -1) {
          messagesByChat[chatId][index] = { ...messagesByChat[chatId][index], ...updates };
          set(messagesByChat);
        }
      }
    },
    clear: () => {
      Object.keys(messagesByChat).forEach(key => delete messagesByChat[key]);
      set(messagesByChat);
    }
  };
}

export const messages = createMessagesStore();
