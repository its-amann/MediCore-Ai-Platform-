/**
 * WebSocket URL utility functions for consistent URL construction
 * Handles environment variables and proper URL formatting
 */

// Get WebSocket base URL from environment variables
const getWebSocketBaseUrl = (): string => {
  const wsUrl = process.env.REACT_APP_WS_URL;
  
  if (!wsUrl) {
    console.warn('REACT_APP_WS_URL not found in environment variables, using default');
    return 'ws://localhost:8000';
  }
  
  return wsUrl;
};

// Get API base URL for converting HTTP to WS
const getApiBaseUrl = (): string => {
  const apiUrl = process.env.REACT_APP_API_URL;
  
  if (!apiUrl) {
    console.warn('REACT_APP_API_URL not found in environment variables, using default');
    return 'http://localhost:8000/api/v1';
  }
  
  return apiUrl;
};

/**
 * Convert HTTP URL to WebSocket URL
 * Handles http/https to ws/wss conversion
 */
export const convertHttpToWs = (httpUrl: string): string => {
  return httpUrl.replace(/^https?:\/\//, (match) => {
    return match === 'https://' ? 'wss://' : 'ws://';
  });
};

/**
 * Construct WebSocket URL for different endpoints
 * @param endpoint - The WebSocket endpoint path (e.g., 'voice', 'room', 'medical-chat')
 * @param params - Additional parameters for the URL
 * @returns Complete WebSocket URL (without token - token should be passed via headers)
 */
export const buildWebSocketUrl = (
  endpoint: string, 
  params?: { 
    id?: string; 
    queryParams?: Record<string, string>; 
  }
): string => {
  const baseUrl = getWebSocketBaseUrl();
  
  // Ensure endpoint starts with 'ws/'
  const normalizedEndpoint = endpoint.startsWith('ws/') ? endpoint : `ws/${endpoint}`;
  
  // Build base URL
  let wsUrl = `${baseUrl}/${normalizedEndpoint}`;
  
  // Add ID if provided
  if (params?.id) {
    wsUrl += `/${params.id}`;
  }
  
  // Build query parameters (excluding token for security)
  const queryParams = new URLSearchParams();
  
  // Add additional query parameters
  if (params?.queryParams) {
    Object.entries(params.queryParams).forEach(([key, value]) => {
      queryParams.append(key, value);
    });
  }
  
  // Append query parameters if any exist
  const queryString = queryParams.toString();
  if (queryString) {
    wsUrl += `?${queryString}`;
  }
  
  return wsUrl;
};

/**
 * Build voice consultation WebSocket URL
 * @param sessionId - Voice session ID
 * @returns WebSocket URL for voice consultation (without token - token should be passed via headers)
 */
export const buildVoiceWebSocketUrl = (sessionId: string): string => {
  // Voice consultation WebSocket uses a different path structure
  const baseUrl = getWebSocketBaseUrl();
  
  // Match the backend route: /api/v1/voice/voice/ws/consultation/{consultation_session_id}
  return `${baseUrl}/api/v1/voice/voice/ws/consultation/${sessionId}`;
};

/**
 * Build room WebSocket URL
 * @param roomId - Room ID
 * @returns WebSocket URL for room communication (without token - token should be passed via headers)
 */
export const buildRoomWebSocketUrl = (roomId: string): string => {
  return buildWebSocketUrl('room', { 
    id: roomId
  });
};

/**
 * Build medical chat WebSocket URL
 * @param queryParams - Additional query parameters
 * @returns WebSocket URL for medical chat (without token - token should be passed via headers)
 */
export const buildMedicalChatWebSocketUrl = (
  queryParams?: Record<string, string>
): string => {
  return buildWebSocketUrl('medical-chat', { 
    queryParams 
  });
};

/**
 * Build workflow WebSocket URL
 * @param reportId - Report ID for workflow
 * @returns WebSocket URL for workflow progress (without token - token should be passed via headers)
 */
export const buildWorkflowWebSocketUrl = (reportId: string): string => {
  return buildWebSocketUrl('workflow', { 
    id: reportId
  });
};

/**
 * Create a WebSocket connection with authentication
 * @param url - The WebSocket URL to connect to
 * @param token - Authentication token (optional, will use localStorage if not provided)
 * @returns WebSocket instance with proper authentication headers
 */
export const createAuthenticatedWebSocket = (url: string, token?: string | null): WebSocket => {
  const authToken = token || localStorage.getItem('token');
  
  if (!authToken) {
    throw new Error('No authentication token available');
  }
  
  // Pass token via Sec-WebSocket-Protocol header for security
  // This prevents tokens from being logged in server access logs
  return new WebSocket(url, ['bearer', authToken]);
};

/**
 * Get current environment information
 * @returns Object containing environment details
 */
export const getWebSocketEnvironment = () => {
  return {
    wsBaseUrl: getWebSocketBaseUrl(),
    apiBaseUrl: getApiBaseUrl(),
    environment: process.env.REACT_APP_ENV || 'development',
    isProduction: process.env.REACT_APP_ENV === 'production',
    isDevelopment: process.env.REACT_APP_ENV === 'development' || !process.env.REACT_APP_ENV
  };
};

const websocketUtils = {
  buildWebSocketUrl,
  buildVoiceWebSocketUrl,
  buildRoomWebSocketUrl,
  buildMedicalChatWebSocketUrl,
  buildWorkflowWebSocketUrl,
  createAuthenticatedWebSocket,
  getWebSocketEnvironment,
  convertHttpToWs
};

export default websocketUtils;