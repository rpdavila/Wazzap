import { writable } from 'svelte/store';

// 'login' or 'debug'
export const currentView = writable('login');
