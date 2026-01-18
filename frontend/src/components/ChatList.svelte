<script>
  import { onMount, onDestroy } from 'svelte';
  import { chats } from '../stores/chats.js';
  import { activeChatId } from '../stores/chats.js';
  import { sendWebSocketMessage } from '../services/websocket.js';
  import { currentView } from '../stores/view.js';
  import { auth } from '../stores/auth.js';
  import { api } from '../services/api.js';
  import { get } from 'svelte/store';

  let dropdownRef;
  let newChatButtonRef;

  let showDropdown = false;
  let showGroupChatModal = false;
  let showDMModal = false;
  let users = [];
  let loading = false;
  let error = '';
  let searchQuery = '';
  let groupChatTitle = '';
  let selectedMembers = new Set();

  $: filteredUsers = users.filter(user => 
    user.id !== $auth.userId && 
    user.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  let clickOutsideHandler;

  onMount(async () => {
    await loadUsers();
    
    // Close dropdown when clicking outside
    clickOutsideHandler = (event) => {
      if (showDropdown && 
          dropdownRef && 
          !dropdownRef.contains(event.target) && 
          newChatButtonRef && 
          !newChatButtonRef.contains(event.target)) {
        closeDropdown();
      }
    };
    
    document.addEventListener('click', clickOutsideHandler);
  });

  onDestroy(() => {
    if (clickOutsideHandler) {
      document.removeEventListener('click', clickOutsideHandler);
    }
  });

  function selectChat(chat) {
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChatList.svelte:9',message:'selectChat called',data:{chatId:chat.id,currentActiveChatId:get(activeChatId)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
    // #endregion
    activeChatId.set(chat.id);
    sendWebSocketMessage('chat.open', { 
      chat_id: chat.id,
      user_id: get(auth).userId
    });
  }

  function getChatTitle(chat) {
    return chat.title || chat.other_user_name || `Chat ${chat.id}`;
  }

  function toggleDropdown() {
    showDropdown = !showDropdown;
  }

  function closeDropdown() {
    showDropdown = false;
  }

  function openDirectMessage() {
    closeDropdown();
    showDMModal = true;
    searchQuery = '';
    loadUsers();
  }

  function openGroupChat() {
    closeDropdown();
    showGroupChatModal = true;
    groupChatTitle = '';
    selectedMembers.clear();
    loadUsers();
  }

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
      const newChat = await api.createDM($auth.userId, user.id);
      
      chats.update(chatsList => {
        if (!chatsList.find(c => c.id === newChat.id)) {
          return [...chatsList, { ...newChat, other_user_name: user.username }];
        }
        return chatsList;
      });

      activeChatId.set(newChat.id);
      currentView.set('chats');
      
      sendWebSocketMessage('chat.open', { 
        chat_id: newChat.id,
        user_id: $auth.userId
      });

      showDMModal = false;
    } catch (err) {
      console.error('Failed to create chat:', err);
      error = 'Failed to start chat. Please try again.';
    }
  }

  function toggleMemberSelection(userId) {
    if (selectedMembers.has(userId)) {
      selectedMembers.delete(userId);
    } else {
      selectedMembers.add(userId);
    }
    selectedMembers = selectedMembers;
  }

  async function createGroupChat() {
    if (!groupChatTitle.trim()) {
      error = 'Please enter a group chat title';
      return;
    }

    if (selectedMembers.size === 0) {
      error = 'Please select at least one member';
      return;
    }

    try {
      error = '';
      const memberIds = Array.from(selectedMembers);
      memberIds.push($auth.userId);
      
      const newChat = await api.createGroupChat(groupChatTitle.trim(), memberIds);
      
      chats.update(chatsList => {
        if (!chatsList.find(c => c.id === newChat.id)) {
          return [...chatsList, newChat];
        }
        return chatsList;
      });

      activeChatId.set(newChat.id);
      currentView.set('chats');
      
      sendWebSocketMessage('chat.open', { 
        chat_id: newChat.id,
        user_id: $auth.userId
      });

      showGroupChatModal = false;
      groupChatTitle = '';
      selectedMembers.clear();
    } catch (err) {
      console.error('Failed to create group chat:', err);
      error = err.message || 'Failed to create group chat. Please try again.';
    }
  }

  function closeGroupChatModal() {
    showGroupChatModal = false;
    groupChatTitle = '';
    selectedMembers.clear();
    error = '';
  }

  function closeDMModal() {
    showDMModal = false;
    error = '';
  }
