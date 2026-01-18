import { writable } from 'svelte/store';

// 'login', 'debug', 'dashboard', or 'chats'
export const currentView = writable('login');
