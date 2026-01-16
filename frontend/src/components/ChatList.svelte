<script>
  import { chats } from '../stores/chats.js';
  import { activeChatId } from '../stores/chats.js';
  import { sendWebSocketMessage } from '../services/websocket.js';

  function selectChat(chat) {
    activeChatId.set(chat.id);
    sendWebSocketMessage('chat.open', { chat_id: chat.id });
  }

  function getChatTitle(chat) {
    return chat.title || chat.other_user_name || `Chat ${chat.id}`;
  }
</script>

<div class="chat-list">
  <div class="chat-list-header">
    <h2>Chats</h2>
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
  }

  .chat-list-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #333;
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
  }

  .chat-item:hover {
    background-color: #f5f5f5;
  }

  .chat-item.active {
    background-color: #e3f2fd;
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
</style>
