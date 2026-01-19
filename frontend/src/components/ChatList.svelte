<script>
  import { onMount, onDestroy } from 'svelte';
  import { chats } from '../stores/chats.js';
  import { activeChatId } from '../stores/chats.js';
  import { sendWebSocketMessage } from '../services/websocket.js';
  import { currentView } from '../stores/view.js';
  import { auth } from '../stores/auth.js';
  import { api } from '../services/api.js';
  import { backgroundSettings } from '../stores/backgroundSettings.js';
  import { get } from 'svelte/store';
  import { generateAvatar } from '../utils/avatar.js';

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
  
  // Chat menu state
  let openChatMenuId = null;
  let chatMenuRefs = {};
  let showDeleteConfirm = false;
  let chatToDelete = null;
  let showBackgroundSettings = false;
  
  // Local copy of background settings for editing
  let localBgSettings = {
    primaryColor: '#e5e5f7', // Back Color (background)
    secondaryColor: '#444cf7', // Front Color (pattern)
    opacity: 0.8, // Match magicpattern.design default
    spacing: 30,
    patternType: 'zigzag'
  };
  
  // Sync with store
  $: {
    const storeSettings = $backgroundSettings;
    localBgSettings = { ...storeSettings };
  }

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
      
      // Close chat menu when clicking outside
      if (openChatMenuId !== null) {
        const menuRef = chatMenuRefs[openChatMenuId];
        if (menuRef && !menuRef.contains(event.target)) {
          // Check if click was on the three dots button
          const threeDotsButton = event.target.closest('.chat-menu-button');
          if (!threeDotsButton) {
            closeChatMenu();
          }
        }
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

  function getChatAvatar(chat) {
    // For direct messages, use other_user_name; for groups, use chat title or ID
    const avatarId = chat.type === 'direct' 
      ? (chat.other_user_name || chat.id)
      : (chat.title || chat.id);
    return generateAvatar(avatarId, 48);
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

  function toggleChatMenu(chatId, event) {
    event.stopPropagation();
    if (openChatMenuId === chatId) {
      openChatMenuId = null;
    } else {
      openChatMenuId = chatId;
    }
  }

  function closeChatMenu() {
    openChatMenuId = null;
  }

  function openDeleteConfirm(chat, event) {
    event.stopPropagation();
    chatToDelete = chat;
    showDeleteConfirm = true;
    closeChatMenu();
  }

  function closeDeleteConfirm() {
    showDeleteConfirm = false;
    chatToDelete = null;
  }
  
  function openBackgroundSettings(event) {
    if (event) event.stopPropagation();
    showBackgroundSettings = true;
    closeChatMenu();
  }
  
  function closeBackgroundSettings() {
    showBackgroundSettings = false;
  }
  
  function resetBackgroundSettings() {
    backgroundSettings.reset();
    localBgSettings = { ...$backgroundSettings };
  }

  async function deleteChat() {
    if (!chatToDelete) return;
    
    try {
      await api.leaveChat(chatToDelete.id, $auth.userId);
      
      // Remove chat from list
      chats.update(chatsList => chatsList.filter(c => c.id !== chatToDelete.id));
      
      // If this was the active chat, clear it
      if ($activeChatId === chatToDelete.id) {
        activeChatId.set(null);
      }
      
      closeDeleteConfirm();
    } catch (err) {
      console.error('Failed to delete chat:', err);
      error = err.message || 'Failed to delete chat. Please try again.';
      closeDeleteConfirm();
    }
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
        <div class="chat-avatar">
          <img src={getChatAvatar(chat)} alt="" />
        </div>
        <div class="chat-item-content">
          <div class="chat-type-label" class:group={chat.type === 'group'} class:direct={chat.type === 'direct'}>
            {chat.type === 'group' ? 'Group' : 'Direct Message'}
          </div>
          <div class="chat-title">{getChatTitle(chat)}</div>
        </div>
        <div class="chat-item-actions">
          {#if chat.unread_count > 0}
            <div class="unread-badge">{chat.unread_count}</div>
          {/if}
          <button
            class="chat-menu-button"
            on:click={(e) => toggleChatMenu(chat.id, e)}
            title="Chat options"
            tabindex="0"
          >
            <span class="three-dots">⋯</span>
          </button>
          {#if openChatMenuId === chat.id}
            <div 
              class="chat-menu-dropdown"
              bind:this={chatMenuRefs[chat.id]}
              on:click|stopPropagation
            >
              <button 
                class="chat-menu-item"
                on:click={(e) => openBackgroundSettings(e)}
              >
                <span class="menu-icon">🎨</span>
                Background Settings
              </button>
              <button 
                class="chat-menu-item delete-chat"
                on:click={(e) => openDeleteConfirm(chat, e)}
              >
                <span class="menu-icon">🗑️</span>
                Delete Chat
              </button>
            </div>
          {/if}
        </div>
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

<!-- Background Settings Modal -->
{#if showBackgroundSettings}
  <div class="modal-overlay" on:click={closeBackgroundSettings}>
    <div class="modal-content background-settings-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Background Settings</h3>
        <button class="modal-close" on:click={closeBackgroundSettings}>×</button>
      </div>
      <div class="modal-body">
        <div class="settings-section">
          <label class="settings-label">
            <span>Pattern Type</span>
            <select value={localBgSettings.patternType} on:change={(e) => {
              localBgSettings.patternType = e.target.value;
              backgroundSettings.update(localBgSettings);
            }}>
              <option value="zigzag">ZigZag</option>
              <option value="isometric">Isometric</option>
              <option value="polka">Polka v1</option>
              <option value="polka-v2">Polka v2</option>
              <option value="cross">Cross</option>
            </select>
          </label>
        </div>
        
        <div class="settings-section">
          <label class="settings-label">
            <span>Back Color</span>
            <input type="color" value={localBgSettings.primaryColor} on:input={(e) => {
              localBgSettings.primaryColor = e.target.value;
              backgroundSettings.update(localBgSettings);
            }} />
          </label>
        </div>
        
        <div class="settings-section">
          <label class="settings-label">
            <span>Front Color</span>
            <input type="color" value={localBgSettings.secondaryColor} on:input={(e) => {
              localBgSettings.secondaryColor = e.target.value;
              backgroundSettings.update(localBgSettings);
            }} />
          </label>
        </div>
        
        <div class="settings-section">
          <label class="settings-label">
            <span>Opacity: {Math.round(localBgSettings.opacity * 100)}%</span>
            <input type="range" min="0" max="1" step="0.01" value={localBgSettings.opacity} on:input={(e) => {
              localBgSettings.opacity = parseFloat(e.target.value);
              backgroundSettings.update(localBgSettings);
            }} />
          </label>
        </div>
        
        <div class="settings-section">
          <label class="settings-label">
            <span>Spacing: {localBgSettings.spacing}px</span>
            <input type="range" min="10" max="60" step="5" value={localBgSettings.spacing} on:input={(e) => {
              localBgSettings.spacing = parseInt(e.target.value);
              backgroundSettings.update(localBgSettings);
            }} />
          </label>
        </div>
        
        <div class="settings-section">
          <label class="settings-label">
          </label>
        </div>
        
        <div class="modal-actions">
          <button class="reset-button" on:click={resetBackgroundSettings}>Reset to Default</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Chat Confirmation Modal -->
{#if showDeleteConfirm && chatToDelete}
  <div class="modal-overlay" on:click={closeDeleteConfirm}>
    <div class="modal-content" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Delete Chat</h3>
        <button class="modal-close" on:click={closeDeleteConfirm}>×</button>
      </div>
      <div class="modal-body">
        <p>
          Are you sure you want to delete this chat?
          {#if chatToDelete.type === 'group'}
            <br><strong>You will leave the group chat.</strong>
          {:else}
            <br><strong>This chat will be removed from your chat list.</strong>
          {/if}
        </p>
        <p class="chat-name-preview">
          <strong>{getChatTitle(chatToDelete)}</strong>
        </p>
        {#if error}
          <div class="error-message">{error}</div>
        {/if}
      </div>
      <div class="modal-footer">
        <button class="cancel-button" on:click={closeDeleteConfirm}>Cancel</button>
        <button class="delete-button" on:click={deleteChat}>
          Delete Chat
        </button>
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

  .chat-item-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
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

  .chat-menu-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
    color: #666;
    font-size: 1.25rem;
    line-height: 1;
    width: 28px;
    height: 28px;
  }

  .chat-menu-button:hover {
    background-color: #e0e0e0;
    color: #333;
  }

  .three-dots {
    font-weight: bold;
    transform: rotate(90deg);
    display: inline-block;
  }

  .chat-menu-dropdown {
    position: absolute;
    top: calc(100% + 0.25rem);
    right: 0;
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    min-width: 160px;
    z-index: 1001;
    overflow: hidden;
  }

  .chat-menu-item {
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

  .chat-menu-item:hover {
    background-color: #f5f5f5;
  }

  .chat-menu-item.delete-chat {
    color: #d32f2f;
  }

  .chat-menu-item.delete-chat:hover {
    background-color: #ffebee;
  }

  .menu-icon {
    font-size: 1rem;
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
    background-color: white !important;
    border-radius: 8px;
    width: 90%;
    max-width: 500px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    opacity: 1 !important;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background-color: white;
  }
  
  .background-settings-modal {
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    background-color: white;
    opacity: 1;
  }

  .background-settings-modal .modal-body {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-y: auto;
    background-color: white !important;
    opacity: 1 !important;
  }

  .settings-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .settings-label {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .settings-label span {
    font-weight: 500;
    color: #333;
  }

  .settings-label input[type="color"] {
    width: 100%;
    height: 40px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    cursor: pointer;
    background-color: white;
  }

  .settings-label input[type="range"] {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #e0e0e0;
    outline: none;
    -webkit-appearance: none;
  }

  .settings-label input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #4a90e2;
    cursor: pointer;
  }

  .settings-label input[type="range"]::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #4a90e2;
    cursor: pointer;
    border: none;
  }

  .settings-label select {
    padding: 0.5rem;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 0.875rem;
    background: white;
    cursor: pointer;
  }

  .settings-label select:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .reset-button {
    padding: 0.625rem 1.25rem;
    background-color: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    margin-top: 0.5rem;
  }

  .reset-button:hover {
    background-color: #c82333;
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

  .chat-name-preview {
    margin-top: 1rem;
    padding: 0.75rem;
    background-color: #f5f5f5;
    border-radius: 4px;
    text-align: center;
  }

  .delete-button {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
    background-color: #d32f2f;
    color: white;
  }

  .delete-button:hover {
    background-color: #b71c1c;
  }
</style>
