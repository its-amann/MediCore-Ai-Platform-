import React, { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  UsersIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  DocumentTextIcon,
  HeartIcon,
  CalendarIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { format, subDays, parseISO } from 'date-fns';
import toast from 'react-hot-toast';
import api from '../../api/axios';

interface AnalyticsData {
  // Dashboard overview
  totalCases: number;
  activeCases: number;
  resolvedCases: number;
  totalConsultations: number;
  averageResolutionTime: number;
  
  // Specialty performance
  specialtyStats: {
    specialty: string;
    consultations: number;
    averageRating: number;
    averageResponseTime: number;
    successRate: number;
  }[];
  
  // Case trends
  caseTrends: {
    date: string;
    newCases: number;
    resolvedCases: number;
    activeCases: number;
  }[];
  
  // Consultation trends
  consultationTrends: {
    date: string;
    consultations: number;
    averageRating: number;
    responseTime: number;
  }[];
  
  // Condition analysis
  topConditions: {
    condition: string;
    count: number;
    trend: 'up' | 'down' | 'stable';
    percentage: number;
  }[];
  
  // Response time analytics
  responseTimeDistribution: {
    timeRange: string;
    count: number;
    percentage: number;
  }[];
  
  // User engagement
  userEngagement: {
    date: string;
    activeUsers: number;
    newUsers: number;
    returningUsers: number;
  }[];
}

interface AnalyticsDashboardProps {
  className?: string;
}

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ className = '' }) => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [selectedMetric, setSelectedMetric] = useState<'cases' | 'consultations' | 'users'>('cases');

  useEffect(() => {
    fetchAnalyticsData();
  }, [timeRange]);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      const [dashboardResponse, specialtyResponse, trendsResponse, performanceResponse] = 
        await Promise.all([
          api.get(`/analytics/dashboard?period=${timeRange}`),
          api.get('/analytics/specialties/comparison'),
          api.get(`/analytics/trends/conditions?period=${timeRange}`),
          api.get(`/analytics/performance/response-times?period=${timeRange}`)
        ]);

      // Combine all analytics data
      const analyticsData: AnalyticsData = {
        ...dashboardResponse.data,
        specialtyStats: specialtyResponse.data.specialties || [],
        topConditions: trendsResponse.data.conditions || [],
        responseTimeDistribution: performanceResponse.data.distribution || [],
        // Mock some additional data for demo
        caseTrends: generateCaseTrendData(),
        consultationTrends: generateConsultationTrendData(),
        userEngagement: generateUserEngagementData()
      };

      setData(analyticsData);
    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
      toast.error('Failed to load analytics data');
      // Set mock data for demo
      setData(generateMockAnalyticsData());
    } finally {
      setLoading(false);
    }
  };

  const generateCaseTrendData = () => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
    return Array.from({ length: days }, (_, i) => {
      const date = format(subDays(new Date(), days - i - 1), 'yyyy-MM-dd');
      return {
        date,
        newCases: Math.floor(Math.random() * 20) + 5,
        resolvedCases: Math.floor(Math.random() * 15) + 3,
        activeCases: Math.floor(Math.random() * 50) + 20
      };
    });
  };

  const generateConsultationTrendData = () => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
    return Array.from({ length: days }, (_, i) => {
      const date = format(subDays(new Date(), days - i - 1), 'yyyy-MM-dd');
      return {
        date,
        consultations: Math.floor(Math.random() * 30) + 10,
        averageRating: Number((Math.random() * 2 + 3).toFixed(1)),
        responseTime: Math.floor(Math.random() * 60) + 30
      };
    });
  };

  const generateUserEngagementData = () => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
    return Array.from({ length: days }, (_, i) => {
      const date = format(subDays(new Date(), days - i - 1), 'yyyy-MM-dd');
      return {
        date,
        activeUsers: Math.floor(Math.random() * 100) + 50,
        newUsers: Math.floor(Math.random() * 20) + 5,
        returningUsers: Math.floor(Math.random() * 80) + 40
      };
    });
  };

  const generateMockAnalyticsData = (): AnalyticsData => ({
    totalCases: 1247,
    activeCases: 89,
    resolvedCases: 1158,
    totalConsultations: 2341,
    averageResolutionTime: 4.2,
    specialtyStats: [
      {
        specialty: 'Cardiologist',
        consultations: 856,
        averageRating: 4.7,
        averageResponseTime: 45,
        successRate: 94.2
      },
      {
        specialty: 'BP Specialist',
        consultations: 623,
        averageRating: 4.5,
        averageResponseTime: 38,
        successRate: 96.1
      },
      {
        specialty: 'General Consultant',
        consultations: 862,
        averageRating: 4.6,
        averageResponseTime: 52,
        successRate: 91.8
      }
    ],
    caseTrends: generateCaseTrendData(),
    consultationTrends: generateConsultationTrendData(),
    userEngagement: generateUserEngagementData(),
    topConditions: [
      { condition: 'Hypertension', count: 234, trend: 'up', percentage: 18.7 },
      { condition: 'Chest Pain', count: 198, trend: 'stable', percentage: 15.8 },
      { condition: 'Heart Palpitations', count: 167, trend: 'down', percentage: 13.4 },
      { condition: 'Shortness of Breath', count: 143, trend: 'up', percentage: 11.4 },
      { condition: 'Fatigue', count: 129, trend: 'stable', percentage: 10.3 }
    ],
    responseTimeDistribution: [
      { timeRange: '0-30s', count: 1234, percentage: 52.7 },
      { timeRange: '30s-1m', count: 678, percentage: 28.9 },
      { timeRange: '1-2m', count: 234, percentage: 10.0 },
      { timeRange: '2-5m', count: 145, percentage: 6.2 },
      { timeRange: '5m+', count: 50, percentage: 2.1 }
    ]
  });

  const exportAnalytics = async (format: 'csv' | 'pdf' | 'json') => {
    try {
      const response = await api.get(`/analytics/export/summary?format=${format}&period=${timeRange}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analytics_${timeRange}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Analytics exported as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Failed to export analytics:', error);
      toast.error('Failed to export analytics');
    }
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    change?: string;
    changeType?: 'positive' | 'negative' | 'neutral';
    icon: React.ReactNode;
    color: string;
  }> = ({ title, value, change, changeType = 'neutral', icon, color }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold text-gray-900">{value}</p>
            {change && (
              <p className={`ml-2 text-sm font-medium ${
                changeType === 'positive' ? 'text-green-600' : 
                changeType === 'negative' ? 'text-red-600' : 
                'text-gray-600'
              }`}>
                {change}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-96 ${className}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Comprehensive insights into your medical AI platform performance
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Time Range Selector */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>

          {/* Export Button */}
          <div className="relative group">
            <button className="btn-secondary flex items-center">
              <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
              Export
            </button>
            <div className="absolute right-0 mt-2 w-32 bg-white rounded-md shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
              <button
                onClick={() => exportAnalytics('csv')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Export CSV
              </button>
              <button
                onClick={() => exportAnalytics('pdf')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Export PDF
              </button>
              <button
                onClick={() => exportAnalytics('json')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Export JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <StatCard
          title="Total Cases"
          value={data.totalCases.toLocaleString()}
          change="+12.5%"
          changeType="positive"
          icon={<DocumentTextIcon className="h-6 w-6 text-white" />}
          color="bg-blue-500"
        />
        <StatCard
          title="Active Cases"
          value={data.activeCases}
          change="-3.2%"
          changeType="negative"
          icon={<ClockIcon className="h-6 w-6 text-white" />}
          color="bg-yellow-500"
        />
        <StatCard
          title="Resolved Cases"
          value={data.resolvedCases.toLocaleString()}
          change="+8.7%"
          changeType="positive"
          icon={<ChartBarIcon className="h-6 w-6 text-white" />}
          color="bg-green-500"
        />
        <StatCard
          title="Total Consultations"
          value={data.totalConsultations.toLocaleString()}
          change="+15.3%"
          changeType="positive"
          icon={<HeartIcon className="h-6 w-6 text-white" />}
          color="bg-red-500"
        />
        <StatCard
          title="Avg Resolution Time"
          value={`${data.averageResolutionTime} days`}
          change="-0.8 days"
          changeType="positive"
          icon={<ArrowTrendingUpIcon className="h-6 w-6 text-white" />}
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Case Trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Case Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.caseTrends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => format(parseISO(value), 'MMM dd')}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => format(parseISO(value as string), 'MMM dd, yyyy')}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="newCases" 
                stackId="1" 
                stroke="#3B82F6" 
                fill="#3B82F6" 
                fillOpacity={0.6}
                name="New Cases"
              />
              <Area 
                type="monotone" 
                dataKey="resolvedCases" 
                stackId="1" 
                stroke="#10B981" 
                fill="#10B981" 
                fillOpacity={0.6}
                name="Resolved Cases"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Specialty Performance */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Specialty Performance</h3>
          <div className="space-y-4">
            {data.specialtyStats.map((specialty, index) => (
              <div key={specialty.specialty} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">{specialty.specialty}</p>
                  <p className="text-sm text-gray-600">
                    {specialty.consultations} consultations • {specialty.averageResponseTime}s avg response
                  </p>
                </div>
                <div className="text-right">
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <span
                        key={i}
                        className={`text-sm ${
                          i < Math.floor(specialty.averageRating) ? 'text-yellow-400' : 'text-gray-300'
                        }`}
                      >
                        ★
                      </span>
                    ))}
                    <span className="ml-1 text-sm text-gray-600">
                      {specialty.averageRating}
                    </span>
                  </div>
                  <p className="text-sm text-green-600">{specialty.successRate}% success</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Conditions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Conditions</h3>
          <div className="space-y-3">
            {data.topConditions.map((condition, index) => (
              <div key={condition.condition} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full`} style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="text-sm font-medium text-gray-900">{condition.condition}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">{condition.count}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    condition.trend === 'up' ? 'bg-green-100 text-green-800' :
                    condition.trend === 'down' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {condition.trend === 'up' ? '↑' : condition.trend === 'down' ? '↓' : '→'}
                    {condition.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Response Time Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data.responseTimeDistribution}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={80}
                paddingAngle={5}
                dataKey="count"
              >
                {data.responseTimeDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value, name) => [`${value} consultations`, 'Count']} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {data.responseTimeDistribution.map((item, index) => (
              <div key={item.timeRange} className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-gray-700">{item.timeRange}</span>
                </div>
                <span className="text-gray-600">{item.percentage}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Consultation Trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Consultations</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.consultationTrends.slice(-7)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => format(parseISO(value), 'EEE')}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => format(parseISO(value as string), 'MMM dd')}
              />
              <Bar dataKey="consultations" fill="#3B82F6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;