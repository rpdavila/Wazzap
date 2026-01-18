<script>
  import { auth } from '../stores/auth.js';
  import { api, ApiError } from '../services/api.js';
  import { connectWebSocket } from '../services/websocket.js';
  import { chats } from '../stores/chats.js';
  import { messages } from '../stores/messages.js';
  import { activeChatId } from '../stores/chats.js';
  import { currentView } from '../stores/view.js';

  let username = '';
  let pin = '';
  let error = '';
  let loading = false;

  function goToDebug() {
    currentView.set('debug');
  }

  async function handleLogin() {
    if (!username.trim() || !pin.trim()) {
      error = 'Please enter both username and PIN';
      return;
    }

    error = '';
    loading = true;

    try {
      let response;
      
      // Development bypass: allow admin/0000 without server check
      if (username.trim().toLowerCase() === 'admin' && pin === '0000') {
        // Generate mock JWT and session_id for development
        const mockJwt = 'dev-mock-jwt-' + Date.now();
        const mockSessionId = 'dev-session-' + Date.now();
        response = {
          jwt: mockJwt,
          session_id: mockSessionId
        };
      } else {
        // Normal login flow
        response = await api.login(username.trim(), pin);
      }
      
      // Check if response has required fields
      if (!response || !response.jwt || !response.session_id) {
        throw new Error('Invalid response from server. Missing authentication tokens.');
      }
      
      auth.login(username.trim(), response.jwt, response.session_id, response.user_id);
      
      // Connect WebSocket
      connectWebSocket();
      
      // Fetch chats
      await loadChats();
      
      // Clear any previous message data
      messages.clear();
      activeChatId.set(null);
      
    } catch (err) {
      console.error('Login error:', err);
      // Handle different types of errors with specific messages
      if (err instanceof ApiError) {
        // API error with status code
        if (err.status === 408 || err.message.includes('timeout') || err.message.includes('timed out')) {
          error = 'Request timed out. The server is not responding. Please check your connection and ensure the server is running.';
        } else if (err.status === 400) {
          // Bad request - usually authentication errors
          error = err.message || 'Invalid username or PIN. Please check your credentials.';
        } else if (err.status === 401) {
          error = 'Authentication failed. Please check your credentials.';
        } else if (err.status === 403) {
          error = 'Access denied. Please contact support.';
        } else if (err.status === 404) {
          error = 'Server endpoint not found. Please check your connection settings.';
        } else if (err.status >= 500) {
          error = 'Server error. Please try again later or contact support.';
        } else {
          error = err.message || 'Login failed. Please check your credentials.';
        }
      } else if (err instanceof Error) {
        // Generic error - check for network issues
        if (err.message && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.message.includes('network'))) {
          error = 'Unable to connect to the server. Please check your internet connection and ensure the server is running.';
        } else if (err.message) {
          error = err.message;
        } else {
          error = 'Login failed. Please check your credentials.';
        }
      } else {
        error = 'Login failed. Please check your credentials.';
      }
      console.log('Error message set to:', error);
    } finally {
      loading = false;
    }
  }

  async function loadChats() {
    try {
      const chatsList = await api.getChats();
      chats.set(chatsList);
    } catch (err) {
      console.error('Failed to load chats:', err);
    }
  }

  function handleKeyPress(event) {
    if (event.key === 'Enter' && !loading) {
      handleLogin();
    }
  }

  function clearError() {
    if (error) {
      error = '';
    }
  }
</script>

<div class="login-container">
  <div class="login-box">
    <h1>Chat Login</h1>
    <form on:submit|preventDefault={handleLogin}>
      <div class="form-group">
        <label for="username">Username</label>
        <input
          id="username"
          type="text"
          bind:value={username}
          on:keypress={handleKeyPress}
          on:input={clearError}
          disabled={loading}
          autocomplete="username"
        />
      </div>
      <div class="form-group">
        <label for="pin">PIN</label>
        <input
          id="pin"
          type="password"
          bind:value={pin}
          on:keypress={handleKeyPress}
          on:input={clearError}
          disabled={loading}
          autocomplete="current-password"
        />
      </div>
      {#if error}
        <div class="error" role="alert">
          <strong>Error:</strong> {error}
        </div>
      {/if}
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
      <div class="debug-link">
        <button type="button" class="link-button" on:click={goToDebug}>
          <svg class="debug-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M8 0C3.58 0 0 3.58 0 8s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6s2.69-6 6-6 6 2.69 6 6-2.69 6-6 6zm-1-9H7v4h2V5zm0 5H7v2h2v-2z" fill="currentColor"/>
          </svg>
          <span>Debug and Develop</span>
        </button>
      </div>
    </form>
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background-color: #f5f5f5;
  }

  .login-box {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 400px;
  }

  .login-box h1 {
    margin: 0 0 1.5rem 0;
    text-align: center;
    color: #333;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    color: #555;
    font-weight: 500;
  }

  .form-group input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    box-sizing: border-box;
  }

  .form-group input:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .form-group input:disabled {
    background-color: #f0f0f0;
    cursor: not-allowed;
  }

  .error {
    color: #d32f2f;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background-color: #ffebee;
    border: 1px solid #d32f2f;
    border-radius: 4px;
    font-size: 0.9rem;
    display: block;
    animation: fadeIn 0.3s ease-in;
  }

  .error strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  button {
    width: 100%;
    padding: 0.75rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  button:hover:not(:disabled) {
    background-color: #357abd;
  }

  button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }

  .debug-link {
    margin-top: 0.75rem;
    text-align: center;
  }

  .link-button {
    background: none !important;
    background-color: transparent !important;
    border: none;
    color: #6b7280;
    text-decoration: none;
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    margin: 0;
    width: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    font-weight: 400;
    transition: none;
  }

  .link-button:hover {
    background: none !important;
    background-color: transparent !important;
  }

  .debug-icon {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }
</style>
