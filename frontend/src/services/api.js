import { config } from '../config.js';
import { auth } from '../stores/auth.js';
import { get } from 'svelte/store';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Helper function to create a timeout promise
function createTimeoutPromise(timeoutMs) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timeout')), timeoutMs);
  });
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
  const timeoutMs = options.timeout || 10000; // Default 10 seconds
  
  // Remove timeout from options before passing to fetch
  const { timeout, ...fetchOptions } = options;
  
  try {
    const response = await Promise.race([
      fetch(url, {
        ...fetchOptions,
        headers
      }),
      createTimeoutPromise(timeoutMs)
    ]);

    if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    // Clone response to read it multiple times if needed
    const responseClone = response.clone();
    try {
      const errorData = await response.json();
      // FastAPI returns errors as {detail: "message"} or {detail: [...]}
      if (errorData.detail) {
        errorMessage = Array.isArray(errorData.detail) 
          ? errorData.detail.map(err => err.msg || err).join(', ')
          : errorData.detail;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      } else if (typeof errorData === 'string') {
        errorMessage = errorData;
      }
    } catch {
      // If response is not JSON, try to get text from clone
      try {
        const errorText = await responseClone.text();
        if (errorText) errorMessage = errorText;
      } catch {
        // Fallback to status code message
      }
    }
    throw new ApiError(errorMessage, response.status);
  }

    return response.json();
  } catch (err) {
    // Handle timeout and network errors
    if (err.message === 'Request timeout') {
      throw new ApiError('Request timed out. The server is not responding. Please check your connection and try again.', 408);
    }
    // Re-throw ApiError as-is
    if (err instanceof ApiError) {
      throw err;
    }
    // Handle network errors (fetch failures)
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new ApiError('Unable to connect to the server. Please check your internet connection and ensure the server is running.', 0);
    }
    // Re-throw other errors
    throw err;
  }
}

export const api = {
  async register(username, pin) {
    const response = await request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, pin })
    });
    return response;
  },

  async login(username, pin) {
    const response = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, pin })
    });
    return response;
  },

  async getChats() {
    const authStore = get(auth);
    // Try to get user_id from auth store, fallback to username
    const params = new URLSearchParams();
    if (authStore.userId) {
      params.append('user_id', authStore.userId.toString());
    } else if (authStore.username) {
      params.append('username', authStore.username);
    }
    const queryString = params.toString();
    return request(`/api/chats${queryString ? '?' + queryString : ''}`);
  },

  async getMessages(chatId) {
    return request(`/api/chats/${chatId}/messages`);
  },

  async uploadMedia(file) {
    const authStore = get(auth);
    const formData = new FormData();
    formData.append('file', file);

    const timeoutMs = 30000; // 30 seconds for file uploads
    
    try {
      const response = await Promise.race([
        fetch(`${config.apiUrl}/api/media/upload`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authStore.jwt}`
          },
          body: formData
        }),
        createTimeoutPromise(timeoutMs)
      ]);

      if (!response.ok) {
        const errorText = await response.text();
        throw new ApiError(errorText || `HTTP ${response.status}`, response.status);
      }

      return response.json();
    } catch (err) {
      if (err.message === 'Request timeout') {
        throw new ApiError('Upload timed out. Please try again.', 408);
      }
      if (err instanceof ApiError) {
        throw err;
      }
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new ApiError('Unable to connect to the server. Please check your internet connection and ensure the server is running.', 0);
      }
      throw err;
    }
  },

  async getAllUsers() {
    return request('/api/users');
  },

  async createDM(user1Id, user2Id) {
    return request('/api/chats/dm', {
      method: 'POST',
      body: JSON.stringify({ user1_id: user1Id, user2_id: user2Id })
    });
  }
};
