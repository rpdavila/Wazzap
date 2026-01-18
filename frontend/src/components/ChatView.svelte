<script>
  import { onMount, onDestroy } from 'svelte';
  import { activeChatId, chats } from '../stores/chats.js';
  import { messages } from '../stores/messages.js';
  import { auth } from '../stores/auth.js';
  import { api } from '../services/api.js';
  import { sendWebSocketMessage, markChatAsRead } from '../services/websocket.js';
  import { get } from 'svelte/store';

  let messageInput = '';
  let messageContainer;
  let isAtBottom = true;
  let mediaModal = null;
  let mediaModalUrl = '';
  let loadingMessages = false;
  let previousChatId = null;
  let showMembersModal = false;
  let chatMembers = [];
  let allUsers = [];
  let showAddMemberModal = false;
  let loadingMembers = false;
  let showReadStatusModal = false;
  let selectedMessageForReadStatus = null;
  let readStatusMembers = [];

  $: currentChat = $chats.find(c => c.id === $activeChatId);
  $: chatMessages = $messages[$activeChatId] || [];
  $: currentUsername = $auth.username;
  $: isGroupChat = currentChat?.type === 'group';
  
  // Load chat members when chat changes and it's a group chat
  $: if (isGroupChat && $activeChatId && chatMembers.length === 0) {
    loadChatMembers();
  }

  $: if ($activeChatId && $activeChatId !== previousChatId) {
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChatView.svelte:22',message:'Active chat changed',data:{newChatId:$activeChatId,previousChatId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
    // #endregion
    previousChatId = $activeChatId;
    loadMessages();
    // Load chat members if group chat
    if (isGroupChat) {
      loadChatMembers();
    }
    // Open the chat via WebSocket to receive messages
    sendWebSocketMessage('chat.open', {
      chat_id: $activeChatId,
      user_id: $auth.userId
    });
  }

  $: if (chatMessages.length > 0 && isAtBottom) {
    scrollToBottom();
  }

  async function loadMessages() {
    // Capture activeChatId at the start to avoid race conditions
    const currentChatId = $activeChatId;
    if (!currentChatId || loadingMessages) return;

    loadingMessages = true;
    try {
      const messageList = await api.getMessages(currentChatId);
      messages.setMessages(currentChatId, messageList);
      
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChatView.svelte:44',message:'loadMessages completed',data:{currentChatId,capturedChatId:currentChatId,reactiveChatId:$activeChatId,messageListLength:messageList.length,chatIdChanged:currentChatId !== $activeChatId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
      // #endregion
      
      // Mark messages as read - use captured chatId to avoid race conditions
      if (messageList.length > 0 && currentChatId) {
        const lastMessage = messageList[messageList.length - 1];
        if (lastMessage && lastMessage.id) {
          // #region agent log
          fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ChatView.svelte:52',message:'Calling markChatAsRead',data:{currentChatId,lastMessageId:lastMessage.id,messageListLength:messageList.length,reactiveChatId:$activeChatId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'M'})}).catch(()=>{});
          // #endregion
          markChatAsRead(currentChatId, lastMessage.id);
        }
      }
      
      // Scroll to bottom after loading
      setTimeout(() => {
        scrollToBottom();
        isAtBottom = true;
        loadingMessages = false;
      }, 100);
    } catch (err) {
      console.error('Failed to load messages:', err);
      loadingMessages = false;
    }
  }

  function scrollToBottom() {
    if (messageContainer) {
      messageContainer.scrollTop = messageContainer.scrollHeight;
    }
  }

  function handleScroll() {
    if (!messageContainer) return;
    const { scrollTop, scrollHeight, clientHeight } = messageContainer;
    isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
  }

  function sendMessage() {
    if (!messageInput.trim() || !$activeChatId) return;

    // Ensure we're connected to this chat before sending
    sendWebSocketMessage('chat.open', {
      chat_id: $activeChatId,
      user_id: $auth.userId
    });

    const message = {
      chat_id: $activeChatId,
      sender_id: $auth.userId,
      content: messageInput.trim(),
      msg_type: 'text'
    };

    sendWebSocketMessage('message.send', message);
    messageInput = '';
  }

  async function handleMediaUpload(event) {
    const file = event.target.files[0];
    if (!file || !$activeChatId) return;

    // Validate file type (images or GIFs)
    if (!file.type.startsWith('image/')) {
      alert('Please upload an image file');
      return;
    }

    try {
      const response = await api.uploadMedia(file);
      
      const message = {
        chat_id: $activeChatId,
        sender_id: $auth.userId,
        media_url: response.media_url,
        msg_type: 'media'
      };

      sendWebSocketMessage('message.send', message);
    } catch (err) {
      console.error('Failed to upload media:', err);
      alert('Failed to upload media. Please try again.');
    }

    // Reset input
    event.target.value = '';
  }

  function openMediaModal(url) {
    mediaModalUrl = url;
    mediaModal = true;
  }

  function closeMediaModal() {
    mediaModal = false;
    mediaModalUrl = '';
  }

  function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  function isOwnMessage(message) {
    return message.sender_username === currentUsername;
  }

  async function loadChatMembers() {
    if (!$activeChatId) return;
    
    loadingMembers = true;
    try {
      // Load members for both group chats and DM chats
      chatMembers = await api.getChatMembers($activeChatId);
    } catch (err) {
      console.error('Failed to load chat members:', err);
    } finally {
      loadingMembers = false;
    }
  }

  async function openMembersModal() {
    showMembersModal = true;
    await loadChatMembers();
  }

  function closeMembersModal() {
    showMembersModal = false;
    showAddMemberModal = false;
  }

  async function openAddMemberModal() {
    try {
      allUsers = await api.getAllUsers();
      // Filter out users who are already members
      const memberIds = new Set(chatMembers.map(m => m.user_id));
      allUsers = allUsers.filter(u => u.id !== $auth.userId && !memberIds.has(u.id));
      showAddMemberModal = true;
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  }

  async function addMemberToGroup(userId) {
    try {
      await api.addMemberToChat($activeChatId, userId);
      // Reload members
      await loadChatMembers();
      // Reload users list
      const memberIds = new Set(chatMembers.map(m => m.user_id));
      allUsers = allUsers.filter(u => u.id !== userId);
      if (allUsers.length === 0) {
        showAddMemberModal = false;
      }
    } catch (err) {
      console.error('Failed to add member:', err);
      alert('Failed to add member. Please try again.');
    }
  }

  async function removeMemberFromGroup(userId) {
    if (!confirm('Are you sure you want to remove this member from the group?')) {
      return;
    }
    
    try {
      await api.removeMemberFromChat($activeChatId, userId);
      // Reload members
      await loadChatMembers();
      // If we removed ourselves, close the modal and switch view
      if (userId === $auth.userId) {
        closeMembersModal();
        // Optionally switch to dashboard or chat list
      }
    } catch (err) {
      console.error('Failed to remove member:', err);
      alert('Failed to remove member. Please try again.');
    }
  }

  async function showReadStatus(message) {
    selectedMessageForReadStatus = message;
    
    // For DM chats, we need to show both users
    if (!isGroupChat) {
      // Get chat members to find both users in the DM
      if (chatMembers.length === 0) {
        await loadChatMembers();
      }
      
      // For DM, we need both the current user and the other user
      const readByUserIds = new Set(message.read_by || []);
      const currentUserId = $auth.userId;
      
      // Build a complete list of both users in the DM
      // Ensure we have both users even if chatMembers is incomplete
      const allDMMembers = [];
      
      // Add current user
      let currentUserMember = chatMembers.find(m => m.user_id === currentUserId);
      if (!currentUserMember) {
        currentUserMember = {
          user_id: currentUserId,
          username: $auth.username
        };
      }
      allDMMembers.push(currentUserMember);
      
      // Add the other user (the one who is not the current user)
      let otherMember = chatMembers.find(m => m.user_id !== currentUserId);
      if (otherMember) {
        allDMMembers.push(otherMember);
      } else {
        // If other user not in chatMembers, try to get from API again
        try {
          const allMembers = await api.getChatMembers($activeChatId);
          otherMember = allMembers.find(m => m.user_id !== currentUserId);
          if (otherMember) {
            allDMMembers.push(otherMember);
          } else {
            // Fallback: use sender info if available
            if (message.sender_id !== currentUserId) {
              allDMMembers.push({
                user_id: message.sender_id,
                username: message.sender_username || 'Unknown'
              });
            }
          }
        } catch (err) {
          console.error('Failed to get chat members:', err);
          // Fallback: use sender info if available
          if (message.sender_id !== currentUserId) {
            allDMMembers.push({
              user_id: message.sender_id,
              username: message.sender_username || 'Unknown'
            });
          }
        }
      }
      
      // Now determine read status for each member
      readStatusMembers = allDMMembers.map(member => {
        let hasRead = false;
        
        // Sender always has "read" it
        if (member.user_id === message.sender_id) {
          hasRead = true;
        }
        // Check if member is in the read_by array
        else if (readByUserIds.has(member.user_id)) {
          hasRead = true;
        }
        // Special case: if this is the current user viewing their own read status
        // and they're not the sender, check their message status
        else if (member.user_id === currentUserId && member.user_id !== message.sender_id) {
          if (message.status === 'read') {
            hasRead = true;
          }
        }
        
        return {
          ...member,
          hasRead
        };
      });
      
      showReadStatusModal = true;
      return;
    }
    
    // Group chat logic (existing)
    
    // Load chat members if not already loaded
    if (chatMembers.length === 0) {
      await loadChatMembers();
    }
    
    // Get read_by user IDs from the message
    const readByUserIds = new Set(message.read_by || []);
    const currentUserId = $auth.userId;
    
    // Build read status list with all members
    readStatusMembers = chatMembers.map(member => {
      let hasRead = false;
      
      // Check if member is the sender (sender always has "read" it)
      if (member.user_id === message.sender_id) {
        hasRead = true;
      }
      // Check if member is in the read_by array (this includes all users who have read it, excluding sender)
      else if (readByUserIds.has(member.user_id)) {
        hasRead = true;
      }
      // Special case: if this is the current user viewing their own read status
      // and they're not the sender, check their message status
      else if (member.user_id === currentUserId && member.user_id !== message.sender_id) {
        // If message status is 'read', the current user has read it
        // This handles cases where read_by might not be updated yet in the message object
        if (message.status === 'read') {
          hasRead = true;
        }
      }
      
      return {
        ...member,
        hasRead
      };
    });
    
    // Also include the sender if they're not in chatMembers (shouldn't happen, but be safe)
    if (message.sender_id && !chatMembers.find(m => m.user_id === message.sender_id)) {
      readStatusMembers.push({
        user_id: message.sender_id,
        username: message.sender_username || 'Unknown',
        hasRead: true // Sender always has "read" it
      });
    }
    
    showReadStatusModal = true;
  }

  function closeReadStatusModal() {
    showReadStatusModal = false;
    selectedMessageForReadStatus = null;
    readStatusMembers = [];
  }
</script>

{#if $activeChatId && currentChat}
  <div class="chat-view">
    <div class="chat-header">
      <div class="chat-header-info">
        <h3>{currentChat.title || currentChat.other_user_name || `Chat ${$activeChatId}`}</h3>
        {#if isGroupChat}
          <span class="group-badge">Group</span>
        {/if}
      </div>
      {#if isGroupChat}
        <button class="members-button" on:click={openMembersModal} title="View members">
          👥 Members
        </button>
      {/if}
    </div>
    
    <div
      class="messages-container"
      bind:this={messageContainer}
      on:scroll={handleScroll}
    >
      {#each chatMessages as message (message.id)}
        {#if message.type === 'system'}
          <div class="system-message-container">
            <div class="system-message-text">{message.content}</div>
            <div class="system-message-time">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          </div>
        {:else}
          {@const readCount = message.read_count || 0}
          {@const totalMembers = isGroupChat ? Math.max(chatMembers.length, 2) : 2}
          {@const isOwn = isOwnMessage(message)}
          {@const allRead = isGroupChat 
            ? (readCount + 1 >= totalMembers)  // +1 for sender, readCount excludes sender
            : (isOwn ? (readCount >= 1) : (message.status === 'read' || (message.read_by && message.read_by.includes($auth.userId))))}
          {@const someRead = isGroupChat 
            ? (readCount > 0)  // Some have read (excluding sender)
            : (isOwn ? (readCount > 0) : (message.status === 'read' || (message.read_by && message.read_by.includes($auth.userId))))}
          <div class="message" class:own={isOwnMessage(message)}>
          <div class="message-content">
            {#if isGroupChat && !isOwnMessage(message)}
              <div class="message-sender">{message.sender_username || 'Unknown'}</div>
            {/if}
              {#if message.type === 'media'}
                <div class="media-message" on:click={() => openMediaModal(message.content)}>
                  <img src={message.content} alt="Media" class="media-thumbnail" />
                  <div class="media-overlay">Click to view</div>
                </div>
              {:else}
                <div class="text-message">{message.content}</div>
              {/if}
              <div class="message-meta">
                <span class="message-time">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
                <button 
                  class="read-status-icon" 
                  on:click={() => showReadStatus(message)}
                  title="View read status"
                >
                  {#if allRead}
                    <span class="read-icon all-read">✓</span>
                  {:else if someRead}
                    <span class="read-icon some-read">✓?</span>
                  {:else}
                    <span class="read-icon unread">○</span>
                  {/if}
                </button>
              </div>
            </div>
          </div>
        {/if}
      {:else}
        <div class="empty-messages">No messages yet. Start the conversation!</div>
      {/each}
    </div>

    <div class="message-input-container">
      <input
        type="file"
        accept="image/*"
        id="media-upload"
        on:change={handleMediaUpload}
        style="display: none;"
      />
      <label for="media-upload" class="media-button" title="Upload image">
        📎
      </label>
      <input
        type="text"
        class="message-input"
        bind:value={messageInput}
        on:keypress={handleKeyPress}
        placeholder="Type a message..."
      />
      <button class="send-button" on:click={sendMessage} disabled={!messageInput.trim()}>
        Send
      </button>
    </div>
  </div>
{:else}
  <div class="no-chat-selected">
    <p>Select a chat to start messaging</p>
  </div>
{/if}

{#if mediaModal}
  <div class="modal-overlay" on:click={closeMediaModal}>
    <div class="modal-content" on:click|stopPropagation>
      <button class="modal-close" on:click={closeMediaModal}>×</button>
      <img src={mediaModalUrl} alt="Media" class="modal-image" />
    </div>
  </div>
{/if}

{#if showMembersModal}
  <div class="modal-overlay" on:click={closeMembersModal}>
    <div class="modal-content members-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Group Members</h3>
        <button class="modal-close" on:click={closeMembersModal}>×</button>
      </div>
      <div class="modal-body">
        {#if loadingMembers}
          <div class="loading-state">Loading members...</div>
        {:else}
          <div class="members-list">
            {#each chatMembers as member (member.user_id)}
              <div class="member-item">
                <div class="member-avatar">
                  {(member.username || 'Unknown').charAt(0).toUpperCase()}
                </div>
                <div class="member-info">
                  <div class="member-name">{member.username || 'Unknown'}</div>
                  {#if member.user_id === $auth.userId}
                    <div class="member-badge">You</div>
                  {/if}
                </div>
                <button 
                  class="remove-member-button" 
                  on:click={() => removeMemberFromGroup(member.user_id)}
                  title={member.user_id === $auth.userId ? "Leave group" : "Remove member"}
                >
                  ×
                </button>
              </div>
            {/each}
          </div>
          <div class="modal-actions">
            <button class="add-member-button" on:click={openAddMemberModal}>
              + Add Member
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if showAddMemberModal}
  <div class="modal-overlay" on:click={closeMembersModal}>
    <div class="modal-content add-member-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Add Member</h3>
        <button class="modal-close" on:click={() => showAddMemberModal = false}>×</button>
      </div>
      <div class="modal-body">
        {#if allUsers.length === 0}
          <div class="empty-state">No users available to add</div>
        {:else}
          <div class="users-list">
            {#each allUsers as user (user.id)}
              <div class="user-item" on:click={() => addMemberToGroup(user.id)} role="button" tabindex="0">
                <div class="user-avatar">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div class="user-name">{user.username}</div>
                <button class="add-button">+ Add</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Read Status Modal -->
{#if showReadStatusModal && selectedMessageForReadStatus}
  <div class="modal-overlay" on:click={closeReadStatusModal}>
    <div class="modal-content read-status-modal" on:click|stopPropagation>
      <div class="modal-header">
        <h3>Read Status</h3>
        <button class="modal-close" on:click={closeReadStatusModal} title="Close">×</button>
      </div>
      <div class="modal-body">
        <div class="message-preview">
          <div class="message-preview-content">
            {#if selectedMessageForReadStatus.type === 'media'}
              <span>📷 Media</span>
            {:else}
              <span>{selectedMessageForReadStatus.content || selectedMessageForReadStatus.text || 'Message'}</span>
            {/if}
          </div>
          <div class="message-preview-time">
            {new Date(selectedMessageForReadStatus.timestamp).toLocaleString()}
          </div>
        </div>
        <div class="read-status-list">
          <div class="read-status-header">
            <span class="read-count">
              {readStatusMembers.filter(m => m.hasRead).length} of {readStatusMembers.length} read
            </span>
          </div>
          {#each readStatusMembers as member (member.user_id)}
            <div class="read-status-item">
              <div class="member-avatar-small">
                {(member.username || 'Unknown').charAt(0).toUpperCase()}
              </div>
              <div class="member-info">
                <div class="member-name">
                  {member.username || 'Unknown'}
                  {#if member.user_id === $auth.userId}
                    <span class="you-badge">(You)</span>
                  {/if}
                  {#if member.user_id === selectedMessageForReadStatus.sender_id}
                    <span class="sender-badge">(Sender)</span>
                  {/if}
                </div>
              </div>
              <div class="read-status-indicator">
                {#if member.hasRead}
                  <button class="read-badge" disabled>✓ Read</button>
                {:else}
                  <button class="unread-badge" disabled>Unread</button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .chat-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: white;
  }

  .chat-header {
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background-color: #f8f9fa;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chat-header-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
  }

  .chat-header h3 {
    margin: 0;
    color: #333;
  }

  .group-badge {
    background-color: #4a90e2;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .members-button {
    padding: 0.5rem 1rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .members-button:hover {
    background-color: #357abd;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .message {
    display: flex;
    margin-bottom: 0.5rem;
  }

  .message.own {
    justify-content: flex-end;
  }

  .message-content {
    max-width: 70%;
    padding: 0.75rem 1rem;
    border-radius: 12px;
    background-color: #e9ecef;
  }

  .message.own .message-content {
    background-color: #4a90e2;
    color: white;
  }

  .system-message-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0.5rem 0;
    padding: 0.5rem 0;
  }

  .system-message-text {
    background-color: #e3f2fd;
    color: #1976d2;
    padding: 0.375rem 0.75rem;
    border-radius: 12px;
    font-size: 0.8125rem;
    font-style: italic;
    text-align: center;
    max-width: 80%;
  }

  .system-message-time {
    font-size: 0.6875rem;
    color: #999;
    margin-top: 0.25rem;
  }

  .text-message {
    word-wrap: break-word;
    white-space: pre-wrap;
  }

  .message-sender {
    font-size: 0.75rem;
    font-weight: 600;
    color: #666;
    margin-bottom: 0.25rem;
  }

  .message.own .message-sender {
    color: rgba(255, 255, 255, 0.9);
  }

  .media-message {
    position: relative;
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
  }

  .media-thumbnail {
    max-width: 300px;
    max-height: 300px;
    display: block;
  }

  .media-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .media-message:hover .media-overlay {
    opacity: 1;
  }

  .message-meta {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.25rem;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .message-time {
    font-size: 0.75rem;
  }

  .read-status-icon {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.125rem 0.25rem;
    margin-left: 0.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.2s;
    line-height: 1;
    vertical-align: middle;
  }

  .read-status-icon:hover {
    opacity: 0.8;
  }

  .read-icon {
    font-size: 0.75rem;
    line-height: 1;
    display: inline-block;
    font-weight: 600;
  }

  .read-icon.all-read {
    color: #28a745;
  }

  .read-icon.some-read {
    color: #4a90e2;
    font-size: 0.6875rem;
  }

  .read-icon.unread {
    color: #666;
    font-size: 0.625rem;
  }

  /* For own messages (blue background), use white/light colors for visibility */
  .message.own .read-icon.all-read {
    color: rgba(255, 255, 255, 0.95);
  }

  .message.own .read-icon.some-read {
    color: rgba(255, 255, 255, 0.85);
    font-size: 0.6875rem;
  }

  .message.own .read-icon.unread {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.625rem;
  }

  .message-status {
    font-size: 0.75rem;
    margin-left: 0.5rem;
  }
  
  .message-status.read {
    color: #4a90e2;
  }
  
  /* For own messages (blue background), use white/light color for status */
  .message.own .message-status.read {
    color: rgba(255, 255, 255, 0.9);
  }
  
  .message.own .message-status.sent {
    color: rgba(255, 255, 255, 0.7);
  }
  
  .message-status.sent {
    color: #999;
  }
  
  .message-status.unread {
    color: #f44336;
    font-weight: 500;
  }

  .empty-messages {
    text-align: center;
    color: #999;
    padding: 2rem;
  }

  .message-input-container {
    display: flex;
    align-items: center;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    gap: 0.5rem;
  }

  .media-button {
    cursor: pointer;
    font-size: 1.5rem;
    padding: 0.5rem;
    user-select: none;
  }

  .media-button:hover {
    opacity: 0.7;
  }

  .message-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .message-input:focus {
    outline: none;
    border-color: #4a90e2;
  }

  .send-button {
    padding: 0.75rem 1.5rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
  }

  .send-button:hover:not(:disabled) {
    background-color: #357abd;
  }

  .send-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }

  .no-chat-selected {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
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
    position: relative;
    max-width: 90%;
    max-height: 90%;
  }

  .modal-close {
    position: absolute;
    top: -40px;
    right: 0;
    background: none;
    border: none;
    color: white;
    font-size: 2rem;
    cursor: pointer;
    padding: 0;
    width: 40px;
    height: 40px;
  }

  .modal-image {
    max-width: 100%;
    max-height: 90vh;
    display: block;
  }

  .members-modal,
  .add-member-modal {
    max-width: 400px;
    width: 90%;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    max-height: 85vh;
    overflow: hidden;
  }

  .members-modal .modal-header,
  .add-member-modal .modal-header {
    position: relative;
    padding: 0.875rem 1rem;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .members-modal .modal-header h3,
  .add-member-modal .modal-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #333;
  }

  .members-modal .modal-close,
  .add-member-modal .modal-close {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: none;
    border: none;
    color: #666;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .members-modal .modal-close:hover,
  .add-member-modal .modal-close:hover {
    background-color: #f5f5f5;
    color: #333;
  }

  .members-modal .modal-body,
  .add-member-modal .modal-body {
    padding: 1rem;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .members-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.25rem;
  }

  .members-list::-webkit-scrollbar {
    width: 6px;
  }

  .members-list::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }

  .members-list::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }

  .members-list::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }

  .member-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-bottom: 1px solid #f0f0f0;
    position: relative;
  }

  .member-item:last-child {
    border-bottom: none;
  }

  .remove-member-button {
    background: none;
    border: none;
    color: #d32f2f;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    margin-left: auto;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
    width: 28px;
    height: 28px;
  }

  .remove-member-button:hover {
    background-color: #ffebee;
    color: #c62828;
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

  .member-info {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .member-name {
    font-weight: 500;
    color: #333;
  }

  .member-badge {
    background-color: #e3f2fd;
    color: #4a90e2;
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .modal-actions {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
  }

  .add-member-button {
    width: 100%;
    padding: 0.75rem;
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .add-member-button:hover {
    background-color: #218838;
  }

  .users-list {
    max-height: 300px;
    overflow-y: auto;
  }

  .user-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-bottom: 1px solid #f0f0f0;
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

  .user-name {
    flex: 1;
    font-weight: 500;
    color: #333;
  }

  .add-button {
    padding: 0.5rem 1rem;
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .add-button:hover {
    background-color: #218838;
  }

  .loading-state,
  .empty-state {
    text-align: center;
    padding: 2rem;
    color: #999;
  }

  .read-status-modal {
    max-width: 450px;
    width: 90%;
    max-height: 85vh;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .read-status-modal .modal-header {
    position: relative;
    padding: 0.625rem 0.875rem;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .read-status-modal .modal-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #333;
  }

  .read-status-modal .modal-close {
    position: absolute;
    top: 0.375rem;
    right: 0.375rem;
    background: none;
    border: none;
    color: #666;
    font-size: 1.125rem;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .read-status-modal .modal-close:hover {
    background-color: #f5f5f5;
    color: #333;
  }

  .read-status-modal .modal-body {
    padding: 0.75rem;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .message-preview {
    padding: 0.5rem 0.75rem;
    background-color: #f5f5f5;
    border-radius: 4px;
    margin-bottom: 0.625rem;
    border: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .message-preview-content {
    font-size: 0.8125rem;
    color: #333;
    margin-bottom: 0.25rem;
    word-wrap: break-word;
    line-height: 1.25;
  }

  .message-preview-time {
    font-size: 0.6875rem;
    color: #666;
  }

  .read-status-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.25rem;
    margin-top: 0.375rem;
  }

  .read-status-list::-webkit-scrollbar {
    width: 6px;
  }

  .read-status-list::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }

  .read-status-list::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
  }

  .read-status-list::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }

  .read-status-header {
    padding: 0.375rem 0;
    margin-bottom: 0.375rem;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .read-count {
    font-size: 0.75rem;
    font-weight: 400;
    color: #666;
  }

  .read-status-item {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.5rem 0.75rem;
    background-color: #f8f9fa;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    margin-bottom: 0.25rem;
    transition: background-color 0.2s;
  }

  .read-status-item:last-child {
    margin-bottom: 0;
  }

  .read-status-item:hover {
    background-color: #f0f0f0;
  }

  .member-avatar-small {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background-color: #4a90e2;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  .member-info {
    flex: 1;
    min-width: 0;
  }

  .member-name {
    font-weight: 500;
    color: #333;
    font-size: 0.8125rem;
    line-height: 1.2;
  }

  .you-badge,
  .sender-badge {
    color: #666;
    font-size: 0.6875rem;
    font-weight: 400;
    margin-left: 0.25rem;
  }

  .read-status-indicator {
    flex-shrink: 0;
  }

  .read-badge {
    background-color: #4a90e2;
    color: white;
    padding: 0.1875rem 0.5rem;
    border-radius: 10px;
    font-size: 0.6875rem;
    font-weight: 500;
    border: none;
    cursor: default;
  }

  .unread-badge {
    background-color: #e9ecef;
    color: #666;
    padding: 0.1875rem 0.5rem;
    border-radius: 10px;
    font-size: 0.6875rem;
    font-weight: 500;
    border: none;
    cursor: default;
  }
</style>
