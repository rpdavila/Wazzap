import { config } from '../config.js';
import { auth } from '../stores/auth.js';
import { get } from 'svelte/store';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(endpoint, options = {}) {
  const authStore = get(auth);
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (authStore.jwt) {
    headers['Authorization'] = `Bearer ${authStore.jwt}`;
  }

  const url = `${config.apiUrl}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(errorText || `HTTP ${response.status}`, response.status);
  }

  return response.json();
}

export const api = {
  async login(username, pin) {
    const response = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, pin })
    });
    return response;
  },

  async getChats() {
    return request('/api/chats');
  },

  async getMessages(chatId) {
    return request(`/api/chats/${chatId}/messages`);
  },

  async uploadMedia(file) {
    const authStore = get(auth);
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${config.apiUrl}/api/media/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.jwt}`
      },
      body: formData
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(errorText || `HTTP ${response.status}`, response.status);
    }

    return response.json();
  }
};
