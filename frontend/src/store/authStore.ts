import { create } from 'zustand';
import axios from 'axios';
import { toast } from 'react-hot-toast';

interface User {
  user_id: string;
  username: string;
  email?: string;
  first_name: string;
  last_name: string;
  role: string;
  created_at: string;
  last_login?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  tokenStatus: {
    shouldRefresh: boolean;
    expiresInSeconds: number;
    inGracePeriod: boolean;
  } | null;
  login: (username: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
  checkTokenStatus: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  clearError: () => void;
}

interface RegisterData {
  username: string;
  password: string;
  email?: string;
  first_name: string;
  last_name: string;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const ACCESS_TOKEN_EXPIRE_MINUTES = 120; // Should match backend setting

// Configure axios defaults
axios.defaults.baseURL = API_BASE_URL;

// Add token to requests if available
axios.interceptors.request.use(
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

// Handle 401 responses with token refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post('/auth/refresh', {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken);
          }
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return axios(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout user
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  tokenStatus: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post('/auth/login', {
        username,
        password
      });

      const { access_token, refresh_token, expires_in } = response.data;
      
      // Store tokens
      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }
      
      // Get user profile
      const profileResponse = await axios.get('/auth/me');
      const user = profileResponse.data;
      
      // Store user and individual fields for WebSocket
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('user_id', user.user_id);
      localStorage.setItem('username', user.username);
      
      set({
        token: access_token,
        refreshToken: refresh_token,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        tokenStatus: {
          shouldRefresh: false,
          expiresInSeconds: expires_in || ACCESS_TOKEN_EXPIRE_MINUTES * 60,
          inGracePeriod: false
        }
      });

      toast.success('Login successful!');
    } catch (error: any) {
      // Extract error message from different possible structures
      let errorMessage = 'Login failed';
      
      if (error.response?.data) {
        const data = error.response.data;
        
        // Handle FastAPI validation errors or HTTPExceptions
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (data.error) {
          errorMessage = data.error;
        }
      }
      
      set({ 
        error: errorMessage, 
        isLoading: false,
        isAuthenticated: false 
      });
      toast.error(errorMessage);
      throw error;
    }
  },

  register: async (userData: RegisterData) => {
    set({ isLoading: true, error: null });
    try {
      await axios.post('/auth/register', userData);
      
      toast.success('Registration successful! Please login.');
      
      // Auto-login after registration
      await get().login(userData.username, userData.password);
    } catch (error: any) {
      // Extract error message from different possible structures
      let errorMessage = 'Registration failed';
      
      if (error.response?.data) {
        const data = error.response.data;
        
        // Handle FastAPI validation errors or HTTPExceptions
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (data.error) {
          errorMessage = data.error;
        } else if (Array.isArray(data.detail)) {
          // Handle array of validation errors
          const firstError = data.detail[0];
          if (firstError?.msg) {
            const field = firstError.loc?.[firstError.loc.length - 1] || 'field';
            errorMessage = `${field}: ${firstError.msg}`;
          }
        }
      }
      
      set({ 
        error: errorMessage, 
        isLoading: false 
      });
      toast.error(errorMessage);
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false
    });

    toast.success('Logged out successfully');
    window.location.href = '/login';
  },

  checkAuth: () => {
    const token = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userStr = localStorage.getItem('user');

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        
        // Ensure user_id and username are in localStorage for WebSocket
        if (user.user_id && user.username) {
          localStorage.setItem('user_id', user.user_id);
          localStorage.setItem('username', user.username);
        }
        
        set({
          user,
          token,
          refreshToken,
          isAuthenticated: true,
          isLoading: false
        });
        
        // Check token status after setting auth
        get().checkTokenStatus();
      } catch (error) {
        console.error('Failed to parse user data:', error);
        get().logout();
      }
    } else {
      set({
        isAuthenticated: false,
        isLoading: false
      });
    }
  },

  checkTokenStatus: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      const response = await axios.get('/auth/token/status');
      const status = response.data;
      
      set({
        tokenStatus: {
          shouldRefresh: status.should_refresh,
          expiresInSeconds: status.expires_in_seconds,
          inGracePeriod: status.in_grace_period
        }
      });

      // Auto-refresh if needed
      if (status.should_refresh && !status.expired) {
        get().refreshAccessToken();
      }
    } catch (error) {
      console.error('Failed to check token status:', error);
    }
  },

  refreshAccessToken: async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      get().logout();
      return false;
    }

    try {
      const response = await axios.post('/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken } = response.data;
      localStorage.setItem('access_token', access_token);
      
      if (newRefreshToken) {
        localStorage.setItem('refresh_token', newRefreshToken);
      }

      set({
        token: access_token,
        refreshToken: newRefreshToken || refreshToken,
        tokenStatus: {
          shouldRefresh: false,
          expiresInSeconds: ACCESS_TOKEN_EXPIRE_MINUTES * 60,
          inGracePeriod: false
        }
      });

      console.log('Token refreshed successfully');
      return true;
    } catch (error: any) {
      console.error('Token refresh failed:', error);
      if (error.response?.status === 401) {
        get().logout();
      }
      return false;
    }
  },

  updateProfile: async (data: Partial<User>) => {
    try {
      const response = await axios.put('/auth/profile', data);
      const updatedUser = response.data;
      
      // Update stored user
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      set({ user: updatedUser });
      
      toast.success('Profile updated successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  }
}));