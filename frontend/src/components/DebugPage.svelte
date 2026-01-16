<script>
  import { api } from '../services/api.js';
  import { config } from '../config.js';
  import { currentView } from '../stores/view.js';
  import { debugApiUrl, debugWsUrl } from '../stores/debugConfig.js';
  import { get } from 'svelte/store';

  let testResults = [];
  let loading = false;
  
  // Collapsible sections state
  let authOpen = false;
  let chatsOpen = false;
  let messagesOpen = false;
  let mediaOpen = false;
  let customOpen = false;
  
  // Test data
  let testUsername = 'admin';
  let testPin = '0000';
  let testChatId = '';
  let testFile = null;
  
  // Custom test data
  let customMethod = 'GET';
  let customEndpoint = '/api/';
  let customJsonBody = '{}';
  let jsonError = null;
  
  // Editable API URL
  let customApiUrl = $debugApiUrl;
  let customWsUrl = $debugWsUrl;
  let showApiConfig = false;

  $: {
    customApiUrl = $debugApiUrl;
    customWsUrl = $debugWsUrl;
  }

  function updateApiUrl() {
    debugApiUrl.set(customApiUrl);
    debugWsUrl.set(customWsUrl);
    showApiConfig = false;
  }

  function resetApiUrl() {
    customApiUrl = config.apiUrl;
    customWsUrl = config.wsUrl;
    debugApiUrl.set(customApiUrl);
    debugWsUrl.set(customWsUrl);
    showApiConfig = false;
  }

  // Override api service to use custom URL
  async function customApiRequest(endpoint, options = {}) {
    const baseUrl = get(debugApiUrl);
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    const url = `${baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async function customApiUpload(file) {
    const baseUrl = get(debugApiUrl);
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${baseUrl}/api/media/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function addResult(endpoint, method, success, data, error, requestData = null) {
    testResults = [
      {
        timestamp: new Date().toLocaleTimeString(),
        endpoint,
        method,
        success,
        data,
        error: error ? (error.message || String(error)) : null,
        requestData
      },
      ...testResults
    ];
  }

  async function testLogin() {
    loading = true;
    const requestData = { username: testUsername, pin: testPin };
    try {
      const response = await customApiRequest('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(requestData)
      });
      addResult('/api/auth/login', 'POST', true, response, null, requestData);
    } catch (err) {
      addResult('/api/auth/login', 'POST', false, null, err, requestData);
    } finally {
      loading = false;
    }
  }

  async function testGetChats() {
    loading = true;
    try {
      const response = await customApiRequest('/api/chats', {
        method: 'GET'
      });
      addResult('/api/chats', 'GET', true, response, null);
    } catch (err) {
      addResult('/api/chats', 'GET', false, null, err);
    } finally {
      loading = false;
    }
  }

  async function testGetMessages() {
    if (!testChatId.trim()) {
      alert('Please enter a chat ID');
      return;
    }
    loading = true;
    const endpoint = `/api/chats/${testChatId.trim()}/messages`;
    try {
      const response = await customApiRequest(endpoint, {
        method: 'GET'
      });
      addResult(endpoint, 'GET', true, response, null);
    } catch (err) {
      addResult(endpoint, 'GET', false, null, err);
    } finally {
      loading = false;
    }
  }

  async function testUploadMedia() {
    if (!testFile) {
      alert('Please select a file');
      return;
    }
    loading = true;
    try {
      const response = await customApiUpload(testFile);
      addResult('/api/media/upload', 'POST', true, response, null, { filename: testFile.name, type: testFile.type });
    } catch (err) {
      addResult('/api/media/upload', 'POST', false, null, err, { filename: testFile.name, type: testFile.type });
    } finally {
      loading = false;
    }
  }

  function handleFileChange(event) {
    testFile = event.target.files[0];
  }

  function clearResults() {
    testResults = [];
  }

  function goToLogin() {
    currentView.set('login');
  }

  function toggleSection(section) {
    if (section === 'auth') authOpen = !authOpen;
    if (section === 'chats') chatsOpen = !chatsOpen;
    if (section === 'messages') messagesOpen = !messagesOpen;
    if (section === 'media') mediaOpen = !mediaOpen;
    if (section === 'custom') customOpen = !customOpen;
  }

  function validateJson(jsonString) {
    try {
      JSON.parse(jsonString);
      jsonError = null;
      return true;
    } catch (e) {
      jsonError = e.message;
      return false;
    }
  }

  async function testCustomRequest() {
    // Validate JSON if method requires body
    const methodsWithBody = ['POST', 'PUT', 'PATCH'];
    if (methodsWithBody.includes(customMethod)) {
      if (!validateJson(customJsonBody)) {
        alert(`Invalid JSON: ${jsonError}`);
        return;
      }
    }

    if (!customEndpoint.trim()) {
      alert('Please enter an endpoint');
      return;
    }

    loading = true;
    const endpoint = customEndpoint.trim().startsWith('/') 
      ? customEndpoint.trim() 
      : '/' + customEndpoint.trim();
    
    let requestData = null;
    let requestOptions = {
      method: customMethod
    };

    // Add body for methods that support it
    if (methodsWithBody.includes(customMethod)) {
      try {
        requestData = JSON.parse(customJsonBody);
        requestOptions.body = JSON.stringify(requestData);
        requestOptions.headers = {
          'Content-Type': 'application/json'
        };
      } catch (e) {
        loading = false;
        alert(`Error parsing JSON: ${e.message}`);
        return;
      }
    }

    try {
      const baseUrl = get(debugApiUrl);
      const url = `${baseUrl}${endpoint}`;
      
      const response = await fetch(url, requestOptions);
      
      let responseData;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      if (!response.ok) {
        addResult(endpoint, customMethod, false, null, new Error(`HTTP ${response.status}: ${typeof responseData === 'string' ? responseData : JSON.stringify(responseData)}`), requestData);
      } else {
        addResult(endpoint, customMethod, true, responseData, null, requestData);
      }
    } catch (err) {
      addResult(endpoint, customMethod, false, null, err, requestData);
    } finally {
      loading = false;
    }
  }

  $: if (customJsonBody) {
    if (['POST', 'PUT', 'PATCH'].includes(customMethod)) {
      validateJson(customJsonBody);
    } else {
      jsonError = null;
    }
  }
</script>

<div class="debug-container">
  <div class="debug-header">
    <h1>API Debug & Development</h1>
    <button class="back-button" on:click={goToLogin}>← Back to Login</button>
  </div>

  <div class="debug-content">
    <div class="debug-sidebar">
      <div class="api-info">
        <div class="api-header">
          <h2>API Configuration</h2>
          <button class="toggle-button" on:click={() => showApiConfig = !showApiConfig}>
            {showApiConfig ? '▼' : '▶'}
          </button>
        </div>
        {#if showApiConfig}
          <div class="api-config-form">
            <div class="input-group">
              <label>API URL:</label>
              <input type="text" bind:value={customApiUrl} placeholder="http://localhost:8000" />
            </div>
            <div class="input-group">
              <label>WebSocket URL:</label>
              <input type="text" bind:value={customWsUrl} placeholder="ws://localhost:8000/api/ws" />
            </div>
            <div class="config-actions">
              <button class="save-button" on:click={updateApiUrl}>Save</button>
              <button class="reset-button" on:click={resetApiUrl}>Reset</button>
            </div>
          </div>
        {:else}
          <div class="info-item">
            <strong>API URL:</strong>
            <code>{$debugApiUrl}</code>
          </div>
          <div class="info-item">
            <strong>WebSocket URL:</strong>
            <code>{$debugWsUrl}</code>
          </div>
        {/if}
      </div>

      <div class="test-section">
        <h2>Test Endpoints</h2>
        
        <!-- Authentication Section -->
        <div class="endpoint-group">
          <button class="endpoint-header" on:click={() => toggleSection('auth')}>
            <span>Authentication</span>
            <span class="toggle-icon">{authOpen ? '▼' : '▶'}</span>
          </button>
          {#if authOpen}
            <div class="endpoint-content">
              <div class="endpoint-info">
                <div class="method-badge post">POST</div>
                <code class="endpoint-path">/api/auth/login</code>
              </div>
              <div class="endpoint-description">
                Authenticate user with username and PIN. Returns JWT and session_id.
              </div>
              <div class="input-group">
                <label>Username:</label>
                <input type="text" bind:value={testUsername} />
              </div>
              <div class="input-group">
                <label>PIN:</label>
                <input type="password" bind:value={testPin} />
              </div>
              <div class="request-data">
                <strong>Request Body:</strong>
                <pre>{JSON.stringify({ username: testUsername, pin: testPin }, null, 2)}</pre>
              </div>
              <button on:click={testLogin} disabled={loading}>Test Login</button>
            </div>
          {/if}
        </div>

        <!-- Chats Section -->
        <div class="endpoint-group">
          <button class="endpoint-header" on:click={() => toggleSection('chats')}>
            <span>Get Chats</span>
            <span class="toggle-icon">{chatsOpen ? '▼' : '▶'}</span>
          </button>
          {#if chatsOpen}
            <div class="endpoint-content">
              <div class="endpoint-info">
                <div class="method-badge get">GET</div>
                <code class="endpoint-path">/api/chats</code>
              </div>
              <div class="endpoint-description">
                Retrieve list of all chats for the authenticated user.
              </div>
              <div class="endpoint-note">
                <strong>Note:</strong> Requires authentication (JWT token in Authorization header)
              </div>
              <button on:click={testGetChats} disabled={loading}>Test Get Chats</button>
            </div>
          {/if}
        </div>

        <!-- Messages Section -->
        <div class="endpoint-group">
          <button class="endpoint-header" on:click={() => toggleSection('messages')}>
            <span>Get Messages</span>
            <span class="toggle-icon">{messagesOpen ? '▼' : '▶'}</span>
          </button>
          {#if messagesOpen}
            <div class="endpoint-content">
              <div class="endpoint-info">
                <div class="method-badge get">GET</div>
                <code class="endpoint-path">/api/chats/:id/messages</code>
              </div>
              <div class="endpoint-description">
                Retrieve message history for a specific chat.
              </div>
              <div class="input-group">
                <label>Chat ID:</label>
                <input type="text" bind:value={testChatId} placeholder="Enter chat ID" />
              </div>
              <div class="endpoint-note">
                <strong>Note:</strong> Requires authentication (JWT token in Authorization header)
              </div>
              <button on:click={testGetMessages} disabled={loading}>Test Get Messages</button>
            </div>
          {/if}
        </div>

        <!-- Media Section -->
        <div class="endpoint-group">
          <button class="endpoint-header" on:click={() => toggleSection('media')}>
            <span>Upload Media</span>
            <span class="toggle-icon">{mediaOpen ? '▼' : '▶'}</span>
          </button>
          {#if mediaOpen}
            <div class="endpoint-content">
              <div class="endpoint-info">
                <div class="method-badge post">POST</div>
                <code class="endpoint-path">/api/media/upload</code>
              </div>
              <div class="endpoint-description">
                Upload an image or GIF file. Returns media_url for use in messages.
              </div>
              <div class="input-group">
                <label>File:</label>
                <input type="file" accept="image/*" on:change={handleFileChange} />
              </div>
              {#if testFile}
                <div class="file-info">
                  <strong>Selected:</strong> {testFile.name} ({(testFile.size / 1024).toFixed(2)} KB)
                </div>
              {/if}
              <div class="endpoint-note">
                <strong>Note:</strong> Requires authentication (JWT token in Authorization header)
              </div>
              <button on:click={testUploadMedia} disabled={loading}>Test Upload Media</button>
            </div>
          {/if}
        </div>

        <!-- Custom Request Section -->
        <div class="endpoint-group custom-request">
          <button class="endpoint-header" on:click={() => toggleSection('custom')}>
            <span>Custom Request</span>
            <span class="toggle-icon">{customOpen ? '▼' : '▶'}</span>
          </button>
          {#if customOpen}
            <div class="endpoint-content">
              <div class="endpoint-description">
                Create a custom API request with any method, endpoint, and JSON body.
              </div>
              <div class="input-group">
                <label>Method:</label>
                <select bind:value={customMethod}>
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="PATCH">PATCH</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
              <div class="input-group">
                <label>Endpoint:</label>
                <input type="text" bind:value={customEndpoint} placeholder="/api/your-endpoint" />
              </div>
              {#if ['POST', 'PUT', 'PATCH'].includes(customMethod)}
                <div class="input-group">
                  <label>JSON Body:</label>
                  <textarea 
                    bind:value={customJsonBody} 
                    placeholder={'{"key": "value"}'}
                    class:json-error={jsonError}
                  ></textarea>
                  {#if jsonError}
                    <div class="error-message">Invalid JSON: {jsonError}</div>
                  {/if}
                </div>
              {/if}
              <div class="endpoint-note">
                <strong>Note:</strong> Endpoint should start with "/" (e.g., /api/chats). The base URL is prepended automatically.
              </div>
              <button on:click={testCustomRequest} disabled={loading}>
                {loading ? 'Sending...' : 'Send Request'}
              </button>
            </div>
          {/if}
        </div>

        <div class="test-actions">
          <button class="clear-button" on:click={clearResults} disabled={loading}>Clear Results</button>
        </div>
      </div>
    </div>

    <div class="debug-main">
      <div class="results-header">
        <h2>API Test Results</h2>
        <span class="result-count">{testResults.length} {testResults.length === 1 ? 'test' : 'tests'}</span>
      </div>
      <div class="results-container">
        {#if testResults.length === 0}
          <div class="empty-results">No tests run yet. Expand endpoint sections in the sidebar to test API endpoints.</div>
        {:else}
          {#each testResults as result (result.timestamp + result.endpoint)}
            <div class="result-item" class:success={result.success} class:error={!result.success}>
              <div class="result-header">
                <span class="result-method" 
                  class:post={result.method === 'POST'} 
                  class:get={result.method === 'GET'}
                  class:put={result.method === 'PUT'}
                  class:patch={result.method === 'PATCH'}
                  class:delete={result.method === 'DELETE'}>
                  {result.method}
                </span>
                <span class="result-endpoint">{result.endpoint}</span>
                <span class="result-time">{result.timestamp}</span>
              </div>
              {#if result.requestData}
                <div class="result-request">
                  <strong>Request Data:</strong>
                  <pre>{JSON.stringify(result.requestData, null, 2)}</pre>
                </div>
              {/if}
              {#if result.success}
                <div class="result-data">
                  <strong>Response:</strong>
                  <pre>{JSON.stringify(result.data, null, 2)}</pre>
                </div>
              {:else}
                <div class="result-error">
                  <strong>Error:</strong> {result.error}
                </div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .debug-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
    background-color: #f5f5f5;
  }

  .debug-header {
    background: white;
    padding: 1rem 2rem;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .debug-header h1 {
    margin: 0;
    color: #333;
    font-size: 1.5rem;
  }

  .back-button {
    padding: 0.5rem 1rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
  }

  .back-button:hover {
    background-color: #357abd;
  }

  .debug-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .debug-sidebar {
    width: 400px;
    background: white;
    border-right: 1px solid #e0e0e0;
    overflow-y: auto;
    padding: 1.5rem;
  }

  .api-info {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .api-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .api-info h2 {
    margin: 0;
    font-size: 1.1rem;
    color: #333;
  }

  .toggle-button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
    color: #666;
    padding: 0.25rem 0.5rem;
  }

  .api-config-form {
    margin-top: 1rem;
  }

  .config-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .save-button, .reset-button {
    flex: 1;
    padding: 0.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
  }

  .save-button {
    background-color: #4a90e2;
    color: white;
  }

  .save-button:hover {
    background-color: #357abd;
  }

  .reset-button {
    background-color: #f5f5f5;
    color: #333;
  }

  .reset-button:hover {
    background-color: #e0e0e0;
  }

  .info-item {
    margin-bottom: 0.75rem;
  }

  .info-item strong {
    display: block;
    margin-bottom: 0.25rem;
    color: #555;
    font-size: 0.875rem;
  }

  .info-item code {
    display: block;
    padding: 0.5rem;
    background-color: #f5f5f5;
    border-radius: 4px;
    font-size: 0.75rem;
    word-break: break-all;
    color: #333;
  }

  .test-section h2 {
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
    color: #333;
  }

  .endpoint-group {
    margin-bottom: 0.75rem;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
  }

  .endpoint-header {
    width: 100%;
    padding: 0.75rem 1rem;
    background-color: #f8f9fa;
    border: none;
    text-align: left;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    color: #333;
  }

  .endpoint-header:hover {
    background-color: #e9ecef;
  }

  .toggle-icon {
    color: #666;
    font-size: 0.75rem;
  }

  .endpoint-content {
    padding: 1rem;
    background-color: white;
  }

  .endpoint-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .method-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
  }

  .method-badge.post {
    background-color: #4caf50;
  }

  .method-badge.get {
    background-color: #2196f3;
  }

  .method-badge.put {
    background-color: #ff9800;
  }

  .method-badge.patch {
    background-color: #9c27b0;
  }

  .method-badge.delete {
    background-color: #f44336;
  }

  .endpoint-path {
    font-family: monospace;
    font-size: 0.875rem;
    color: #333;
    background-color: #f5f5f5;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
  }

  .endpoint-description {
    margin-bottom: 1rem;
    font-size: 0.875rem;
    color: #666;
    line-height: 1.4;
  }

  .endpoint-note {
    margin: 0.75rem 0;
    padding: 0.5rem;
    background-color: #fff3cd;
    border-left: 3px solid #ffc107;
    border-radius: 3px;
    font-size: 0.8rem;
    color: #856404;
  }

  .request-data {
    margin: 0.75rem 0;
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-radius: 4px;
  }

  .request-data strong {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #555;
  }

  .request-data pre {
    margin: 0;
    font-size: 0.75rem;
    color: #333;
  }

  .file-info {
    margin: 0.75rem 0;
    padding: 0.5rem;
    background-color: #e3f2fd;
    border-radius: 4px;
    font-size: 0.875rem;
    color: #1976d2;
  }

  .input-group {
    margin-bottom: 0.75rem;
  }

  .input-group label {
    display: block;
    margin-bottom: 0.25rem;
    font-size: 0.875rem;
    color: #555;
  }

  .input-group input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    box-sizing: border-box;
  }

  .endpoint-content button {
    width: 100%;
    padding: 0.75rem;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    margin-top: 0.5rem;
  }

  .endpoint-content button:hover:not(:disabled) {
    background-color: #357abd;
  }

  .endpoint-content button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }

  .endpoint-content select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    box-sizing: border-box;
    background-color: white;
  }

  .endpoint-content textarea {
    width: 100%;
    min-height: 150px;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    font-family: monospace;
    box-sizing: border-box;
    resize: vertical;
  }

  .endpoint-content textarea.json-error {
    border-color: #f44336;
  }

  .error-message {
    margin-top: 0.25rem;
    color: #f44336;
    font-size: 0.75rem;
  }

  .custom-request {
    border: 2px solid #4a90e2;
  }

  .test-actions {
    margin-top: 1rem;
  }

  .clear-button {
    width: 100%;
    padding: 0.75rem;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
  }

  .clear-button:hover:not(:disabled) {
    background-color: #d32f2f;
  }

  .debug-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .results-header {
    background: white;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .results-header h2 {
    margin: 0;
    font-size: 1.1rem;
    color: #333;
  }

  .result-count {
    font-size: 0.875rem;
    color: #666;
  }

  .results-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
  }

  .empty-results {
    text-align: center;
    color: #999;
    padding: 3rem;
    font-size: 0.95rem;
  }

  .result-item {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .result-item.success {
    border-left: 4px solid #4caf50;
  }

  .result-item.error {
    border-left: 4px solid #f44336;
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #f0f0f0;
  }

  .result-method {
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
  }

  .result-method.post {
    background-color: #4caf50;
  }

  .result-method.get {
    background-color: #2196f3;
  }

  .result-method.put {
    background-color: #ff9800;
  }

  .result-method.patch {
    background-color: #9c27b0;
  }

  .result-method.delete {
    background-color: #f44336;
  }

  .result-endpoint {
    flex: 1;
    font-family: monospace;
    font-size: 0.875rem;
    color: #333;
  }

  .result-time {
    font-size: 0.75rem;
    color: #999;
  }

  .result-request {
    margin: 0.75rem 0;
    padding: 0.75rem;
    background-color: #f8f9fa;
    border-radius: 4px;
  }

  .result-request strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #555;
    font-size: 0.875rem;
  }

  .result-request pre {
    margin: 0;
    font-size: 0.8rem;
    line-height: 1.4;
  }

  .result-data {
    margin-top: 0.5rem;
  }

  .result-data strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #555;
    font-size: 0.875rem;
  }

  .result-data pre {
    margin: 0;
    padding: 0.75rem;
    background-color: #f8f9fa;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.8rem;
    line-height: 1.4;
  }

  .result-error {
    margin-top: 0.5rem;
    color: #d32f2f;
  }

  .result-error strong {
    display: block;
    margin-bottom: 0.25rem;
  }
</style>
