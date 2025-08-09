# Medical Imaging Workflow Progress Visualization

## Overview

The Workflow Progress component provides a comprehensive real-time visualization of the medical imaging analysis pipeline. It shows live updates for each stage of processing, from image upload through AI analysis to final report compilation.

## Design System

### Visual Style
- **Glassmorphism Effects**: Semi-transparent containers with backdrop blur for modern depth
- **Gradient Accents**: Purple-to-indigo gradients for primary actions and highlights
- **Dark Theme**: Optimized for medical professional environments with reduced eye strain
- **Smooth Animations**: Framer Motion for fluid transitions and micro-interactions

### Color Palette
```scss
// Status Colors
$success: #10b981;  // Green - Completed stages
$active: #6366f1;   // Indigo - Processing stages
$error: #ef4444;    // Red - Failed stages
$pending: #6b7280;  // Gray - Waiting stages

// UI Colors
$background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
$glass: rgba(255, 255, 255, 0.05);
$border: rgba(255, 255, 255, 0.1);
$text-primary: rgba(255, 255, 255, 0.9);
$text-secondary: rgba(255, 255, 255, 0.6);
```

## Component Architecture

### 1. WorkflowProgress Component

The main component that orchestrates the entire workflow visualization.

#### Key Features:
- **WebSocket Integration**: Real-time updates via WebSocket connection
- **Stage Management**: Tracks progress through 6 distinct stages
- **Time Tracking**: Elapsed time and remaining time estimates
- **Error Handling**: Graceful error display with retry options
- **Logging System**: Detailed logs with export functionality

#### Props:
```typescript
interface WorkflowProgressProps {
  reportId?: string;           // Unique identifier for the workflow
  onComplete?: (report: any) => void;  // Callback when workflow completes
  onError?: (error: string) => void;   // Callback on workflow error
}
```

### 2. Workflow Stages

The system tracks progress through 6 key stages:

1. **Image Upload** (5-10s)
   - File upload and preprocessing
   - Format validation
   - Initial quality checks

2. **AI Analysis** (15-30s)
   - Coordinate detection
   - Feature extraction
   - Pattern recognition

3. **Heatmap Generation** (10-20s)
   - Attention map creation
   - Annotation overlay
   - Region highlighting

4. **Multi-Agent Analysis** (30-60s)
   - Radiologist AI: Medical interpretation
   - Researcher AI: Literature correlation
   - Clinical Advisor: Treatment suggestions
   - Report Writer: Documentation generation
   - Quality Checker: Validation and verification

5. **Knowledge Storage** (5-10s)
   - Embedding generation
   - Neo4j graph storage
   - Similarity indexing

6. **Report Compilation** (5-10s)
   - Final report assembly
   - PDF generation
   - Export preparation

### 3. Visual Components

#### Status Badge
Animated indicator showing stage status:
- **Pending**: Gray static circle
- **Processing**: Pulsing blue with rotation animation
- **Completed**: Green with checkmark
- **Error**: Red with error icon

#### Progress Bar
Linear progress indicator with:
- Gradient fill animation
- Shimmer effect for active stages
- Percentage display

#### Connection Lines
Visual connectors between stages:
- Inactive: Faded gray line
- Active: Animated gradient shimmer
- Completed: Solid blue line

#### Agent Activity
For multi-agent stage:
- Individual agent status indicators
- Real-time activity updates
- Completion checkmarks

### 4. Interactive Features

#### Expandable Details
- Click any stage to expand detailed information
- Preview images for heatmap stage
- Agent activity for multi-agent stage
- Error details for failed stages

#### Log Panel
- Collapsible detailed log view
- Timestamp for each event
- Export functionality
- Auto-scroll to latest

#### WebSocket Status
- Live connection indicator
- Auto-reconnect on disconnect
- Visual feedback for connection state

## Implementation Details

### WebSocket Protocol

Messages follow this structure:
```typescript
interface WebSocketMessage {
  type: 'stage_update' | 'agent_update' | 'error' | 'complete';
  stage?: string;
  progress?: number;
  status?: 'pending' | 'processing' | 'completed' | 'error';
  message?: string;
  details?: any;
  error?: string;
  report?: any;
}
```

### State Management

The component maintains:
- Stage statuses and progress
- WebSocket connection state
- Timing information
- Log history
- UI state (expanded sections, visibility toggles)

### Animation System

Using Framer Motion for:
- Stage entry animations (staggered)
- Progress transitions
- Expand/collapse animations
- Status badge pulsing
- Connection line shimmers

### Responsive Design

- **Desktop**: Horizontal stage layout with connection lines
- **Tablet**: Vertical stage layout, compact controls
- **Mobile**: Stacked stages, simplified animations

## Usage Example

```tsx
import WorkflowProgress from './components/WorkflowProgress';

function MedicalImagingPage() {
  const [reportId, setReportId] = useState(null);

  const handleUpload = async (files) => {
    const response = await uploadImages(files);
    setReportId(response.report_id);
  };

  const handleComplete = (report) => {
    console.log('Analysis complete:', report);
    // Navigate to report view or download
  };

  const handleError = (error) => {
    console.error('Workflow error:', error);
    // Show error notification
  };

  return (
    <div>
      {reportId && (
        <WorkflowProgress
          reportId={reportId}
          onComplete={handleComplete}
          onError={handleError}
        />
      )}
    </div>
  );
}
```

## Accessibility

- **ARIA Labels**: Descriptive labels for all interactive elements
- **Keyboard Navigation**: Tab through stages and controls
- **Screen Reader Support**: Status announcements for stage changes
- **Color Contrast**: WCAG AA compliant color combinations
- **Motion Preferences**: Reduced animations for prefers-reduced-motion

## Performance Optimizations

- **Lazy Loading**: Components load on demand
- **Memoization**: Prevent unnecessary re-renders
- **Throttled Updates**: WebSocket message batching
- **Virtual Scrolling**: For long log lists
- **Image Optimization**: Lazy load preview images

## Future Enhancements

1. **Stage Customization**: Allow dynamic stage configuration
2. **Progress Persistence**: Resume interrupted workflows
3. **Batch Processing**: Multiple image workflow tracking
4. **Analytics Dashboard**: Aggregate workflow statistics
5. **Mobile App**: Native mobile visualization
6. **3D Visualization**: Three.js powered stage representation
7. **Voice Updates**: Audio notifications for stage completion