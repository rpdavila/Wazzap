<script>
  import { onMount, onDestroy } from 'svelte';
  import { auth } from './stores/auth.js';
  import { websocket } from './stores/websocket.js';
  import { chats } from './stores/chats.js';
  import { messages } from './stores/messages.js';
  import { activeChatId } from './stores/chats.js';
  import { connectWebSocket, disconnectWebSocket } from './services/websocket.js';
  import { api } from './services/api.js';
  import Login from './components/Login.svelte';
  import ChatList from './components/ChatList.svelte';
  import ChatView from './components/ChatView.svelte';
  import DebugPage from './components/DebugPage.svelte';
  import { currentView } from './stores/view.js';

  onMount(async () => {
    // If already authenticated, connect WebSocket and load chats
    if ($auth.isAuthenticated) {
      connectWebSocket();
      await loadChats();
    }
  });

  onDestroy(() => {
    disconnectWebSocket();
  });

  async function loadChats() {
    try {
      const chatsList = await api.getChats();
      chats.set(chatsList);
    } catch (err) {
      console.error('Failed to load chats:', err);
    }
  }

  function handleLogout() {
    disconnectWebSocket();
    auth.logout();
    messages.clear();
    activeChatId.set(null);
    chats.set([]);
  }

  $: wsStatus = $websocket.connected ? 'connected' : 'disconnected';
</script>

{#if $currentView === 'debug'}
  <DebugPage />
{:else if !$auth.isAuthenticated}
  <Login />
{:else}
  <div class="app">
    <header class="app-header">
      <div class="header-content">
        <div class="user-info">
          <span class="username">{$auth.username}</span>
        </div>
        <div class="header-right">
          <div class="ws-status" class:connected={$websocket.connected}>
            <span class="status-indicator"></span>
            {wsStatus}
          </div>
          <button class="logout-button" on:click={handleLogout}>Logout</button>
        </div>
      </div>
    </header>
    
    <div class="app-body">
      <aside class="sidebar">
        <ChatList />
      </aside>
      <main class="main-content">
        <ChatView />
      </main>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  }

  :global(#app) {
    height: 100vh;
    overflow: hidden;
  }

  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .app-header {
    background-color: #fff;
    border-bottom: 1px solid #e0e0e0;
    padding: 0 1rem;
    height: 60px;
    display: flex;
    align-items: center;
  }

  .header-content {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .user-info {
    display: flex;
    align-items: center;
  }

  .username {
    font-weight: 500;
    color: #333;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .ws-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #666;
  }

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #d32f2f;
  }

  .ws-status.connected .status-indicator {
    background-color: #4caf50;
  }

  .logout-button {
    padding: 0.5rem 1rem;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .logout-button:hover {
    background-color: #d32f2f;
  }

  .app-body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .sidebar {
    width: 300px;
    flex-shrink: 0;
    overflow: hidden;
  }

  .main-content {
    flex: 1;
    overflow: hidden;
  }
</style>
