/**
 * Unit tests for WebSocket utility functions
 */

import {
  buildWebSocketUrl,
  buildVoiceWebSocketUrl,
  buildRoomWebSocketUrl,
  buildMedicalChatWebSocketUrl,
  buildWorkflowWebSocketUrl,
  createAuthenticatedWebSocket,
  getWebSocketEnvironment
} from './websocketUtils';

// Mock environment variables
const originalEnv = process.env;

beforeEach(() => {
  jest.resetModules();
  process.env = { ...originalEnv };
});

afterAll(() => {
  process.env = originalEnv;
});

describe('WebSocket Utils', () => {
  describe('buildWebSocketUrl', () => {
    test('should build basic WebSocket URL', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWebSocketUrl('test-endpoint');
      expect(url).toBe('ws://localhost:8000/ws/test-endpoint');
    });

    test('should handle endpoint with ws/ prefix', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWebSocketUrl('ws/test-endpoint');
      expect(url).toBe('ws://localhost:8000/ws/test-endpoint');
    });

    test('should add ID parameter', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWebSocketUrl('voice', { id: 'session-123' });
      expect(url).toBe('ws://localhost:8000/ws/voice/session-123');
    });

    test('should not include token in URL for security', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWebSocketUrl('voice');
      expect(url).toBe('ws://localhost:8000/ws/voice');
      // Tokens should be passed via headers, not URL parameters
    });

    test('should add multiple query parameters (excluding token)', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWebSocketUrl('test', {
        id: 'room-456',
        queryParams: { debug: 'true', version: '1.0' }
      });
      expect(url).toBe('ws://localhost:8000/ws/test/room-456?debug=true&version=1.0');
    });

    test('should use default URL when environment variable is missing', () => {
      delete process.env.REACT_APP_WS_URL;
      const url = buildWebSocketUrl('test');
      expect(url).toBe('ws://localhost:8000/ws/test');
    });
  });

  describe('buildVoiceWebSocketUrl', () => {
    test('should build voice WebSocket URL with special path', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildVoiceWebSocketUrl('session-123');
      expect(url).toBe('ws://localhost:8000/api/v1/voice/voice/ws/consultation/session-123');
    });

    test('should not include token in URL', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildVoiceWebSocketUrl('session-456');
      expect(url).toBe('ws://localhost:8000/api/v1/voice/voice/ws/consultation/session-456');
      // Tokens should be passed via headers, not URL parameters
    });
  });

  describe('buildRoomWebSocketUrl', () => {
    test('should build room WebSocket URL', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildRoomWebSocketUrl('room-789');
      expect(url).toBe('ws://localhost:8000/ws/room/room-789');
    });
  });

  describe('buildMedicalChatWebSocketUrl', () => {
    test('should build medical chat WebSocket URL', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildMedicalChatWebSocketUrl();
      expect(url).toBe('ws://localhost:8000/ws/medical-chat');
    });

    test('should include query parameters (excluding token)', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildMedicalChatWebSocketUrl({ reportId: 'report-456' });
      expect(url).toBe('ws://localhost:8000/ws/medical-chat?reportId=report-456');
    });
  });

  describe('buildWorkflowWebSocketUrl', () => {
    test('should build workflow WebSocket URL', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      const url = buildWorkflowWebSocketUrl('report-123');
      expect(url).toBe('ws://localhost:8000/ws/workflow/report-123');
    });
  });

  describe('getWebSocketEnvironment', () => {
    test('should return environment information', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
      process.env.REACT_APP_API_URL = 'http://localhost:8000/api/v1';
      process.env.REACT_APP_ENV = 'development';

      const env = getWebSocketEnvironment();
      
      expect(env.wsBaseUrl).toBe('ws://localhost:8000');
      expect(env.apiBaseUrl).toBe('http://localhost:8000/api/v1');
      expect(env.environment).toBe('development');
      expect(env.isDevelopment).toBe(true);
      expect(env.isProduction).toBe(false);
    });

    test('should handle production environment', () => {
      process.env.REACT_APP_ENV = 'production';
      
      const env = getWebSocketEnvironment();
      
      expect(env.environment).toBe('production');
      expect(env.isDevelopment).toBe(false);
      expect(env.isProduction).toBe(true);
    });

    test('should use defaults when environment variables are missing', () => {
      delete process.env.REACT_APP_WS_URL;
      delete process.env.REACT_APP_API_URL;
      delete process.env.REACT_APP_ENV;

      const env = getWebSocketEnvironment();
      
      expect(env.wsBaseUrl).toBe('ws://localhost:8000');
      expect(env.apiBaseUrl).toBe('http://localhost:8000/api/v1');
      expect(env.environment).toBe('development');
      expect(env.isDevelopment).toBe(true);
      expect(env.isProduction).toBe(false);
    });
  });

  describe('Production environment handling', () => {
    test('should handle HTTPS to WSS conversion', () => {
      process.env.REACT_APP_WS_URL = 'wss://production-server.com';
      const url = buildWebSocketUrl('voice', { id: 'session-123' });
      expect(url).toBe('wss://production-server.com/ws/voice/session-123');
    });

    test('should handle different ports', () => {
      process.env.REACT_APP_WS_URL = 'ws://localhost:3001';
      const url = buildWebSocketUrl('room', { id: 'room-456' });
      expect(url).toBe('ws://localhost:3001/ws/room/room-456');
    });
  });

  describe('createAuthenticatedWebSocket', () => {
    // Mock WebSocket
    const mockWebSocket = jest.fn();
    (global as any).WebSocket = mockWebSocket;

    beforeEach(() => {
      mockWebSocket.mockClear();
      localStorage.clear();
    });

    test('should create WebSocket with bearer token protocol', () => {
      localStorage.setItem('token', 'test-token-123');
      
      createAuthenticatedWebSocket('ws://localhost:8000/ws/test');
      
      expect(mockWebSocket).toHaveBeenCalledWith(
        'ws://localhost:8000/ws/test',
        ['bearer', 'test-token-123']
      );
    });

    test('should use provided token over localStorage', () => {
      localStorage.setItem('token', 'stored-token');
      
      createAuthenticatedWebSocket('ws://localhost:8000/ws/test', 'provided-token');
      
      expect(mockWebSocket).toHaveBeenCalledWith(
        'ws://localhost:8000/ws/test',
        ['bearer', 'provided-token']
      );
    });

    test('should throw error when no token available', () => {
      expect(() => {
        createAuthenticatedWebSocket('ws://localhost:8000/ws/test');
      }).toThrow('No authentication token available');
    });
  });
});