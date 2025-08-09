import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  HeartIcon,
  UserGroupIcon,
  DocumentTextIcon,
  ClockIcon,
  ArrowRightIcon,
  PlusIcon
} from '@heroicons/react/24/outline';
import api from '../api/axios';
import { useAuthStore } from '../store/authStore';

interface DashboardStats {
  totalCases: number;
  activeCases: number;
  completedCases: number;
  totalConsultations: number;
  recentCases: Array<{
    id: string;
    title: string;
    status: string;
    lastUpdated: string;
    priority: string;
  }>;
}

const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats>({
    totalCases: 0,
    activeCases: 0,
    completedCases: 0,
    totalConsultations: 0,
    recentCases: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await api.get('/cases/user/cases');
      const cases = response.data || [];
      
      // Calculate stats
      const totalCases = cases.length;
      const activeCases = cases.filter((c: any) => c.status === 'active').length;
      const completedCases = cases.filter((c: any) => c.status === 'resolved').length;
      
      // Get recent cases (last 5)
      const recentCases = cases
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5)
        .map((c: any) => ({
          id: c.case_id,
          title: c.chief_complaint || 'Medical Case',
          status: c.status,
          lastUpdated: new Date(c.updated_at || c.created_at).toLocaleDateString(),
          priority: c.priority || 'medium'
        }));

      setStats({
        totalCases,
        activeCases,
        completedCases,
        totalConsultations: 0, // This would come from a consultations endpoint
        recentCases
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard: React.FC<{
    title: string;
    value: number;
    icon: React.ReactNode;
    bgColor: string;
  }> = ({ title, value, icon, bgColor }) => (
    <div className={`${bgColor} rounded-lg p-6 text-white`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm opacity-90">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
        </div>
        <div className="opacity-80">{icon}</div>
      </div>
    </div>
  );

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'emergency':
        return 'text-red-600 bg-red-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-green-600 bg-green-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-blue-600 bg-blue-100';
      case 'in_progress':
        return 'text-purple-600 bg-purple-100';
      case 'resolved':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.username || 'Patient'}!
        </h1>
        <p className="text-gray-600 mt-2">
          Here's an overview of your medical cases and consultations.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Cases"
          value={stats.totalCases}
          icon={<DocumentTextIcon className="h-8 w-8" />}
          bgColor="bg-blue-600"
        />
        <StatCard
          title="Active Cases"
          value={stats.activeCases}
          icon={<ClockIcon className="h-8 w-8" />}
          bgColor="bg-purple-600"
        />
        <StatCard
          title="Completed Cases"
          value={stats.completedCases}
          icon={<UserGroupIcon className="h-8 w-8" />}
          bgColor="bg-green-600"
        />
        <StatCard
          title="Consultations"
          value={stats.totalConsultations}
          icon={<HeartIcon className="h-8 w-8" />}
          bgColor="bg-pink-600"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/cases/new"
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 p-2 rounded-lg">
                <PlusIcon className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">New Case</p>
                <p className="text-sm text-gray-600">Start a new medical case</p>
              </div>
            </div>
            <ArrowRightIcon className="h-5 w-5 text-gray-400" />
          </Link>

          <Link
            to="/consultations"
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div className="bg-purple-100 p-2 rounded-lg">
                <UserGroupIcon className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Consult Doctor</p>
                <p className="text-sm text-gray-600">Talk to an AI specialist</p>
              </div>
            </div>
            <ArrowRightIcon className="h-5 w-5 text-gray-400" />
          </Link>

          <Link
            to="/imaging"
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div className="bg-green-100 p-2 rounded-lg">
                <DocumentTextIcon className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Upload Image</p>
                <p className="text-sm text-gray-600">Analyze medical images</p>
              </div>
            </div>
            <ArrowRightIcon className="h-5 w-5 text-gray-400" />
          </Link>
        </div>
      </div>

      {/* Recent Cases */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Cases</h2>
            <Link to="/cases" className="text-sm text-blue-600 hover:text-blue-700">
              View all cases →
            </Link>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {stats.recentCases.length > 0 ? (
            stats.recentCases.map((caseItem) => (
              <Link
                key={caseItem.id}
                to={`/cases/${caseItem.id}`}
                className="p-6 hover:bg-gray-50 transition-colors block"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{caseItem.title}</h3>
                    <div className="flex items-center space-x-4 mt-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(caseItem.status)}`}>
                        {caseItem.status.charAt(0).toUpperCase() + caseItem.status.slice(1).replace('_', ' ')}
                      </span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(caseItem.priority)}`}>
                        {caseItem.priority.charAt(0).toUpperCase() + caseItem.priority.slice(1)} Priority
                      </span>
                      <span className="text-sm text-gray-500">
                        Updated {caseItem.lastUpdated}
                      </span>
                    </div>
                  </div>
                  <ArrowRightIcon className="h-5 w-5 text-gray-400 ml-4" />
                </div>
              </Link>
            ))
          ) : (
            <div className="p-6 text-center text-gray-500">
              <p>No cases yet.</p>
              <Link to="/cases/new" className="text-blue-600 hover:text-blue-700 mt-2 inline-block">
                Create your first case →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;