</script>

<div class="chat-list">
  <div class="chat-list-header">
    <h2>Chats</h2>
    <div class="new-chat-container">
      <button 
        class="new-chat-button" 
        bind:this={newChatButtonRef}
        on:click={toggleDropdown} 
        title="Start new chat"
      >
        <span class="plus-icon">+</span>
        New Chat
        <span class="dropdown-arrow">▼</span>
      </button>
      {#if showDropdown}
        <div class="dropdown-menu" bind:this={dropdownRef}>
          <button class="dropdown-item" on:click={openDirectMessage}>
            <span class="dropdown-icon">💬</span>
            Direct Message
          </button>
          <button class="dropdown-item" on:click={openGroupChat}>
            <span class="dropdown-icon">👥</span>
            Group Chat
          </button>
        </div>
      {/if}
    </div>
  </div>
  <div class="chat-list-content">
    {#each $chats as chat (chat.id)}
      <div
        class="chat-item"
        class:active={$activeChatId === chat.id}
        on:click={() => selectChat(chat)}
        role="button"
        tabindex="0"
        on:keypress={(e) => e.key === 'Enter' && selectChat(chat)}
      >
        <div class="chat-type-label" class:group={chat.type === 'group'} class:direct={chat.type === 'direct'}>
          {chat.type === 'group' ? 'Group' : 'DM'}
        </div>
        <div class="chat-item-content">
          <div class="chat-title">{getChatTitle(chat)}</div>
        </div>
        {#if chat.unread_count > 0}
          <div class="unread-badge">{chat.unread_count}</div>
        {/if}
      </div>
    {:else}
      <div class="empty-state">No chats available</div>
    {/each}
  </div>
</div>

<!-- Direct Message Modal -->
{#if showDMModal}
  <div class="modal-overlay" on:click={closeDMModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Start Direct Message</h3>
        <button class="modal-close" on:click={closeDMModal}>×</button>
      </div>
      <div class="modal-body">
        <div class="search-section">
          <input
            type="text"
            class="search-input"
            bind:value={searchQuery}
            placeholder="Search users..."
          />
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
            {#each filteredUsers as user (user.id)}
              <div 
                class="user-item" 
                on:click={() => startChatWithUser(user)}
                role="button"
                tabindex="0"
                on:keypress={(e) => e.key === 'Enter' && startChatWithUser(user)}
              >
                <div class="user-avatar">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div class="user-info">
                  <div class="user-name">{user.username}</div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Group Chat Modal -->
{#if showGroupChatModal}
  <div class="modal-overlay" on:click={closeGroupChatModal}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Create Group Chat</h3>
        <button class="modal-close" on:click={closeGroupChatModal}>×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label for="group-title">Group Name</label>
          <input
            id="group-title"
            type="text"
            class="form-input"
            bind:value={groupChatTitle}
            placeholder="Enter group name..."
            maxlength="128"
          />
        </div>
        <div class="form-group">
          <label>Select Members ({selectedMembers.size} selected)</label>
          <div class="members-list">
            {#each filteredUsers as user (user.id)}
              <div 
                class="member-item"
                class:selected={selectedMembers.has(user.id)}
                on:click={() => toggleMemberSelection(user.id)}
                role="button"
                tabindex="0"
                on:keypress={(e) => e.key === 'Enter' && toggleMemberSelection(user.id)}
              >
                <div class="member-avatar">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div class="member-name">{user.username}</div>
                {#if selectedMembers.has(user.id)}
                  <div class="checkmark">✓</div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
        {#if error}
          <div class="error-message">{error}</div>
        {/if}
      </div>
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeGroupChatModal}>Cancel</button>
        <button 
          class="create-button" 
          on:click={createGroupChat}
          disabled={!groupChatTitle.trim() || selectedMembers.size === 0}
        >
          Create Group
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .chat-list {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #f8f9fa;
    border-right: 1px solid #e0e0e0;
  }

  .chat-list-header {
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background-color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
  }

  .chat-list-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #333;
    flex: 1;
  }

  .new-chat-container {
    position: relative;
  }

  .new-chat-button {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 0.75rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    white-space: nowrap;
  }

  .new-chat-button:hover {
    background-color: #357abd;
  }

  .plus-icon {
    font-size: 1.125rem;
    font-weight: 600;
    line-height: 1;
  }

  .dropdown-arrow {
    font-size: 0.625rem;
    margin-left: 0.25rem;
  }

  .dropdown-menu {
    position: absolute;
    top: calc(100% + 0.25rem);
    right: 0;
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    min-width: 180px;
    z-index: 1000;
    overflow: hidden;
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    font-size: 0.875rem;
    color: #333;
    transition: background-color 0.2s;
  }

  .dropdown-item:hover {
    background-color: #f5f5f5;
  }

  .dropdown-item:first-child {
    border-bottom: 1px solid #f0f0f0;
  }

  .dropdown-icon {
    font-size: 1rem;
  }

  .chat-list-content {
    flex: 1;
    overflow-y: auto;
  }

  .chat-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    cursor: pointer;
    border-bottom: 1px solid #e0e0e0;
    background-color: white;
    transition: background-color 0.2s;
    gap: 0.75rem;
  }

  .chat-item:hover {
    background-color: #f5f5f5;
  }

  .chat-item.active {
    background-color: #e3f2fd;
  }

  .chat-type-label {
    font-size: 0.625rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    flex-shrink: 0;
    min-width: 36px;
    text-align: center;
  }

  .chat-type-label.group {
    background-color: #4a90e2;
    color: white;
  }

  .chat-type-label.direct {
    background-color: #e3f2fd;
    color: #1976d2;
  }

  .chat-item-content {
    flex: 1;
    min-width: 0;
  }

  .chat-title {
    font-weight: 500;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .unread-badge {
    background-color: #4a90e2;
    color: white;
    border-radius: 12px;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    min-width: 20px;
    text-align: center;
  }

  .empty-state {
    padding: 2rem;
    text-align: center;
    color: #999;
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background-color: white;
    border-radius: 8px;
    width: 90%;
    max-width: 500px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .modal-header h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #333;
  }

  .modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #999;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-close:hover {
    color: #333;
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
  }

  .search-section {
    margin-bottom: 1rem;
  }

  .search-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    box-sizing: border-box;
  }

  .search-input:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .error-message {
    padding: 0.75rem;
    background-color: #ffebee;
    border: 1px solid #d32f2f;
    border-radius: 4px;
    color: #d32f2f;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .loading-state {
    text-align: center;
    padding: 2rem;
    color: #999;
  }

  .users-list {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
  }

  .user-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    cursor: pointer;
    transition: background-color 0.2s;
    border-bottom: 1px solid #f0f0f0;
  }

  .user-item:hover {
    background-color: #f5f5f5;
  }

  .user-item:last-child {
    border-bottom: none;
  }

  .user-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #4a90e2;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 1rem;
    flex-shrink: 0;
  }

  .user-info {
    flex: 1;
  }

  .user-name {
    font-weight: 500;
    color: #333;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #333;
  }

  .form-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    box-sizing: border-box;
  }

  .form-input:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .members-list {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
  }

  .member-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    cursor: pointer;
    transition: background-color 0.2s;
    border-bottom: 1px solid #f0f0f0;
  }

  .member-item:last-child {
    border-bottom: none;
  }

  .member-item:hover {
    background-color: #f5f5f5;
  }

  .member-item.selected {
    background-color: #e3f2fd;
  }

  .member-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #4a90e2;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 1rem;
    flex-shrink: 0;
  }

  .member-name {
    flex: 1;
    font-weight: 500;
    color: #333;
  }

  .checkmark {
    color: #4a90e2;
    font-weight: bold;
    font-size: 1.25rem;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
  }

  .cancel-button,
  .create-button {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .cancel-button {
    background-color: #f5f5f5;
    color: #333;
  }

  .cancel-button:hover {
    background-color: #e9ecef;
  }

  .create-button {
    background-color: #28a745;
    color: white;
  }

  .create-button:hover:not(:disabled) {
    background-color: #218838;
  }

  .create-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
</style>
