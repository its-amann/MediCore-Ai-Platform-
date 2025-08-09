import React, { useState, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Avatar,
  Stack,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Badge,
  Card,
  CardContent
} from '@mui/material';
import {
  PhotoCamera as CameraIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Verified as VerifiedIcon,
  School as SchoolIcon,
  LocalHospital as HospitalIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { UserProfile, UserType } from '../../types/collaboration';

interface UserProfileEditorProps {
  profile: UserProfile;
  onSave: (updatedProfile: Partial<UserProfile>) => Promise<void>;
  onVerificationRequest?: () => void;
  canChangeUserType?: boolean;
}

interface ValidationError {
  field: string;
  message: string;
}

export const UserProfileEditor: React.FC<UserProfileEditorProps> = ({
  profile,
  onSave,
  onVerificationRequest,
  canChangeUserType = false
}) => {
  const [editMode, setEditMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [editedProfile, setEditedProfile] = useState<Partial<UserProfile>>({
    full_name: profile.full_name || '',
    bio: profile.bio || '',
    specialization: profile.specialization || '',
    institution: profile.institution || '',
    license_number: profile.license_number || '',
    user_type: profile.user_type
  });
  const [profileImage, setProfileImage] = useState<File | null>(null);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(profile.profile_picture || null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [showVerificationDialog, setShowVerificationDialog] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getUserTypeIcon = (userType: UserType) => {
    const icons = {
      [UserType.DOCTOR]: <HospitalIcon />,
      [UserType.TEACHER]: <SchoolIcon />,
      [UserType.STUDENT]: <PersonIcon />,
      [UserType.PATIENT]: <PersonIcon />,
      [UserType.ADMIN]: <AdminIcon />
    };
    return icons[userType] || <PersonIcon />;
  };

  const getUserTypeColor = (userType: UserType) => {
    const colors = {
      [UserType.DOCTOR]: '#1976d2',
      [UserType.TEACHER]: '#9c27b0',
      [UserType.STUDENT]: '#4caf50',
      [UserType.PATIENT]: '#ff9800',
      [UserType.ADMIN]: '#f44336'
    };
    return colors[userType] || '#757575';
  };

  const handleFieldChange = (field: keyof UserProfile, value: any) => {
    setEditedProfile(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear validation error for this field
    setValidationErrors(prev => prev.filter(error => error.field !== field));
  };

  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Image size should be less than 5MB');
        return;
      }
      
      setProfileImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setProfileImageUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const validateProfile = (): boolean => {
    const errors: ValidationError[] = [];

    if (!editedProfile.full_name?.trim()) {
      errors.push({ field: 'full_name', message: 'Full name is required' });
    }

    if (editedProfile.user_type === UserType.DOCTOR) {
      if (!editedProfile.specialization?.trim()) {
        errors.push({ field: 'specialization', message: 'Specialization is required for doctors' });
      }
      if (!editedProfile.license_number?.trim()) {
        errors.push({ field: 'license_number', message: 'License number is required for doctors' });
      }
    }

    if (editedProfile.user_type === UserType.TEACHER && !editedProfile.institution?.trim()) {
      errors.push({ field: 'institution', message: 'Institution is required for teachers' });
    }

    if (editedProfile.bio && editedProfile.bio.length > 500) {
      errors.push({ field: 'bio', message: 'Bio must be less than 500 characters' });
    }

    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleSave = async () => {
    if (!validateProfile()) {
      toast.error('Please fix the validation errors');
      return;
    }

    setIsLoading(true);
    try {
      const updates: Partial<UserProfile> = { ...editedProfile };
      
      // Handle profile image upload
      if (profileImage) {
        // In a real implementation, upload the image and get the URL
        // const imageUrl = await uploadProfileImage(profileImage);
        // updates.profile_picture = imageUrl;
      }

      await onSave(updates);
      toast.success('Profile updated successfully');
      setEditMode(false);
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setEditedProfile({
      full_name: profile.full_name || '',
      bio: profile.bio || '',
      specialization: profile.specialization || '',
      institution: profile.institution || '',
      license_number: profile.license_number || '',
      user_type: profile.user_type
    });
    setProfileImageUrl(profile.profile_picture || null);
    setProfileImage(null);
    setValidationErrors([]);
    setEditMode(false);
  };

  const getFieldError = (field: string): string | undefined => {
    return validationErrors.find(error => error.field === field)?.message;
  };

  const calculateProfileCompletion = (): number => {
    const fields = ['full_name', 'bio', 'profile_picture'];
    
    if (profile.user_type === UserType.DOCTOR) {
      fields.push('specialization', 'license_number', 'institution');
    } else if (profile.user_type === UserType.TEACHER) {
      fields.push('institution', 'specialization');
    } else if (profile.user_type === UserType.STUDENT) {
      fields.push('institution');
    }

    const completedFields = fields.filter(field => 
      profile[field as keyof UserProfile] && 
      profile[field as keyof UserProfile] !== ''
    ).length;

    return Math.round((completedFields / fields.length) * 100);
  };

  const profileCompletion = calculateProfileCompletion();

  return (
    <Box>
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5">User Profile</Typography>
          {!editMode ? (
            <Button
              variant="contained"
              startIcon={<EditIcon />}
              onClick={() => setEditMode(true)}
            >
              Edit Profile
            </Button>
          ) : (
            <Stack direction="row" spacing={1}>
              <Button
                variant="outlined"
                startIcon={<CancelIcon />}
                onClick={handleCancel}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={isLoading}
              >
                {isLoading ? <CircularProgress size={20} /> : 'Save'}
              </Button>
            </Stack>
          )}
        </Box>

        {/* Profile Completion */}
        <Card sx={{ mb: 3, bgcolor: 'background.default' }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle2">Profile Completion</Typography>
              <Typography variant="subtitle2" color="primary">
                {profileCompletion}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={profileCompletion}
              sx={{ height: 8, borderRadius: 4 }}
              color={profileCompletion === 100 ? 'success' : 'primary'}
            />
            {profileCompletion < 100 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Complete your profile for better collaboration experience
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* Profile Picture */}
        <Box display="flex" alignItems="center" gap={3} mb={3}>
          <Badge
            overlap="circular"
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            badgeContent={
              editMode ? (
                <IconButton
                  size="small"
                  sx={{
                    bgcolor: 'primary.main',
                    color: 'white',
                    '&:hover': { bgcolor: 'primary.dark' }
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <CameraIcon fontSize="small" />
                </IconButton>
              ) : profile.is_verified ? (
                <VerifiedIcon sx={{ color: 'success.main' }} />
              ) : null
            }
          >
            <Avatar
              src={profileImageUrl || undefined}
              sx={{
                width: 100,
                height: 100,
                bgcolor: getUserTypeColor(profile.user_type)
              }}
            >
              {profile.full_name?.[0] || profile.username[0]}
            </Avatar>
          </Badge>

          <Box>
            <Typography variant="h6">
              {editMode ? (
                <TextField
                  value={editedProfile.full_name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('full_name', e.target.value)}
                  error={!!getFieldError('full_name')}
                  helperText={getFieldError('full_name')}
                  size="small"
                  fullWidth
                />
              ) : (
                profile.full_name || profile.username
              )}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" mt={1}>
              <Chip
                icon={getUserTypeIcon(profile.user_type)}
                label={profile.user_type}
                size="small"
                sx={{
                  bgcolor: getUserTypeColor(profile.user_type),
                  color: 'white'
                }}
              />
              {profile.is_verified && (
                <Chip
                  icon={<VerifiedIcon />}
                  label="Verified"
                  size="small"
                  color="success"
                />
              )}
            </Stack>
          </Box>
        </Box>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleImageSelect}
        />

        <Divider sx={{ my: 3 }} />

        {/* User Type Selection */}
        {editMode && canChangeUserType && (
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>User Type</InputLabel>
            <Select
              value={editedProfile.user_type}
              onChange={(e: React.ChangeEvent<{ value: unknown }>) => handleFieldChange('user_type', e.target.value)}
              label="User Type"
            >
              {Object.values(UserType).map(type => (
                <MenuItem key={type} value={type}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getUserTypeIcon(type)}
                    <Typography>{type}</Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {/* Profile Fields */}
        <Stack spacing={3}>
          <TextField
            label="Email"
            value={profile.email}
            disabled
            fullWidth
            InputProps={{
              readOnly: true
            }}
          />

          <TextField
            label="Username"
            value={profile.username}
            disabled
            fullWidth
            InputProps={{
              readOnly: true
            }}
          />

          <TextField
            label="Bio"
            value={editMode ? editedProfile.bio : profile.bio}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('bio', e.target.value)}
            error={!!getFieldError('bio')}
            helperText={getFieldError('bio') || `${editedProfile.bio?.length || 0}/500`}
            multiline
            rows={3}
            disabled={!editMode}
            fullWidth
          />

          {(profile.user_type === UserType.DOCTOR || profile.user_type === UserType.TEACHER) && (
            <TextField
              label="Specialization"
              value={editMode ? editedProfile.specialization : profile.specialization}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('specialization', e.target.value)}
              error={!!getFieldError('specialization')}
              helperText={getFieldError('specialization')}
              disabled={!editMode}
              fullWidth
            />
          )}

          {(profile.user_type === UserType.DOCTOR || 
            profile.user_type === UserType.TEACHER || 
            profile.user_type === UserType.STUDENT) && (
            <TextField
              label="Institution"
              value={editMode ? editedProfile.institution : profile.institution}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('institution', e.target.value)}
              error={!!getFieldError('institution')}
              helperText={getFieldError('institution')}
              disabled={!editMode}
              fullWidth
            />
          )}

          {profile.user_type === UserType.DOCTOR && (
            <TextField
              label="License Number"
              value={editMode ? editedProfile.license_number : profile.license_number}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('license_number', e.target.value)}
              error={!!getFieldError('license_number')}
              helperText={getFieldError('license_number')}
              disabled={!editMode}
              fullWidth
            />
          )}
        </Stack>

        {/* Verification Section */}
        {!profile.is_verified && (profile.user_type === UserType.DOCTOR || profile.user_type === UserType.TEACHER) && (
          <Alert
            severity="warning"
            sx={{ mt: 3 }}
            action={
              <Button
                size="small"
                onClick={() => setShowVerificationDialog(true)}
              >
                Request Verification
              </Button>
            }
          >
            Your profile is not verified. Verification adds credibility and enables additional features.
          </Alert>
        )}
      </Paper>

      {/* Verification Dialog */}
      <Dialog open={showVerificationDialog} onClose={() => setShowVerificationDialog(false)}>
        <DialogTitle>Request Verification</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Profile verification helps build trust in the community. You'll need to provide:
          </Typography>
          <List>
            {profile.user_type === UserType.DOCTOR && (
              <>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Medical License"
                    secondary="Valid medical license number and documentation"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Institution Verification"
                    secondary="Proof of current affiliation"
                  />
                </ListItem>
              </>
            )}
            {profile.user_type === UserType.TEACHER && (
              <>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Teaching Credentials"
                    secondary="Valid teaching certificate or credentials"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Institution Verification"
                    secondary="Proof of teaching position"
                  />
                </ListItem>
              </>
            )}
          </List>
          <Alert severity="info" sx={{ mt: 2 }}>
            Verification typically takes 2-3 business days
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowVerificationDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              setShowVerificationDialog(false);
              if (onVerificationRequest) {
                onVerificationRequest();
              }
              toast.success('Verification request submitted');
            }}
          >
            Submit Request
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};