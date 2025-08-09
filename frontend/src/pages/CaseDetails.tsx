import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeftIcon, 
  ChatBubbleLeftIcon, 
  CalendarIcon, 
  ExclamationTriangleIcon,
  ClockIcon,
  UserIcon,
  HeartIcon,
  BeakerIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { getCaseById } from '../services/caseService';
import toast from 'react-hot-toast';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const CaseDetails: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCase = async () => {
      if (!caseId) return;
      
      try {
        const data = await getCaseById(caseId);
        setCaseData(data);
      } catch (error) {
        console.error('Failed to fetch case:', error);
        toast.error('Failed to load case details');
        navigate('/cases');
      } finally {
        setLoading(false);
      }
    };

    fetchCase();
  }, [caseId, navigate]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!caseData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Case not found</p>
        <Link to="/cases" className="text-blue-600 hover:underline mt-4 inline-block">
          Back to Cases
        </Link>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Invalid Date';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
      case 'emergency':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => navigate('/cases')}
            className="flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back to Cases
          </button>
          <button
            onClick={() => navigate(`/consultation/${caseId}`)}
            className="btn-primary flex items-center"
          >
            <ChatBubbleLeftIcon className="h-5 w-5 mr-2" />
            Continue Consultation
          </button>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {caseData.title || caseData.chief_complaint || 'Medical Case'}
        </h1>
        
        <div className="flex flex-wrap gap-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(caseData.status)}`}>
            {caseData.status}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(caseData.priority)}`}>
            {caseData.priority} Priority
          </span>
        </div>
      </div>

      {/* Case Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Chief Complaint */}
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 mr-2 text-gray-500" />
              Chief Complaint
            </h2>
            <p className="text-gray-700">{caseData.chief_complaint || 'Not specified'}</p>
          </div>

          {/* Symptoms */}
          {caseData.symptoms && caseData.symptoms.length > 0 && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <HeartIcon className="h-5 w-5 mr-2 text-gray-500" />
                Symptoms
              </h2>
              <div className="flex flex-wrap gap-2">
                {caseData.symptoms.map((symptom: string, index: number) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    {symptom}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          {caseData.description && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <DocumentTextIcon className="h-5 w-5 mr-2 text-gray-500" />
                Description
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">{caseData.description}</p>
            </div>
          )}
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Timeline */}
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <ClockIcon className="h-5 w-5 mr-2 text-gray-500" />
              Timeline
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Created:</span>
                <span className="text-gray-900">{formatDate(caseData.created_at)}</span>
              </div>
              {caseData.updated_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Updated:</span>
                  <span className="text-gray-900">{formatDate(caseData.updated_at)}</span>
                </div>
              )}
              {caseData.closed_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Closed:</span>
                  <span className="text-gray-900">{formatDate(caseData.closed_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Medical History */}
          {caseData.medical_history && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <UserIcon className="h-5 w-5 mr-2 text-gray-500" />
                Past Medical History
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">{caseData.medical_history}</p>
            </div>
          )}

          {/* Current Medications */}
          {caseData.medications && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <BeakerIcon className="h-5 w-5 mr-2 text-gray-500" />
                Current Medications
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">{caseData.medications}</p>
            </div>
          )}

          {/* Allergies */}
          {caseData.allergies && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <ExclamationTriangleIcon className="h-5 w-5 mr-2 text-red-500" />
                Allergies
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">{caseData.allergies}</p>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => navigate(`/consultation/${caseId}`)}
            className="btn-primary"
          >
            Continue Consultation
          </button>
          <button
            onClick={() => navigate('/cases')}
            className="btn-secondary"
          >
            Back to Cases
          </button>
        </div>
      </div>
    </div>
  );
};

export default CaseDetails;