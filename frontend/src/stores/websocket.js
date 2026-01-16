import { writable } from 'svelte/store';

export const websocket = writable({
  connected: false,
  socket: null
});
