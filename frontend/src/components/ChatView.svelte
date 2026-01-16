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

  $: currentChat = $chats.find(c => c.id === $activeChatId);
  $: chatMessages = $messages[$activeChatId] || [];
  $: currentUsername = $auth.username;

  $: if ($activeChatId && $activeChatId !== previousChatId) {
    previousChatId = $activeChatId;
    loadMessages();
  }

  $: if (chatMessages.length > 0 && isAtBottom) {
    scrollToBottom();
  }

  async function loadMessages() {
    if (!$activeChatId || loadingMessages) return;

    loadingMessages = true;
    try {
      const messageList = await api.getMessages($activeChatId);
      messages.setMessages($activeChatId, messageList);
      
      // Mark messages as read
      if (messageList.length > 0) {
        const lastMessage = messageList[messageList.length - 1];
        markChatAsRead($activeChatId, lastMessage.id);
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

    const message = {
      chat_id: $activeChatId,
      content: messageInput.trim(),
      type: 'text'
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
        content: response.media_url,
        type: 'media'
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
</script>

{#if $activeChatId && currentChat}
  <div class="chat-view">
    <div class="chat-header">
      <h3>{currentChat.title || currentChat.other_user_name || `Chat ${$activeChatId}`}</h3>
    </div>
    
    <div
      class="messages-container"
      bind:this={messageContainer}
      on:scroll={handleScroll}
    >
      {#each chatMessages as message (message.id)}
        <div class="message" class:own={isOwnMessage(message)}>
          <div class="message-content">
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
              {#if isOwnMessage(message) && message.status}
                <span class="message-status">{message.status}</span>
              {/if}
            </div>
          </div>
        </div>
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
  }

  .chat-header h3 {
    margin: 0;
    color: #333;
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

  .text-message {
    word-wrap: break-word;
    white-space: pre-wrap;
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

  .message-status {
    font-size: 0.75rem;
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
    background-color: rgba(0, 0, 0, 0.9);
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
</style>
