import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  UserGroupIcon,
  PlusIcon,
  ArrowRightIcon,
  LockClosedIcon,
  GlobeAltIcon,
  MicrophoneIcon,
  VideoCameraIcon,
  ClockIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import collaborationService, { Room, RoomType, RoomStatus } from '../services/collaborationService';

const RoomList: React.FC = () => {
  const navigate = useNavigate();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<RoomType | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<RoomStatus | 'all'>(RoomStatus.ACTIVE);
  const [currentPage, setCurrentPage] = useState(1);
  const roomsPerPage = 12;

  useEffect(() => {
    fetchRooms();
  }, [filterType, filterStatus]);

  const fetchRooms = async () => {
    try {
      const filters: any = {};
      if (filterType !== 'all') filters.room_type = filterType;
      if (filterStatus !== 'all') filters.status = filterStatus;

      const response = await collaborationService.getRooms(filters);
      console.log('Rooms API response:', response); // Debug log
      
      // Handle both array response and object with rooms property
      let roomsData = [];
      if (Array.isArray(response)) {
        roomsData = response;
      } else if (response && typeof response === 'object') {
        // Handle the format from the original rooms router
        roomsData = response.rooms || [];
      }
      
      // Ensure roomsData is always an array
      if (!Array.isArray(roomsData)) {
        console.error('Unexpected rooms data format:', roomsData);
        roomsData = [];
      }
      
      // Deduplicate rooms by room_id and sort by creation date
      const uniqueRooms = Array.from(
        new Map(roomsData.map(room => [room.room_id, room])).values()
      ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      
      setRooms(uniqueRooms);
    } catch (error: any) {
      console.error('Failed to fetch rooms:', error);
      toast.error(error.response?.data?.detail || 'Failed to fetch rooms');
      setRooms([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const filteredRooms = (rooms || []).filter(room =>
    room.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    room.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Calculate pagination
  const totalPages = Math.ceil(filteredRooms.length / roomsPerPage);
  const startIndex = (currentPage - 1) * roomsPerPage;
  const endIndex = startIndex + roomsPerPage;
  const currentRooms = filteredRooms.slice(startIndex, endIndex);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterType, filterStatus]);

  const getRoomTypeIcon = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return <VideoCameraIcon className="h-5 w-5" />;
      case RoomType.CASE_DISCUSSION:
      default:
        return <UserGroupIcon className="h-5 w-5" />;
    }
  };

  const getRoomTypeColor = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return 'bg-purple-100 text-purple-600';
      case RoomType.CASE_DISCUSSION:
      default:
        return 'bg-green-100 text-green-600';
    }
  };

  const getStatusColor = (status: RoomStatus) => {
    switch (status) {
      case RoomStatus.ACTIVE:
        return 'text-green-600 bg-green-100';
      case RoomStatus.INACTIVE:
        return 'text-yellow-600 bg-yellow-100';
      case RoomStatus.ARCHIVED:
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getRoomTypeLabel = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return 'Teaching Session';
      case RoomType.CASE_DISCUSSION:
        return 'Case Discussion';
      default:
        return type;
    }
  };

  const handleJoinRoom = async (roomId: string, isPrivate: boolean) => {
    if (isPrivate) {
      // Show password prompt
      const password = window.prompt('Enter room password:');
      if (!password) return;

      try {
        await collaborationService.joinRoom(roomId, password);
        navigate(`/rooms/${roomId}`);
      } catch (error) {
        console.error('Failed to join room:', error);
      }
    } else {
      try {
        await collaborationService.joinRoom(roomId);
        navigate(`/rooms/${roomId}`);
      } catch (error) {
        console.error('Failed to join room:', error);
      }
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
            <h1 className="text-2xl font-bold text-gray-900">Collaboration Rooms</h1>
            <p className="text-gray-600 mt-2">
              Join real-time discussions with medical professionals and other patients.
            </p>
          </div>
          <button
            onClick={() => navigate('/rooms/new')}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Room
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search rooms..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as RoomType | 'all')}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            <option value={RoomType.CASE_DISCUSSION}>Case Discussion</option>
            <option value={RoomType.TEACHING}>Teaching Session</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as RoomStatus | 'all')}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value={RoomStatus.ACTIVE}>Active</option>
            <option value={RoomStatus.INACTIVE}>Inactive</option>
            <option value={RoomStatus.ARCHIVED}>Archived</option>
            <option value="all">All Status</option>
          </select>
        </div>
      </div>

      {/* Room Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {currentRooms.length > 0 ? (
          currentRooms.map((room) => (
            <div
              key={room.room_id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleJoinRoom(room.room_id, room.is_private)}
            >
              <div className="p-6">
                {/* Room Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg ${getRoomTypeColor(room.room_type)}`}>
                      {getRoomTypeIcon(room.room_type)}
                    </div>
                    <div className="ml-3">
                      <h3 className="font-semibold text-gray-900">{room.name}</h3>
                      <p className="text-sm text-gray-600">
                        {getRoomTypeLabel(room.room_type)}
                      </p>
                    </div>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(room.status)}`}>
                    {room.status}
                  </span>
                </div>

                {/* Room Description */}
                <p className="text-sm text-gray-600 mb-4 line-clamp-2 min-h-[2.5rem]">
                  {room.description || 'No description available'}
                </p>

                {/* Room Info */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-500">
                    <UserGroupIcon className="h-4 w-4 mr-2" />
                    <span>{room.participant_count || 1}/{room.max_participants || 10} participants</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-500">
                    {room.is_private ? (
                      <>
                        <LockClosedIcon className="h-4 w-4 mr-2" />
                        <span>Private Room</span>
                      </>
                    ) : (
                      <>
                        <GlobeAltIcon className="h-4 w-4 mr-2" />
                        <span>Public Room</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center text-sm text-gray-500">
                    <ClockIcon className="h-4 w-4 mr-2" />
                    <span>Created {new Date(room.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Features */}
                <div className="flex items-center justify-between">
                  <div className="flex space-x-2">
                    {room.room_type === RoomType.TEACHING && (
                      <span className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-xs text-gray-600">
                        <VideoCameraIcon className="h-3 w-3 mr-1" />
                        Video
                      </span>
                    )}
                    {room.tags?.map((tag: string) => (
                      <span key={tag} className="inline-flex items-center px-2 py-1 rounded-md bg-blue-100 text-xs text-blue-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center py-12">
            <UserGroupIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No rooms found</h3>
            <p className="text-gray-600 mb-4">
              {searchTerm ? 'Try adjusting your search or filters' : 'Be the first to create a collaboration room!'}
            </p>
            <button
              onClick={() => navigate('/rooms/new')}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create Room
            </button>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {startIndex + 1} to {Math.min(endIndex, filteredRooms.length)} of {filteredRooms.length} rooms
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              
              {/* Page numbers */}
              <div className="flex space-x-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  
                  return pageNum > 0 && pageNum <= totalPages ? (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1 rounded-md transition-colors ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {pageNum}
                    </button>
                  ) : null;
                })}
              </div>
              
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoomList;