import { writable } from 'svelte/store';

function createAuthStore() {
  const { subscribe, set, update } = writable({
    isAuthenticated: false,
    username: null,
    userId: null,
    jwt: null,
    sessionId: null
  });

  // Load from sessionStorage on initialization
  if (typeof window !== 'undefined') {
    const storedJwt = sessionStorage.getItem('jwt');
    const storedSessionId = sessionStorage.getItem('session_id');
    const storedUsername = sessionStorage.getItem('username');
    const storedUserId = sessionStorage.getItem('user_id');
    
    if (storedJwt && storedSessionId) {
      set({
        isAuthenticated: true,
        username: storedUsername,
        userId: storedUserId ? parseInt(storedUserId) : null,
        jwt: storedJwt,
        sessionId: storedSessionId
      });
    }
  }

  return {
    subscribe,
    login: (username, jwt, sessionId, userId = null) => {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('jwt', jwt);
        sessionStorage.setItem('session_id', sessionId);
        sessionStorage.setItem('username', username);
        if (userId) {
          sessionStorage.setItem('user_id', userId.toString());
        }
      }
      set({
        isAuthenticated: true,
        username,
        userId,
        jwt,
        sessionId
      });
    },
    logout: () => {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('jwt');
        sessionStorage.removeItem('session_id');
        sessionStorage.removeItem('username');
        sessionStorage.removeItem('user_id');
      }
      set({
        isAuthenticated: false,
        username: null,
        userId: null,
        jwt: null,
        sessionId: null
      });
    }
  };
}

export const auth = createAuthStore();
