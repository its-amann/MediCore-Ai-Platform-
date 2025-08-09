import React from 'react';
import { motion } from 'framer-motion';
import { X, Check, CheckCheck, Trash2, RefreshCw, Bell, Users, MessageSquare, Video, Calendar, AlertCircle, ThumbsUp, ThumbsDown } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import collaborationService from '../services/collaborationService';
import { toast } from 'react-hot-toast';

interface Notification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  data: any;
  is_read: boolean;
  created_at: string;
  priority: 'urgent' | 'normal' | 'low';
}

interface NotificationPanelProps {
  notifications: Notification[];
  onClose: () => void;
  onMarkAsRead: (id: string) => void;
  onMarkAllAsRead: () => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({
  notifications,
  onClose,
  onMarkAsRead,
  onMarkAllAsRead,
  onDelete,
  onRefresh
}) => {
  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'JOIN_REQUEST':
      case 'JOIN_APPROVED':
      case 'JOIN_REJECTED':
      case 'PARTICIPANT_JOINED':
      case 'PARTICIPANT_LEFT':
        return <Users className="h-5 w-5" />;
      case 'ROOM_INVITE':
      case 'ROOM_DISABLED':
      case 'ROOM_CLOSING_SOON':
        return <Bell className="h-5 w-5" />;
      case 'NEW_MESSAGE':
      case 'MENTION':
      case 'AI_RESPONSE':
        return <MessageSquare className="h-5 w-5" />;
      case 'TEACHING_REMINDER':
        return <Calendar className="h-5 w-5" />;
      case 'ROOM_STARTED':
        return <Video className="h-5 w-5" />;
      default:
        return <Bell className="h-5 w-5" />;
    }
  };

  const getNotificationColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-red-600 bg-red-50';
      case 'normal':
        return 'text-blue-600 bg-blue-50';
      case 'low':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      onMarkAsRead(notification.id);
    }

    // Handle action based on notification type
    if (notification.data?.room_id && notification.notification_type !== 'JOIN_REQUEST') {
      // Navigate to room - you can implement this based on your routing
      window.location.href = `/rooms/${notification.data.room_id}`;
    }
  };

  const handleJoinRequest = async (notification: Notification, action: 'approve' | 'reject') => {
    try {
      const { room_id, request_id } = notification.data;
      await collaborationService.handleJoinRequest(room_id, request_id, action);
      toast.success(`Request ${action}d successfully`);
      onDelete(notification.id);
      onRefresh();
    } catch (error) {
      console.error(`Failed to ${action} join request:`, error);
      toast.error(`Failed to ${action} request`);
    }
  };

  const unreadCount = notifications?.filter(n => !n.is_read).length || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl z-50 max-h-[600px] flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">
          Notifications {unreadCount > 0 && <span className="text-sm text-gray-500">({unreadCount} unread)</span>}
        </h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={onRefresh}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          {unreadCount > 0 && (
            <button
              onClick={onMarkAllAsRead}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              title="Mark all as read"
            >
              <CheckCheck className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {!notifications || notifications.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Bell className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No notifications yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {notifications?.map((notification) => (
              <motion.div
                key={notification.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  !notification.is_read ? 'bg-blue-50' : ''
                }`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-full ${getNotificationColor(notification.priority)}`}>
                    {getNotificationIcon(notification.notification_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {notification.title}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {notification.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                    </p>
                    {/* Show approve/reject buttons for join requests */}
                    {notification.notification_type === 'JOIN_REQUEST' && notification.data?.request_id && (
                      <div className="flex items-center space-x-2 mt-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleJoinRequest(notification, 'approve');
                          }}
                          className="flex items-center px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                        >
                          <ThumbsUp className="h-3 w-3 mr-1" />
                          Approve
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleJoinRequest(notification, 'reject');
                          }}
                          className="flex items-center px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                        >
                          <ThumbsDown className="h-3 w-3 mr-1" />
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center space-x-1">
                    {!notification.is_read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onMarkAsRead(notification.id);
                        }}
                        className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                        title="Mark as read"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(notification.id);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {notification.priority === 'urgent' && (
                  <div className="flex items-center mt-2 text-xs text-red-600">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Urgent notification
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications && notifications.length > 0 && (
        <div className="p-4 border-t bg-gray-50">
          <button
            onClick={() => {
              // Navigate to notification settings
              window.location.href = '/settings/notifications';
            }}
            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            Notification Settings
          </button>
        </div>
      )}
    </motion.div>
  );
};

export default NotificationPanel;