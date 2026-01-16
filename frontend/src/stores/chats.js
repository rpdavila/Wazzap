import { writable } from 'svelte/store';

export const chats = writable([]);
export const activeChatId = writable(null);
