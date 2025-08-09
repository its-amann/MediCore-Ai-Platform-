import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  IconButton,
  Avatar,
  Tabs,
  Tab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  InputAdornment,
  Badge,
  Tooltip,
  Menu,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { Grid } from '@mui/material';
import {
  Add as AddIcon,
  Settings as SettingsIcon,
  Group as GroupIcon,
  School as SchoolIcon,
  Search as SearchIcon,
  Lock as LockIcon,
  Public as PublicIcon,
  FilterList as FilterListIcon,
  Person as PersonIcon,
  CalendarToday as CalendarIcon,
  MoreVert as MoreVertIcon,
  Archive as ArchiveIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import collaborationService, { Room, RoomType, RoomStatus } from '../../services/collaborationService';
import RoomSettingsModal from './RoomSettingsModal';
import RoomDetailsModal from './RoomDetailsModal';

type ParticipationFilter = 'all' | 'created' | 'member' | 'pending';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`room-tabpanel-${index}`}
      aria-labelledby={`room-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

const CollaborationRooms: React.FC = () => {
  const navigate = useNavigate();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [tabValue, setTabValue] = useState(0);
  const [participationFilter, setParticipationFilter] = useState<ParticipationFilter>('all');
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedRoomForMenu, setSelectedRoomForMenu] = useState<Room | null>(null);
  const currentUserId = localStorage.getItem('userId'); // Assuming userId is stored in localStorage

  useEffect(() => {
    fetchRooms();
  }, []);

  const fetchRooms = async () => {
    try {
      setLoading(true);
      const response = await collaborationService.getRooms();
      
      // Handle both array response and object with rooms property
      let roomsData = [];
      if (Array.isArray(response)) {
        roomsData = response;
      } else if (response && typeof response === 'object') {
        roomsData = response.rooms || [];
      }
      
      setRooms(roomsData);
    } catch (error) {
      console.error('Failed to fetch rooms:', error);
      setRooms([]);
    } finally {
      setLoading(false);
    }
  };

  const getRoomTypeFromTab = (tab: number): RoomType | 'all' => {
    switch (tab) {
      case 0:
        return 'all';
      case 1:
        return RoomType.CASE_DISCUSSION;
      case 2:
        return RoomType.TEACHING;
      default:
        return 'all';
    }
  };

  const filteredRooms = useMemo(() => {
    let filtered = rooms;

    // Filter by room type based on tab
    const roomType = getRoomTypeFromTab(tabValue);
    if (roomType !== 'all') {
      filtered = filtered.filter(room => room.room_type === roomType);
    }

    // Filter by participation
    if (participationFilter !== 'all' && currentUserId) {
      switch (participationFilter) {
        case 'created':
          filtered = filtered.filter(room => room.host_id === currentUserId);
          break;
        case 'member':
          // This would require checking if user is in participants list
          // For now, we'll filter rooms where user is not the host
          filtered = filtered.filter(room => room.host_id !== currentUserId);
          break;
        case 'pending':
          // This would require checking pending join requests
          // Implementation depends on backend support
          break;
      }
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(room =>
        room.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        room.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        room.tags?.some((tag: string) => tag?.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Only show active rooms by default
    filtered = filtered.filter(room => room.status === RoomStatus.ACTIVE);

    return filtered;
  }, [rooms, tabValue, participationFilter, searchTerm, currentUserId]);

  const handleJoinRoom = async (room: Room) => {
    if (room.is_private) {
      // Show room details modal for private rooms
      setSelectedRoom(room);
      setDetailsModalOpen(true);
    } else {
      try {
        await collaborationService.joinRoom(room.room_id);
        navigate(`/rooms/${room.room_id}`);
      } catch (error) {
        console.error('Failed to join room:', error);
      }
    }
  };

  const handleRequestJoin = async (roomId: string, message?: string) => {
    try {
      await collaborationService.sendJoinRequest(roomId, message);
      toast.success('Join request sent successfully');
      setDetailsModalOpen(false);
    } catch (error) {
      console.error('Failed to send join request:', error);
    }
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, room: Room) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedRoomForMenu(room);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedRoomForMenu(null);
  };

  const handleSettingsClick = () => {
    if (selectedRoomForMenu) {
      setSelectedRoom(selectedRoomForMenu);
      setSettingsModalOpen(true);
    }
    handleMenuClose();
  };

  const handleArchiveRoom = async () => {
    if (selectedRoomForMenu) {
      try {
        await collaborationService.updateRoom(selectedRoomForMenu.room_id, {
          status: RoomStatus.ARCHIVED
        } as any);
        toast.success('Room archived successfully');
        fetchRooms();
      } catch (error) {
        console.error('Failed to archive room:', error);
      }
    }
    handleMenuClose();
  };

  const getRoomIcon = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return <SchoolIcon />;
      case RoomType.CASE_DISCUSSION:
      default:
        return <GroupIcon />;
    }
  };

  const getRoomTypeColor = (type: RoomType) => {
    switch (type) {
      case RoomType.TEACHING:
        return 'secondary';
      case RoomType.CASE_DISCUSSION:
      default:
        return 'primary';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <Typography>Loading rooms...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Collaboration Rooms
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Join real-time discussions with medical professionals and collaborate on cases
        </Typography>
      </Box>

      {/* Actions and Filters */}
      <Box mb={3}>
        <Grid container spacing={2} alignItems="center">
          <Grid xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search rooms..."
              value={searchTerm}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Participation</InputLabel>
              <Select
                value={participationFilter}
                onChange={(e: any) => setParticipationFilter(e.target.value as ParticipationFilter)}
                label="Participation"
              >
                <MenuItem value="all">All Rooms</MenuItem>
                <MenuItem value="created">Created by me</MenuItem>
                <MenuItem value="member">I'm a member</MenuItem>
                <MenuItem value="pending">Pending requests</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid xs={12} md={5} textAlign="right">
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/rooms/new')}
            >
              Create Room
            </Button>
          </Grid>
        </Grid>
      </Box>

      {/* Room Type Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabValue} onChange={(e: React.SyntheticEvent, newValue: number) => setTabValue(newValue)}>
          <Tab label="All Rooms" />
          <Tab label="Case Discussions" icon={<GroupIcon />} iconPosition="start" />
          <Tab label="Teaching Sessions" icon={<SchoolIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Room Grid */}
      <TabPanel value={tabValue} index={tabValue}>
        <Grid container spacing={3}>
          {filteredRooms.length > 0 ? (
            filteredRooms.map((room) => (
              <Grid xs={12} sm={6} md={4} key={room.room_id}>
                <Card 
                  sx={{ 
                    height: '100%', 
                    cursor: 'pointer',
                    '&:hover': { boxShadow: 3 }
                  }}
                  onClick={() => handleJoinRoom(room)}
                >
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                      <Box display="flex" alignItems="center">
                        <Avatar sx={{ bgcolor: `${getRoomTypeColor(room.room_type)}.main`, mr: 2 }}>
                          {getRoomIcon(room.room_type)}
                        </Avatar>
                        <Box>
                          <Typography variant="h6" noWrap>
                            {room.name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            Created by {room.host_id === currentUserId ? 'You' : 'Dr. Smith'}
                          </Typography>
                        </Box>
                      </Box>
                      {room.host_id === currentUserId && (
                        <IconButton
                          size="small"
                          onClick={(e: React.MouseEvent<HTMLElement>) => handleMenuClick(e, room)}
                        >
                          <MoreVertIcon />
                        </IconButton>
                      )}
                    </Box>

                    <Typography variant="body2" color="textSecondary" mb={2}>
                      {room.description || 'No description available'}
                    </Typography>

                    <Box display="flex" alignItems="center" gap={1} mb={2}>
                      <Chip
                        size="small"
                        icon={room.is_private ? <LockIcon /> : <PublicIcon />}
                        label={room.is_private ? 'Private' : 'Public'}
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        icon={<PersonIcon />}
                        label={`${room.participant_count || 0} participants`}
                        variant="outlined"
                      />
                    </Box>

                    {room.tags && room.tags.length > 0 && (
                      <Box display="flex" flexWrap="wrap" gap={0.5}>
                        {room.tags.map((tag: string, index: number) => (
                          <Chip
                            key={index}
                            label={tag}
                            size="small"
                            color={getRoomTypeColor(room.room_type)}
                          />
                        ))}
                      </Box>
                    )}

                    {room.room_type === RoomType.TEACHING && room.metadata?.subject && (
                      <Box mt={2} display="flex" alignItems="center">
                        <CalendarIcon fontSize="small" sx={{ mr: 1 }} />
                        <Typography variant="caption" color="textSecondary">
                          Subject: {room.metadata.subject}
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))
          ) : (
            <Grid xs={12}>
              <Box textAlign="center" py={5}>
                <Typography variant="h6" gutterBottom>
                  No rooms found
                </Typography>
                <Typography variant="body2" color="textSecondary" mb={2}>
                  {searchTerm ? 'Try adjusting your search or filters' : 'Be the first to create a room!'}
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => navigate('/rooms/new')}
                >
                  Create Room
                </Button>
              </Box>
            </Grid>
          )}
        </Grid>
      </TabPanel>

      {/* Room Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleSettingsClick}>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Room Settings</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleArchiveRoom}>
          <ListItemIcon>
            <ArchiveIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Archive Room</ListItemText>
        </MenuItem>
      </Menu>

      {/* Modals */}
      {selectedRoom && (
        <>
          <RoomSettingsModal
            open={settingsModalOpen}
            onClose={() => {
              setSettingsModalOpen(false);
              fetchRooms();
            }}
            room={selectedRoom}
          />
          <RoomDetailsModal
            open={detailsModalOpen}
            onClose={() => setDetailsModalOpen(false)}
            room={selectedRoom}
            onJoinRequest={handleRequestJoin}
          />
        </>
      )}
    </Box>
  );
};

export default CollaborationRooms;