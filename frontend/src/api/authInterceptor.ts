import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Track refresh attempts to prevent infinite loops
let refreshAttempts = 0;
const MAX_REFRESH_ATTEMPTS = 3;

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh with enhanced error handling
apiClient.interceptors.response.use(
  (response) => {
    // Reset refresh attempts on successful response
    refreshAttempts = 0;
    
    // Check for token refresh warnings in response headers
    const tokenStatus = response.headers['x-token-status'];
    const refreshRequired = response.headers['x-refresh-required'];
    
    if (tokenStatus === 'expired' || refreshRequired === 'true') {
      console.warn('Token refresh required according to response headers');
      // Trigger background refresh
      refreshTokenInBackground();
    }
    
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors with token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Check if we've exceeded max refresh attempts
      if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
        console.error('Max refresh attempts exceeded');
        handleLogout('Multiple authentication failures');
        return Promise.reject(error);
      }

      try {
        refreshAttempts++;
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        console.log(`Attempting token refresh (attempt ${refreshAttempts}/${MAX_REFRESH_ATTEMPTS})`);
        
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        
        // Update stored tokens
        localStorage.setItem('access_token', access_token);
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken);
        }

        // Reset refresh attempts on successful refresh
        refreshAttempts = 0;
        
        // Emit refresh event
        window.dispatchEvent(new CustomEvent('tokenRefreshed', {
          detail: { access_token, refresh_token: newRefreshToken }
        }));

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
        
      } catch (refreshError: any) {
        console.error('Token refresh failed:', refreshError);
        
        // Check if refresh token is also expired
        if (refreshError.response?.status === 401) {
          handleLogout('Session expired');
        } else {
          handleLogout('Authentication error');
        }
        
        return Promise.reject(refreshError);
      }
    }

    // Handle other error status codes
    if (error.response?.status === 403) {
      toast.error('Access denied. You do not have permission to perform this action.');
    } else if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.');
    }

    return Promise.reject(error);
  }
);

/**
 * Handle logout and cleanup
 */
function handleLogout(reason: string): void {
  console.log(`Logging out user: ${reason}`);
  
  // Clear stored data
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  
  // Show appropriate message
  if (reason.includes('expired')) {
    toast.error('Your session has expired. Please log in again.');
  } else {
    toast.error('Authentication failed. Please log in again.');
  }
  
  // Emit logout event
  window.dispatchEvent(new CustomEvent('tokenExpired', { detail: { reason } }));
  
  // Redirect to login if not already there
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

/**
 * Refresh token in background without blocking the UI
 */
async function refreshTokenInBackground(): Promise<void> {
  try {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return;
    
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });
    
    const { access_token, refresh_token: newRefreshToken } = response.data;
    localStorage.setItem('access_token', access_token);
    
    if (newRefreshToken) {
      localStorage.setItem('refresh_token', newRefreshToken);
    }
    
    console.log('Background token refresh successful');
    
    // Emit refresh event
    window.dispatchEvent(new CustomEvent('tokenRefreshed', {
      detail: { access_token, refresh_token: newRefreshToken }
    }));
    
  } catch (error) {
    console.error('Background token refresh failed:', error);
  }
}

export default apiClient;