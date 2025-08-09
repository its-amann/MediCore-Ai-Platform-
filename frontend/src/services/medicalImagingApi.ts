import axios from 'axios';
import { useAuthStore } from '../store/authStore';

// Medical Imaging API uses the standard API v1 path
const MEDICAL_IMAGING_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const medicalImagingApi = axios.create({
  baseURL: MEDICAL_IMAGING_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
medicalImagingApi.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
medicalImagingApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default medicalImagingApi;