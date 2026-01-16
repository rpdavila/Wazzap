import { writable } from 'svelte/store';
import { config } from '../config.js';

// Store for debug page configuration (editable API URL)
export const debugApiUrl = writable(config.apiUrl);
export const debugWsUrl = writable(config.wsUrl);
