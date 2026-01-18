    <script>
  import { onMount } from 'svelte';
  import { api } from '../services/api.js';
  import { auth } from '../stores/auth.js';
  import { chats } from '../stores/chats.js';
  import { activeChatId } from '../stores/chats.js';
  import { currentView } from '../stores/view.js';
  import { sendWebSocketMessage } from '../services/websocket.js';
  import { get } from 'svelte/store';

  let users = [];
  let loading = false;
  let error = '';
  let searchQuery = '';

  $: filteredUsers = users.filter(user => 
    user.id !== $auth.userId && 
    user.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  onMount(async () => {
    await loadUsers();
  });

  async function loadUsers() {
    loading = true;
    error = '';
    try {
      users = await api.getAllUsers();
    } catch (err) {
      console.error('Failed to load users:', err);
      error = 'Failed to load users. Please try again.';
    } finally {
      loading = false;
    }
  }

  async function startChatWithUser(user) {
    try {
      // Check if DM already exists
      const existingChat = $chats.find(chat => {
        // For direct messages, check if both users are members
        if (chat.type === 'direct') {
          // We'll need to check members, but for now, try to create
          return false;
        }
        return false;
      });

      // Create new DM
      const newChat = await api.createDM($auth.userId, user.id);
      
      // Add to chats list
      chats.update(chatsList => {
        // Check if chat already exists
        if (!chatsList.find(c => c.id === newChat.id)) {
          return [...chatsList, { ...newChat, other_user_name: user.username }];
        }
        return chatsList;
      });

      // Select the chat
      activeChatId.set(newChat.id);
      
      // Switch to chats view
      currentView.set('chats');
      
      // Open chat via WebSocket
      sendWebSocketMessage('chat.open', { 
        chat_id: newChat.id,
        user_id: $auth.userId
      });
    } catch (err) {
      console.error('Failed to create chat:', err);
      error = 'Failed to start chat. Please try again.';
    }
  }

  function goToChats() {
    currentView.set('chats');
  }
</script>

<div class="dashboard">
  <div class="dashboard-header">
    <h2>Dashboard</h2>
    <button class="chats-button" on:click={goToChats}>
      ← Back to Chats
    </button>
  </div>
  
  <div class="dashboard-content">
    <div class="search-section">
      <input
        type="text"
        class="search-input"
        bind:value={searchQuery}
        placeholder="Search users..."
      />
      <button class="refresh-button" on:click={loadUsers} disabled={loading}>
        {loading ? 'Loading...' : '🔄 Refresh'}
      </button>
    </div>

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    {#if loading && users.length === 0}
      <div class="loading-state">Loading users...</div>
    {:else if filteredUsers.length === 0}
      <div class="empty-state">
        {searchQuery ? 'No users found matching your search.' : 'No other users available.'}
      </div>
    {:else}
      <div class="users-list">
        <div class="users-header">
          <h3>Active Users ({filteredUsers.length})</h3>
        </div>
        {#each filteredUsers as user (user.id)}
          <div class="user-item" role="button" tabindex="0" on:click={() => startChatWithUser(user)} on:keypress={(e) => e.key === 'Enter' && startChatWithUser(user)}>
            <div class="user-avatar">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div class="user-info">
              <div class="user-name">{user.username}</div>
              <div class="user-meta">User ID: {user.id}</div>
            </div>
            <button class="chat-button" on:click|stopPropagation={() => startChatWithUser(user)}>
              Start Chat
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #f8f9fa;
  }

  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background-color: white;
  }

  .dashboard-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #333;
  }

  .chats-button {
    padding: 0.5rem 1rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .chats-button:hover {
    background-color: #357abd;
  }

  .dashboard-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
  }

  .search-section {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .search-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .search-input:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .refresh-button {
    padding: 0.75rem 1rem;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    white-space: nowrap;
  }

  .refresh-button:hover:not(:disabled) {
    background-color: #e9ecef;
  }

  .refresh-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error-message {
    padding: 1rem;
    background-color: #ffebee;
    border: 1px solid #d32f2f;
    border-radius: 4px;
    color: #d32f2f;
    margin-bottom: 1rem;
  }

  .loading-state,
  .empty-state {
    text-align: center;
    padding: 3rem;
    color: #999;
  }

  .users-list {
    background-color: white;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e0e0e0;
  }

  .users-header {
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background-color: #f8f9fa;
  }

  .users-header h3 {
    margin: 0;
    font-size: 1rem;
    color: #333;
  }

  .user-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .user-item:hover {
    background-color: #f5f5f5;
  }

  .user-item:last-child {
    border-bottom: none;
  }

  .user-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background-color: #4a90e2;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 1.25rem;
    flex-shrink: 0;
  }

  .user-info {
    flex: 1;
    min-width: 0;
  }

  .user-name {
    font-weight: 500;
    color: #333;
    margin-bottom: 0.25rem;
  }

  .user-meta {
    font-size: 0.875rem;
    color: #666;
  }

  .chat-button {
    padding: 0.5rem 1rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    white-space: nowrap;
  }

  .chat-button:hover {
    background-color: #357abd;
  }
</style>
