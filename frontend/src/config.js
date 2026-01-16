// Environment-based configuration
const getDomain = () => {
  // Can be overridden via environment variable
  if (import.meta.env.VITE_DOMAIN) {
    return import.meta.env.VITE_DOMAIN;
  }
  // Try to detect from window location
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    // Extract domain from chat.<domain>
    const match = hostname.match(/^chat\.(.+)$/);
    if (match) {
      return match[1];
    }
    // For localhost, return localhost
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'localhost';
    }
    return hostname;
  }
  return 'localhost';
};

const getProtocol = () => {
  if (typeof window !== 'undefined') {
    return window.location.protocol === 'https:' ? 'https' : 'http';
  }
  return 'http';
};

const getWsProtocol = () => {
  return getProtocol() === 'https' ? 'wss' : 'ws';
};

const domain = getDomain();
const protocol = getProtocol();
const wsProtocol = getWsProtocol();

export const config = {
  domain,
  get apiUrl() {
    if (this.domain === 'localhost' || this.domain === '127.0.0.1') {
      // For localhost, assume API runs on a different port or use localhost:8000
      return import.meta.env.VITE_API_URL || `${protocol}://localhost:8000`;
    }
    return `${protocol}://chat-api.${this.domain}`;
  },
  get wsUrl() {
    if (this.domain === 'localhost' || this.domain === '127.0.0.1') {
      // For localhost, assume WS runs on a different port or use localhost:8000
      const baseUrl = import.meta.env.VITE_WS_URL || `${wsProtocol}://localhost:8000`;
      return baseUrl.endsWith('/api/ws') ? baseUrl : `${baseUrl}/api/ws`;
    }
    const baseUrl = `${wsProtocol}://chat-api.${this.domain}`;
    return baseUrl.endsWith('/api/ws') ? baseUrl : `${baseUrl}/api/ws`;
  }
};
