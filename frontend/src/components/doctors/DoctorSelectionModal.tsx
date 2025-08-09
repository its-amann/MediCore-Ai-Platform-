import React, { useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  XMarkIcon,
  HeartIcon,
  UserIcon,
  BeakerIcon,
  StarIcon,
  ClockIcon,
  CheckCircleIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid, StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import toast from 'react-hot-toast';
import api from '../../api/axios';

interface Doctor {
  doctor_id: string;
  name: string;
  specialty: 'CARDIOLOGIST' | 'BP_SPECIALIST' | 'GENERAL_CONSULTANT';
  description: string;
  avatar_url?: string;
  average_rating: number;
  consultation_count: number;
  specialization_areas: string[];
  years_of_experience: number;
  languages: string[];
  availability_status: 'available' | 'busy' | 'offline';
  response_time_avg: number; // in seconds
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface DoctorSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDoctorSelect: (doctor: Doctor) => void;
  caseId?: string;
  preferredSpecialty?: string;
}

const DoctorSelectionModal: React.FC<DoctorSelectionModalProps> = ({
  isOpen,
  onClose,
  onDoctorSelect,
  caseId,
  preferredSpecialty
}) => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>(preferredSpecialty || 'all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchDoctors();
    }
  }, [isOpen, selectedSpecialty]);

  const fetchDoctors = async () => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams();
      if (selectedSpecialty !== 'all') {
        params.append('specialty', selectedSpecialty);
      }
      params.append('is_active', 'true');

      const response = await api.get(`/doctors/?${params.toString()}`);
      setDoctors(response.data || []);
    } catch (error) {
      console.error('Failed to fetch doctors:', error);
      toast.error('Failed to load available doctors');
      setDoctors([]);
    } finally {
      setLoading(false);
    }
  };

  const getSpecialtyIcon = (specialty: string) => {
    switch (specialty) {
      case 'CARDIOLOGIST':
        return HeartIcon;
      case 'BP_SPECIALIST':
        return BeakerIcon;
      case 'GENERAL_CONSULTANT':
        return UserIcon;
      default:
        return UserIcon;
    }
  };

  const getSpecialtyColor = (specialty: string) => {
    switch (specialty) {
      case 'CARDIOLOGIST':
        return 'text-red-600 bg-red-100';
      case 'BP_SPECIALIST':
        return 'text-blue-600 bg-blue-100';
      case 'GENERAL_CONSULTANT':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getAvailabilityStatus = (status: string) => {
    switch (status) {
      case 'available':
        return { color: 'text-green-600', label: 'Available', dot: 'bg-green-500' };
      case 'busy':
        return { color: 'text-yellow-600', label: 'Busy', dot: 'bg-yellow-500' };
      case 'offline':
        return { color: 'text-gray-600', label: 'Offline', dot: 'bg-gray-500' };
      default:
        return { color: 'text-gray-600', label: 'Unknown', dot: 'bg-gray-500' };
    }
  };

  const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const formatSpecialty = (specialty: string) => {
    return specialty.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join(' ');
  };

  const filteredDoctors = doctors.filter(doctor => {
    const matchesSearch = doctor.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         doctor.specialization_areas.some(area => 
                           area.toLowerCase().includes(searchQuery.toLowerCase())
                         );
    return matchesSearch;
  });

  const handleDoctorSelect = (doctor: Doctor) => {
    onDoctorSelect(doctor);
    onClose();
    toast.success(`Selected Dr. ${doctor.name} for consultation`);
  };

  const renderStars = (rating: number) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 !== 0;

    for (let i = 0; i < fullStars; i++) {
      stars.push(
        <StarIconSolid key={`full-${i}`} className="h-4 w-4 text-yellow-400" />
      );
    }

    if (hasHalfStar) {
      stars.push(
        <div key="half" className="relative">
          <StarIcon className="h-4 w-4 text-yellow-400" />
          <StarIconSolid className="h-4 w-4 text-yellow-400 absolute top-0 left-0 overflow-hidden" style={{ width: '50%' }} />
        </div>
      );
    }

    const emptyStars = 5 - Math.ceil(rating);
    for (let i = 0; i < emptyStars; i++) {
      stars.push(
        <StarIcon key={`empty-${i}`} className="h-4 w-4 text-gray-300" />
      );
    }

    return stars;
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-white text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900">
                      Select an AI Doctor
                    </Dialog.Title>
                    <p className="text-sm text-gray-600 mt-1">
                      Choose a specialist for your medical consultation
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="p-6">
                  {/* Filters */}
                  <div className="flex items-center space-x-4 mb-6">
                    {/* Search */}
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Search doctors by name or specialization..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    {/* Specialty Filter */}
                    <select
                      value={selectedSpecialty}
                      onChange={(e) => setSelectedSpecialty(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="all">All Specialties</option>
                      <option value="CARDIOLOGIST">Cardiologist</option>
                      <option value="BP_SPECIALIST">BP Specialist</option>
                      <option value="GENERAL_CONSULTANT">General Consultant</option>
                    </select>
                  </div>

                  {/* Doctors List */}
                  {loading ? (
                    <div className="flex items-center justify-center h-48">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                  ) : filteredDoctors.length === 0 ? (
                    <div className="text-center py-12">
                      <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
                      <h3 className="mt-2 text-sm font-medium text-gray-900">No doctors found</h3>
                      <p className="mt-1 text-sm text-gray-500">
                        Try adjusting your search criteria
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
                      {filteredDoctors.map((doctor) => {
                        const SpecialtyIcon = getSpecialtyIcon(doctor.specialty);
                        const availability = getAvailabilityStatus(doctor.availability_status);
                        
                        return (
                          <div
                            key={doctor.doctor_id}
                            className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                            onClick={() => handleDoctorSelect(doctor)}
                          >
                            {/* Header */}
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex items-center space-x-3">
                                {/* Avatar */}
                                <div className="flex-shrink-0">
                                  {doctor.avatar_url ? (
                                    <img
                                      src={doctor.avatar_url}
                                      alt={doctor.name}
                                      className="h-12 w-12 rounded-full object-cover"
                                    />
                                  ) : (
                                    <div className="h-12 w-12 bg-gray-200 rounded-full flex items-center justify-center">
                                      <UserIcon className="h-6 w-6 text-gray-500" />
                                    </div>
                                  )}
                                </div>

                                {/* Basic Info */}
                                <div>
                                  <h3 className="text-lg font-semibold text-gray-900">
                                    Dr. {doctor.name}
                                  </h3>
                                  <div className="flex items-center space-x-2">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSpecialtyColor(doctor.specialty)}`}>
                                      <SpecialtyIcon className="h-3 w-3 mr-1" />
                                      {formatSpecialty(doctor.specialty)}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Availability Status */}
                              <div className="flex items-center space-x-1">
                                <div className={`h-2 w-2 rounded-full ${availability.dot}`}></div>
                                <span className={`text-xs font-medium ${availability.color}`}>
                                  {availability.label}
                                </span>
                              </div>
                            </div>

                            {/* Description */}
                            <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                              {doctor.description}
                            </p>

                            {/* Specialization Areas */}
                            <div className="mb-3">
                              <p className="text-xs font-medium text-gray-700 mb-1">Specializations:</p>
                              <div className="flex flex-wrap gap-1">
                                {doctor.specialization_areas.slice(0, 3).map((area, index) => (
                                  <span
                                    key={index}
                                    className="inline-flex items-center px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                                  >
                                    {area}
                                  </span>
                                ))}
                                {doctor.specialization_areas.length > 3 && (
                                  <span className="text-xs text-gray-500">
                                    +{doctor.specialization_areas.length - 3} more
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-4 text-center">
                              {/* Rating */}
                              <div>
                                <div className="flex items-center justify-center space-x-1 mb-1">
                                  {renderStars(doctor.average_rating)}
                                </div>
                                <p className="text-xs text-gray-600">
                                  {doctor.average_rating.toFixed(1)} Rating
                                </p>
                              </div>

                              {/* Consultations */}
                              <div>
                                <p className="text-lg font-semibold text-gray-900">
                                  {doctor.consultation_count}
                                </p>
                                <p className="text-xs text-gray-600">Consultations</p>
                              </div>

                              {/* Response Time */}
                              <div>
                                <p className="text-lg font-semibold text-gray-900">
                                  {formatResponseTime(doctor.response_time_avg)}
                                </p>
                                <p className="text-xs text-gray-600">Avg Response</p>
                              </div>
                            </div>

                            {/* Languages */}
                            <div className="mt-3 pt-3 border-t border-gray-100">
                              <div className="flex items-center justify-between text-xs text-gray-600">
                                <span>Languages: {doctor.languages.join(', ')}</span>
                                <span>{doctor.years_of_experience} years exp.</span>
                              </div>
                            </div>

                            {/* Select Button Overlay */}
                            <div className="mt-3">
                              <button className="w-full btn-primary text-sm py-2">
                                Select Dr. {doctor.name}
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                  <div className="flex justify-end">
                    <button
                      onClick={onClose}
                      className="btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

export default DoctorSelectionModal;