import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import api from '../api/axios';
import { FormInput, FormTextArea, FormSelect } from '../components/ui/FormField';
import LoadingSpinner from '../components/ui/LoadingSpinner';

interface CaseFormData {
  chief_complaint: string;
  symptoms: string[];
  description: string;
  priority: string;
  past_medical_history: string;
  current_medications: string;
  allergies: string;
}

interface FormErrors {
  chief_complaint?: string;
  symptoms?: string;
  description?: string;
  priority?: string;
  past_medical_history?: string;
  current_medications?: string;
  allergies?: string;
}

const NewCase: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [currentSymptom, setCurrentSymptom] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [formData, setFormData] = useState<CaseFormData>({
    chief_complaint: '',
    symptoms: [],
    description: '',
    priority: 'medium',
    past_medical_history: '',
    current_medications: '',
    allergies: ''
  });

  const commonSymptoms = [
    'Chest pain',
    'Shortness of breath',
    'Headache',
    'Fever',
    'Cough',
    'Fatigue',
    'Nausea',
    'Dizziness',
    'Abdominal pain',
    'Back pain',
    'Joint pain',
    'Skin rash'
  ];

  const validateField = (name: string, value: any): string | undefined => {
    switch (name) {
      case 'chief_complaint':
        if (!value || value.trim().length < 3) {
          return 'Chief complaint must be at least 3 characters long';
        }
        if (value.length > 200) {
          return 'Chief complaint must be less than 200 characters';
        }
        break;
      case 'symptoms':
        if (!value || value.length === 0) {
          return 'Please add at least one symptom';
        }
        break;
      case 'description':
        if (value && value.length > 1000) {
          return 'Description must be less than 1000 characters';
        }
        break;
      case 'past_medical_history':
        if (value && value.length > 500) {
          return 'Medical history must be less than 500 characters';
        }
        break;
      case 'current_medications':
        if (value && value.length > 300) {
          return 'Medications must be less than 300 characters';
        }
        break;
      case 'allergies':
        if (value && value.length > 200) {
          return 'Allergies must be less than 200 characters';
        }
        break;
    }
    return undefined;
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Real-time validation
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors(prev => ({ ...prev, [name]: error }));
    }
  };

  const handleFieldBlur = (fieldName: string) => {
    setTouched(prev => ({ ...prev, [fieldName]: true }));
    const value = fieldName === 'symptoms' ? formData.symptoms : formData[fieldName as keyof CaseFormData];
    const error = validateField(fieldName, value);
    setErrors(prev => ({ ...prev, [fieldName]: error }));
  };

  const addSymptom = (symptom: string) => {
    if (symptom && !formData.symptoms.includes(symptom)) {
      const newSymptoms = [...formData.symptoms, symptom];
      setFormData(prev => ({
        ...prev,
        symptoms: newSymptoms
      }));
      setCurrentSymptom('');
      
      // Clear symptoms error if we now have symptoms
      if (errors.symptoms) {
        setErrors(prev => ({ ...prev, symptoms: undefined }));
      }
    }
  };

  const removeSymptom = (symptom: string) => {
    const newSymptoms = formData.symptoms.filter(s => s !== symptom);
    setFormData(prev => ({
      ...prev,
      symptoms: newSymptoms
    }));
    
    // Re-validate symptoms if field was touched
    if (touched.symptoms) {
      const error = validateField('symptoms', newSymptoms);
      setErrors(prev => ({ ...prev, symptoms: error }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    let isValid = true;

    // Validate all fields
    Object.keys(formData).forEach(key => {
      const value = key === 'symptoms' ? formData.symptoms : formData[key as keyof CaseFormData];
      const error = validateField(key, value);
      if (error) {
        newErrors[key as keyof FormErrors] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);
    setTouched({
      chief_complaint: true,
      symptoms: true,
      description: true,
      priority: true,
      past_medical_history: true,
      current_medications: true,
      allergies: true
    });

    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error('Please fix the errors below before submitting.');
      return;
    }

    setLoading(true);
    try {
      const caseData = {
        title: formData.chief_complaint.substring(0, 200),
        description: formData.description || `Chief complaint: ${formData.chief_complaint}. Symptoms: ${formData.symptoms.join(', ')}`,
        chief_complaint: formData.chief_complaint,
        symptoms: formData.symptoms,
        priority: formData.priority,
        past_medical_history: formData.past_medical_history,
        current_medications: formData.current_medications,
        allergies: formData.allergies
      };

      const response = await api.post('/cases/', caseData);
      const caseId = response.data.case_id;
      
      toast.success('Medical case created successfully! Starting consultation...');
      
      // Navigate to consultation page
      navigate(`/consultation/${caseId}`);
    } catch (error) {
      console.error('Failed to create case:', error);
      toast.error('Failed to create case. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityInfo = (priority: string) => {
    switch (priority) {
      case 'emergency':
        return {
          icon: <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />,
          text: 'Requires immediate attention',
          bgColor: 'bg-red-50 border-red-200'
        };
      case 'high':
        return {
          icon: <ExclamationTriangleIcon className="h-5 w-5 text-orange-600" />,
          text: 'Should be addressed soon',
          bgColor: 'bg-orange-50 border-orange-200'
        };
      case 'medium':
        return {
          icon: <InformationCircleIcon className="h-5 w-5 text-yellow-600" />,
          text: 'Moderate concern',
          bgColor: 'bg-yellow-50 border-yellow-200'
        };
      default:
        return {
          icon: <CheckCircleIcon className="h-5 w-5 text-green-600" />,
          text: 'Can be scheduled normally',
          bgColor: 'bg-green-50 border-green-200'
        };
    }
  };

  const priorityInfo = getPriorityInfo(formData.priority);

  if (loading) {
    return <LoadingSpinner overlay text="Creating your medical case..." />;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <button
          onClick={() => navigate('/cases')}
          className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to Cases
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-lg">
        <div className="px-4 py-5 sm:p-6 lg:p-8">
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Create New Medical Case</h1>
            <p className="mt-2 text-gray-600">Provide details about your health concern to get personalized AI consultation.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Chief Complaint */}
            <FormInput
              label="Chief Complaint"
              name="chief_complaint"
              value={formData.chief_complaint}
              onChange={handleInputChange}
              onBlur={() => handleFieldBlur('chief_complaint')}
              placeholder="e.g., Persistent chest pain"
              error={touched.chief_complaint ? errors.chief_complaint : undefined}
              required
              maxLength={200}
              hint="Briefly describe your main health concern"
            />

            {/* Symptoms */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Symptoms <span className="text-red-500">*</span>
              </label>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={currentSymptom}
                    onChange={(e) => setCurrentSymptom(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addSymptom(currentSymptom);
                      }
                    }}
                    placeholder="Type a symptom and press Enter"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
                    onBlur={() => handleFieldBlur('symptoms')}
                  />
                  <button
                    type="button"
                    onClick={() => addSymptom(currentSymptom)}
                    disabled={!currentSymptom.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                  >
                    Add
                  </button>
                </div>

                {/* Common Symptoms */}
                <div>
                  <p className="text-xs text-gray-600 mb-2">Common symptoms (click to add):</p>
                  <div className="flex flex-wrap gap-2">
                    {commonSymptoms.map((symptom) => (
                      <button
                        key={symptom}
                        type="button"
                        onClick={() => addSymptom(symptom)}
                        disabled={formData.symptoms.includes(symptom)}
                        className={`px-2 sm:px-3 py-1 text-xs rounded-full transition-colors ${
                          formData.symptoms.includes(symptom)
                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            : 'bg-gray-100 text-gray-700 hover:bg-blue-100 hover:text-blue-700'
                        }`}
                      >
                        {symptom}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Selected Symptoms */}
                {formData.symptoms.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-700">Selected symptoms:</p>
                    <div className="flex flex-wrap gap-2">
                      {formData.symptoms.map((symptom) => (
                        <span
                          key={symptom}
                          className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                        >
                          {symptom}
                          <button
                            type="button"
                            onClick={() => removeSymptom(symptom)}
                            className="ml-2 text-blue-600 hover:text-blue-800 focus:outline-none"
                            aria-label={`Remove ${symptom}`}
                          >
                            <XMarkIcon className="h-4 w-4" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {touched.symptoms && errors.symptoms && (
                  <p className="text-sm text-red-600 flex items-center">
                    <ExclamationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
                    {errors.symptoms}
                  </p>
                )}
              </div>
            </div>

            {/* Description */}
            <FormTextArea
              label="Detailed Description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              onBlur={() => handleFieldBlur('description')}
              rows={4}
              placeholder="Provide more details about your condition, when it started, what makes it better or worse..."
              error={touched.description ? errors.description : undefined}
              hint="Optional: Additional context about your symptoms and condition"
              maxLength={1000}
            />

            {/* Priority */}
            <div>
              <FormSelect
                label="Priority Level"
                name="priority"
                value={formData.priority}
                onChange={handleInputChange}
                onBlur={() => handleFieldBlur('priority')}
                error={touched.priority ? errors.priority : undefined}
              >
                <option value="low">Low - Routine check</option>
                <option value="medium">Medium - Moderate concern</option>
                <option value="high">High - Needs attention soon</option>
                <option value="emergency">Emergency - Immediate attention needed</option>
              </FormSelect>
              
              <div className={`mt-3 p-3 rounded-md border ${priorityInfo.bgColor}`}>
                <div className="flex items-center">
                  {priorityInfo.icon}
                  <span className="ml-2 text-sm">{priorityInfo.text}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Medical History */}
              <FormTextArea
                label="Past Medical History"
                name="past_medical_history"
                value={formData.past_medical_history}
                onChange={handleInputChange}
                onBlur={() => handleFieldBlur('past_medical_history')}
                rows={3}
                placeholder="Previous conditions, surgeries, hospitalizations..."
                error={touched.past_medical_history ? errors.past_medical_history : undefined}
                hint="Optional: Help us understand your medical background"
                maxLength={500}
              />

              {/* Current Medications */}
              <FormTextArea
                label="Current Medications"
                name="current_medications"
                value={formData.current_medications}
                onChange={handleInputChange}
                onBlur={() => handleFieldBlur('current_medications')}
                rows={3}
                placeholder="List all medications you're currently taking..."
                error={touched.current_medications ? errors.current_medications : undefined}
                hint="Optional: Include dosages if known"
                maxLength={300}
              />
            </div>

            {/* Allergies */}
            <FormInput
              label="Allergies"
              name="allergies"
              value={formData.allergies}
              onChange={handleInputChange}
              onBlur={() => handleFieldBlur('allergies')}
              placeholder="Drug allergies, food allergies, etc..."
              error={touched.allergies ? errors.allergies : undefined}
              hint="Optional: List any known allergies or adverse reactions"
              maxLength={200}
            />

            {/* Submit Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-end space-y-2 sm:space-y-0 sm:space-x-4 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={() => navigate('/cases')}
                className="w-full sm:w-auto px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center justify-center"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creating...
                  </>
                ) : (
                  'Create Case & Start Consultation'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <InformationCircleIcon className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-900">What happens next?</h3>
            <p className="mt-1 text-sm text-blue-700">
              After creating your case, you'll be connected with an AI medical specialist who can help analyze your symptoms
              and provide guidance. You can share additional information, upload medical images, or have a voice consultation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewCase;