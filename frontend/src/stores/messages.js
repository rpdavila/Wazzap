import { writable } from 'svelte/store';

// Store messages by chat ID
const messagesByChat = {};

function createMessagesStore() {
  const { subscribe, set, update } = writable(messagesByChat);

  return {
    subscribe,
    setMessages: (chatId, messageList) => {
      messagesByChat[chatId] = messageList;
      set(messagesByChat);
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
