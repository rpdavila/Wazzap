<script>
  import { auth } from '../stores/auth.js';
  import { api } from '../services/api.js';
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
      
      auth.login(username.trim(), response.jwt, response.session_id);
      
      // Connect WebSocket
      connectWebSocket();
      
      // Fetch chats
      await loadChats();
      
      // Clear any previous message data
      messages.clear();
      activeChatId.set(null);
      
    } catch (err) {
      if (err instanceof Error) {
        error = err.message || 'Login failed. Please check your credentials.';
      } else {
        error = 'Login failed. Please check your credentials.';
      }
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
          disabled={loading}
          autocomplete="current-password"
        />
      </div>
      {#if error}
        <div class="error">{error}</div>
      {/if}
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
      <div class="debug-link">
        <button type="button" class="link-button" on:click={goToDebug}>Debug and Develop</button>
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
    padding: 0.5rem;
    background-color: #ffebee;
    border-radius: 4px;
    font-size: 0.9rem;
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
    margin-top: 1rem;
    text-align: center;
  }

  .link-button {
    background: none;
    border: none;
    color: #4a90e2;
    text-decoration: none;
    font-size: 0.875rem;
    cursor: pointer;
    padding: 0;
    margin: 0;
  }

  .link-button:hover {
    text-decoration: underline;
  }
</style>
