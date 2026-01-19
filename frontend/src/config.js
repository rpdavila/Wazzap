// Helper to check if a string is an IP address
const isIPAddress = (str) => {
  // IPv4 pattern
  const ipv4Pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
  // IPv6 pattern (simplified - covers most cases)
  const ipv6Pattern = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;
  return ipv4Pattern.test(str) || ipv6Pattern.test(str);
};

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
    // Check for explicit API URL override
    if (import.meta.env.VITE_API_URL) {
      return import.meta.env.VITE_API_URL;
    }
    
    // For localhost, use port-based (development)
    if (this.domain === 'localhost' || this.domain === '127.0.0.1') {
      return `${protocol}://localhost:8000`;
    }
    
    // For IP addresses, use the same IP with port 8000 (can't use subdomains with IPs)
    if (isIPAddress(this.domain)) {
      return `${protocol}://${this.domain}:8000`;
    }
    
    // For production/Docker with domain names, use hostname-based routing
    // Frontend is at chat.<domain>, backend is at chat-api.<domain>
    return `${protocol}://chat-api.${this.domain}`;
  },
  get wsUrl() {
    // Check for explicit WebSocket URL override
    if (import.meta.env.VITE_WS_URL) {
      const baseUrl = import.meta.env.VITE_WS_URL;
      return baseUrl.endsWith('/api/ws') ? baseUrl : `${baseUrl}/api/ws`;
    }
    
    // For localhost, use port-based (development)
    if (this.domain === 'localhost' || this.domain === '127.0.0.1') {
      return `${wsProtocol}://localhost:8000/api/ws`;
    }
    
    // For IP addresses, use the same IP with port 8000 (can't use subdomains with IPs)
    if (isIPAddress(this.domain)) {
      return `${wsProtocol}://${this.domain}:8000/api/ws`;
    }
    
    // For production/Docker with domain names, use hostname-based routing
    return `${wsProtocol}://chat-api.${this.domain}/api/ws`;
  }
};
