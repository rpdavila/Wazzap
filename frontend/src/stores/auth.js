import { writable } from 'svelte/store';

function createAuthStore() {
  const { subscribe, set, update } = writable({
    isAuthenticated: false,
    username: null,
    jwt: null,
    sessionId: null
  });

  // Load from sessionStorage on initialization
  if (typeof window !== 'undefined') {
    const storedJwt = sessionStorage.getItem('jwt');
    const storedSessionId = sessionStorage.getItem('session_id');
    const storedUsername = sessionStorage.getItem('username');
    
    if (storedJwt && storedSessionId) {
      set({
        isAuthenticated: true,
        username: storedUsername,
        jwt: storedJwt,
        sessionId: storedSessionId
      });
    }
  }

  return {
    subscribe,
    login: (username, jwt, sessionId) => {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('jwt', jwt);
        sessionStorage.setItem('session_id', sessionId);
        sessionStorage.setItem('username', username);
      }
      set({
        isAuthenticated: true,
        username,
        jwt,
        sessionId
      });
    },
    logout: () => {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('jwt');
        sessionStorage.removeItem('session_id');
        sessionStorage.removeItem('username');
      }
      set({
        isAuthenticated: false,
        username: null,
        jwt: null,
        sessionId: null
      });
    }
  };
}

export const auth = createAuthStore();
