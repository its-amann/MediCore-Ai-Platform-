import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  DocumentTextIcon,
  CalendarIcon,
  ChartBarIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import api from '../api/axios';
import toast from 'react-hot-toast';

interface Report {
  id: string;
  title: string;
  type: 'case_summary' | 'health_overview' | 'consultation_history' | 'lab_results' | 'medical_imaging';
  generatedAt: string;
  caseId?: string;
  caseName?: string;
  status: 'ready' | 'generating' | 'failed';
  fileUrl?: string;
  summary?: string;
}

const Reports: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [generatingReport, setGeneratingReport] = useState(false);

  useEffect(() => {
    fetchReports();
    
    // Check if we should open a specific report
    const reportId = searchParams.get('reportId');
    if (reportId) {
      // Auto-navigate to the report detail page
      navigate(`/reports/${reportId}`);
    }
  }, [searchParams, navigate]);

  const fetchReports = async () => {
    try {
      // Try to fetch medical imaging reports first
      try {
        const response = await api.get('/medical-imaging/imaging-reports/recent');
        if (response.data && response.data.length > 0) {
          const medicalReports = response.data.map((r: any) => ({
            id: r.id || r.report_id,
            title: `Medical Imaging Report - ${r.studyType || 'Imaging'}`,
            type: 'medical_imaging' as const,
            generatedAt: r.createdAt || r.created_at,
            caseId: r.caseId || r.case_id,
            status: 'ready' as const,
            summary: r.radiologicalAnalysis?.substring(0, 200) || r.overall_analysis?.substring(0, 200) || 'Medical imaging analysis complete'
          }));
          setReports(prev => [...medicalReports, ...prev]);
        }
      } catch (err) {
        console.log('No medical imaging reports found');
      }
      
      // Mock data for now
      setReports([
        {
          id: '1',
          title: 'Monthly Health Summary - November 2024',
          type: 'health_overview',
          generatedAt: '2024-11-30T10:00:00Z',
          status: 'ready',
          summary: 'Overall health status is good with minor recommendations for lifestyle improvements.'
        },
        {
          id: '2',
          title: 'Case Report: Chronic Headaches',
          type: 'case_summary',
          generatedAt: '2024-11-28T14:30:00Z',
          caseId: '123',
          caseName: 'Chronic Headaches Investigation',
          status: 'ready',
          summary: 'Detailed analysis of chronic headache patterns with treatment recommendations.'
        },
        {
          id: '3',
          title: 'Consultation History Report',
          type: 'consultation_history',
          generatedAt: '2024-11-25T09:15:00Z',
          status: 'ready',
          summary: 'Summary of all consultations from the past 3 months.'
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (type: string) => {
    setGeneratingReport(true);
    try {
      // TODO: Replace with actual API endpoint
      // const response = await api.post('/reports/generate', { type });
      toast.success('Report generation started. This may take a few moments.');
      
      // Simulate report generation
      setTimeout(() => {
        fetchReports();
      }, 3000);
    } catch (error) {
      console.error('Failed to generate report:', error);
      toast.error('Failed to generate report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const downloadReport = async (reportId: string, title: string) => {
    try {
      // TODO: Replace with actual download logic
      toast.success(`Downloading ${title}...`);
    } catch (error) {
      console.error('Failed to download report:', error);
      toast.error('Failed to download report');
    }
  };

  const filteredReports = reports.filter(report => {
    const matchesSearch = report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         report.caseName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         report.summary?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = filterType === 'all' || report.type === filterType;
    
    let matchesDate = true;
    if (dateRange.start && dateRange.end) {
      const reportDate = new Date(report.generatedAt);
      const startDate = new Date(dateRange.start);
      const endDate = new Date(dateRange.end);
      matchesDate = reportDate >= startDate && reportDate <= endDate;
    }
    
    return matchesSearch && matchesType && matchesDate;
  });

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case 'case_summary':
        return <DocumentTextIcon className="h-5 w-5" />;
      case 'health_overview':
        return <ChartBarIcon className="h-5 w-5" />;
      case 'consultation_history':
        return <CalendarIcon className="h-5 w-5" />;
      case 'medical_imaging':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
          </svg>
        );
      default:
        return <DocumentTextIcon className="h-5 w-5" />;
    }
  };

  const getReportTypeColor = (type: string) => {
    switch (type) {
      case 'case_summary':
        return 'bg-blue-100 text-blue-600';
      case 'health_overview':
        return 'bg-green-100 text-green-600';
      case 'consultation_history':
        return 'bg-purple-100 text-purple-600';
      case 'medical_imaging':
        return 'bg-indigo-100 text-indigo-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'text-green-600 bg-green-100';
      case 'generating':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
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
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Medical Reports</h1>
            <p className="text-gray-600 mt-2">
              View and generate comprehensive medical reports and summaries.
            </p>
          </div>
          <div className="relative">
            <button
              onClick={() => setGeneratingReport(true)}
              disabled={generatingReport}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              {generatingReport ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </div>
      </div>

      {/* Report Generation Options */}
      {generatingReport && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Generate New Report</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => generateReport('case_summary')}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors"
            >
              <DocumentTextIcon className="h-8 w-8 text-blue-600 mx-auto mb-2" />
              <h4 className="font-medium text-gray-900">Case Summary</h4>
              <p className="text-sm text-gray-600 mt-1">
                Detailed report for a specific medical case
              </p>
            </button>
            
            <button
              onClick={() => generateReport('health_overview')}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-green-500 transition-colors"
            >
              <ChartBarIcon className="h-8 w-8 text-green-600 mx-auto mb-2" />
              <h4 className="font-medium text-gray-900">Health Overview</h4>
              <p className="text-sm text-gray-600 mt-1">
                Comprehensive health status summary
              </p>
            </button>
            
            <button
              onClick={() => generateReport('consultation_history')}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-purple-500 transition-colors"
            >
              <CalendarIcon className="h-8 w-8 text-purple-600 mx-auto mb-2" />
              <h4 className="font-medium text-gray-900">Consultation History</h4>
              <p className="text-sm text-gray-600 mt-1">
                History of all medical consultations
              </p>
            </button>
          </div>
          <button
            onClick={() => setGeneratingReport(false)}
            className="mt-4 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            <option value="case_summary">Case Summary</option>
            <option value="health_overview">Health Overview</option>
            <option value="consultation_history">Consultation History</option>
            <option value="lab_results">Lab Results</option>
            <option value="medical_imaging">Medical Imaging</option>
          </select>

          {/* Date Range */}
          <div className="flex items-center space-x-2">
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {filteredReports.length > 0 ? (
          filteredReports.map((report) => (
            <div
              key={report.id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-lg ${getReportTypeColor(report.type)}`}>
                      {getReportTypeIcon(report.type)}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {report.title}
                      </h3>
                      <div className="mt-1 text-sm text-gray-600">
                        <span>Generated on {new Date(report.generatedAt).toLocaleDateString()}</span>
                        {report.caseName && (
                          <span className="ml-4">
                            Case: <button
                              onClick={() => navigate(`/consultation/${report.caseId}`)}
                              className="text-blue-600 hover:text-blue-700"
                            >
                              {report.caseName}
                            </button>
                          </span>
                        )}
                      </div>
                      {report.summary && (
                        <p className="mt-2 text-sm text-gray-700">
                          {report.summary}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(report.status)}`}>
                      {report.status}
                    </span>
                    
                    {report.status === 'ready' && (
                      <>
                        <button
                          onClick={() => navigate(`/reports/${report.id}`)}
                          className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
                          title="View Report"
                        >
                          <EyeIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => downloadReport(report.id, report.title)}
                          className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
                          title="Download Report"
                        >
                          <ArrowDownTrayIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No reports found</h3>
            <p className="text-gray-600 mb-4">
              {searchTerm || filterType !== 'all' 
                ? 'Try adjusting your search or filters' 
                : 'Generate your first medical report to get started'}
            </p>
            {!searchTerm && filterType === 'all' && (
              <button
                onClick={() => setGeneratingReport(true)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Generate Report
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;