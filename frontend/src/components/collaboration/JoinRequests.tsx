import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  IconButton,
  Chip,
  Divider,
  Alert,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  Person as PersonIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Search as SearchIcon,
  AccessTime as TimeIcon,
  Message as MessageIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'react-hot-toast';
import collaborationService, { JoinRequest } from '../../services/collaborationService';

interface JoinRequestsProps {
  roomId: string;
  roomName: string;
  onRequestHandled?: () => void;
}

const JoinRequests: React.FC<JoinRequestsProps> = ({ roomId, roomName, onRequestHandled }) => {
  const [requests, setRequests] = useState<JoinRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchJoinRequests();
    // Set up polling for new requests
    const interval = setInterval(fetchJoinRequests, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [roomId]);

  const fetchJoinRequests = async () => {
    try {
      const response = await collaborationService.getJoinRequests(roomId);
      setRequests(response.requests || []);
    } catch (error) {
      console.error('Failed to fetch join requests:', error);
      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRequest = async (requestId: string, action: 'approve' | 'reject') => {
    setProcessingIds(prev => new Set(prev).add(requestId));
    
    try {
      await collaborationService.handleJoinRequest(roomId, requestId, action);
      toast.success(`Request ${action}d successfully`);
      
      // Remove the request from the list
      setRequests(prev => prev.filter(r => r.request_id !== requestId));
      
      if (onRequestHandled) {
        onRequestHandled();
      }
    } catch (error) {
      console.error(`Failed to ${action} request:`, error);
      toast.error(`Failed to ${action} request`);
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(requestId);
        return newSet;
      });
    }
  };

  const filteredRequests = requests.filter(request =>
    request.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    request.message?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingRequests = filteredRequests.filter(r => r.status === 'pending');

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" height={200}>
            <Typography>Loading join requests...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box mb={3}>
          <Typography variant="h6" gutterBottom>
            Join Requests for {roomName}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {pendingRequests.length} pending request{pendingRequests.length !== 1 ? 's' : ''}
          </Typography>
        </Box>

        {pendingRequests.length > 0 && (
          <Box mb={3}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search requests..."
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
          </Box>
        )}

        {pendingRequests.length === 0 ? (
          <Box textAlign="center" py={4}>
            <PersonIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="body1" color="textSecondary">
              No pending join requests
            </Typography>
            <Typography variant="body2" color="textSecondary" mt={1}>
              New requests will appear here
            </Typography>
          </Box>
        ) : (
          <List>
            {pendingRequests.map((request, index) => (
              <React.Fragment key={request.request_id}>
                {index > 0 && <Divider />}
                <ListItem
                  sx={{
                    py: 2,
                    opacity: processingIds.has(request.request_id) ? 0.6 : 1,
                  }}
                >
                  <ListItemAvatar>
                    <Avatar>
                      <PersonIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography variant="subtitle1" fontWeight="medium">
                          {request.username}
                        </Typography>
                        {request.message && (
                          <Box display="flex" alignItems="start" mt={1}>
                            <MessageIcon sx={{ fontSize: 16, mr: 1, mt: 0.5, color: 'text.secondary' }} />
                            <Typography variant="body2" color="textSecondary">
                              "{request.message}"
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    }
                    secondary={
                      <Box display="flex" alignItems="center" mt={1}>
                        <TimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                        <Typography variant="caption">
                          {formatDistanceToNow(new Date(request.created_at), { addSuffix: true })}
                        </Typography>
                      </Box>
                    }
                  />
                  <Box display="flex" gap={1}>
                    <IconButton
                      color="success"
                      onClick={() => handleRequest(request.request_id, 'approve')}
                      disabled={processingIds.has(request.request_id)}
                      title="Approve"
                    >
                      <CheckIcon />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => handleRequest(request.request_id, 'reject')}
                      disabled={processingIds.has(request.request_id)}
                      title="Reject"
                    >
                      <CloseIcon />
                    </IconButton>
                  </Box>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}

        {pendingRequests.length > 5 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Tip: You can approve multiple requests quickly by using keyboard shortcuts.
              Press 'A' to approve or 'R' to reject the selected request.
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default JoinRequests;