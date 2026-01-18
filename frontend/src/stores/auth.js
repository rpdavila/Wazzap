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
    
    // #region agent log
    fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:13',message:'Auth store init from sessionStorage',data:{hasJwt:!!storedJwt,hasSessionId:!!storedSessionId,hasUsername:!!storedUsername,hasUserId:!!storedUserId,willRestoreAuth:!!(storedJwt && storedSessionId)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    
    if (storedJwt && storedSessionId) {
      set({
        isAuthenticated: true,
        username: storedUsername,
        userId: storedUserId ? parseInt(storedUserId) : null,
        jwt: storedJwt,
        sessionId: storedSessionId
      });
      // #region agent log
      fetch('http://127.0.0.1:7247/ingest/6e3d4334-3650-455b-b2c2-2943a80ca994',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:26',message:'Auth state restored from sessionStorage',data:{username:storedUsername,userId:storedUserId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
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
