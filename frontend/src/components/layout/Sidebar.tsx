import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import {
  Home,
  Users,
  UserPlus,
  FileText,
  BarChart3,
  Settings,
  Stethoscope,
  Activity,
  Pill,
  ClipboardList,
  Heart,
  Mic
} from 'lucide-react';

interface SidebarProps {
  onNavigate?: () => void;
}

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  roles?: string[];
}

export const Sidebar: React.FC<SidebarProps> = ({ onNavigate }) => {
  const { user } = useAuthStore();

  const navItems: NavItem[] = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: <Home className="h-5 w-5" />,
    },
    {
      name: 'My Cases',
      path: '/cases',
      icon: <FileText className="h-5 w-5" />,
    },
    {
      name: 'New Case',
      path: '/cases/new',
      icon: <UserPlus className="h-5 w-5" />,
    },
    {
      name: 'Collaboration Rooms',
      path: '/rooms',
      icon: <Users className="h-5 w-5" />,
    },
    {
      name: 'Medical Imaging',
      path: '/imaging',
      icon: <Activity className="h-5 w-5" />,
    },
    {
      name: 'Voice Consultation',
      path: '/voice',
      icon: <Pill className="h-5 w-5" />,
    },
    {
      name: 'Voice AI (New)',
      path: '/voice-new',
      icon: <Mic className="h-5 w-5" />,
    },
    {
      name: 'Gemini Live',
      path: '/voice-live',
      icon: <Stethoscope className="h-5 w-5" />,
    },
    {
      name: 'Reports',
      path: '/reports',
      icon: <ClipboardList className="h-5 w-5" />,
    },
    {
      name: 'Analytics',
      path: '/analytics',
      icon: <BarChart3 className="h-5 w-5" />,
    },
    {
      name: 'Settings',
      path: '/settings',
      icon: <Settings className="h-5 w-5" />,
    },
  ];

  // Filter nav items based on user role
  const filteredNavItems = navItems.filter(item => {
    if (!item.roles) return true;
    return item.roles.includes(user?.role || '');
  });

  return (
    <div className="flex flex-col h-full bg-white shadow-lg">
      {/* Logo/Brand */}
      <div className="flex items-center justify-center h-16 px-4 bg-indigo-600">
        <div className="flex items-center space-x-2">
          <Heart className="h-8 w-8 text-white" />
          <span className="text-xl font-bold text-white">Medical AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto">
        <div className="px-3 py-4">
          <ul className="space-y-1">
            {filteredNavItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${
                      isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  <span className="mr-3">{item.icon}</span>
                  {item.name}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* User Info */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="h-10 w-10 rounded-full bg-indigo-600 flex items-center justify-center">
              <span className="text-white font-medium">
                {user?.username?.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>
          <div className="ml-3">
            <p className="text-sm font-medium text-gray-700">{user?.username}</p>
            <p className="text-xs text-gray-500">{user?.role}</p>
          </div>
        </div>
      </div>
    </div>
  );
};