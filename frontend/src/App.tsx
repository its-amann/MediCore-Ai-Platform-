import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';

// Context Providers
import WebSocketProvider from './contexts/WebSocketContext';

// Layout
import Layout from './components/layout/Layout';

// Auth Components
import LoginForm from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';

// Protected Route Component
import { ProtectedRoute } from './components/auth/ProtectedRoute';

// Pages
import Dashboard from './pages/Dashboard';
import Cases from './pages/Cases';
import NewCase from './pages/NewCase';
import CaseDetails from './pages/CaseDetails';
import Consultation from './pages/Consultation';
import TestChat from './pages/TestChat';
import RoomList from './pages/RoomList';
import RoomDetail from './pages/RoomDetailNew';
import CreateRoom from './pages/CreateRoom';
import RoomSettings from './pages/RoomSettings';
import Profile from './pages/Profile';

// Lazy loaded components for better performance
import { 
  LazyWrapper, 
  LazyAnalyticsDashboard, 
  LazyMediaGallery, 
  LazyMedicalImaging, 
  LazyVoiceConsultation,
  LazyVoiceConsultationNew,
  LazyVoiceConsultationGeminiLive,
  LazyReports,
  LazyReportViewer, 
  LazySettings
} from './components/LazyComponents';

function App() {
  const { checkAuth, isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <WebSocketProvider>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            style: {
              background: '#10b981',
            },
          },
          error: {
            style: {
              background: '#ef4444',
            },
          },
        }}
      />

      <Routes>
        {/* Auth Routes */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/dashboard" /> : <LoginForm />
        } />
        <Route path="/register" element={
          isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterForm />
        } />
        
        {/* Test Route - No Auth Required */}
        <Route path="/test-chat" element={<TestChat />} />

        {/* Protected Routes */}
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/cases/new" element={<NewCase />} />
          <Route path="/cases/:caseId" element={<CaseDetails />} />
          <Route path="/consultation/:caseId" element={<Consultation />} />
          
          {/* Collaboration Rooms */}
          <Route path="/rooms" element={<RoomList />} />
          <Route path="/rooms/new" element={<CreateRoom />} />
          <Route path="/rooms/:roomId" element={<RoomDetail />} />
          <Route path="/rooms/:roomId/settings" element={<RoomSettings />} />
          
          {/* Analytics Dashboard */}
          <Route path="/analytics" element={
            <LazyWrapper>
              <LazyAnalyticsDashboard />
            </LazyWrapper>
          } />
          
          {/* Medical Imaging */}
          <Route path="/imaging" element={
            <LazyWrapper>
              <LazyMedicalImaging />
            </LazyWrapper>
          } />
          
          {/* Voice Consultation */}
          <Route path="/voice" element={
            <LazyWrapper>
              <LazyVoiceConsultation />
            </LazyWrapper>
          } />
          
          {/* New Voice Consultation with LangGraph */}
          <Route path="/voice-new" element={
            <LazyWrapper>
              <LazyVoiceConsultationNew />
            </LazyWrapper>
          } />
          
          {/* Gemini Live Voice Consultation */}
          <Route path="/voice-live" element={
            <LazyWrapper>
              <LazyVoiceConsultationGeminiLive />
            </LazyWrapper>
          } />
          
          {/* Reports */}
          <Route path="/reports" element={
            <LazyWrapper>
              <LazyReports />
            </LazyWrapper>
          } />
          <Route path="/reports/:reportId" element={
            <LazyWrapper>
              <LazyReportViewer />
            </LazyWrapper>
          } />
          
          {/* Settings */}
          <Route path="/settings" element={
            <LazyWrapper>
              <LazySettings />
            </LazyWrapper>
          } />
          
          {/* Profile */}
          <Route path="/profile" element={<Profile />} />
          
          {/* Media Management */}
          <Route path="/media" element={
            <div className="p-6">
              <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Media Library</h1>
                <p className="text-gray-600 mt-1">Manage your uploaded medical files and images</p>
              </div>
              <LazyWrapper>
                <LazyMediaGallery />
              </LazyWrapper>
            </div>
          } />
          
          {/* Doctor Selection - Will be modal-based */}
          <Route path="/doctors" element={
            <div className="p-6">
              <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">AI Doctors</h1>
                <p className="text-gray-600 mt-1">Choose from our specialized AI medical consultants</p>
              </div>
              <div className="text-center py-12">
                <p className="text-gray-500">Doctor selection is available through the consultation interface.</p>
              </div>
            </div>
          } />
        </Route>

        {/* Default Route */}
        <Route path="/" element={
          isAuthenticated ? <Navigate to="/dashboard" /> : <Navigate to="/login" />
        } />

        {/* 404 Route */}
        <Route path="*" element={
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <h1 className="text-6xl font-bold text-gray-300">404</h1>
              <p className="text-xl text-gray-600 mt-4">Page not found</p>
              <a href="/dashboard" className="btn-primary mt-6 inline-block">
                Go to Dashboard
              </a>
            </div>
          </div>
        } />
      </Routes>
    </WebSocketProvider>
  );
}

export default App;