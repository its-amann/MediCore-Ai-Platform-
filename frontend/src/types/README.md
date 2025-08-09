# Medical Imaging Types Documentation

This directory contains TypeScript type definitions for the medical imaging service and related components.

## File Structure

- `medical.ts` - Comprehensive medical imaging and report types
- `common.ts` - Common types used across the application
- `websocket.ts` - WebSocket communication types
- `room.ts` - Collaboration room types
- `index.ts` - Central export file

## Usage Examples

### Importing Types

```typescript
// Import specific types
import { ImagingReport, MedicalReport, Finding } from '@/types/medical';

// Import from index
import { ImagingReport, Message, Room } from '@/types';

// Import enums
import { ReportStatus, ImagingModality, FindingSeverity } from '@/types/medical';
```

### Using ImagingReport Type

```typescript
import { ImagingReport, ReportStatus, ImagingModality } from '@/types/medical';

const report: ImagingReport = {
  id: 'report-123',
  patientId: 'patient-456',
  patientName: 'John Doe',
  reportDate: new Date(),
  studyDate: new Date(),
  studyType: StudyType.DIAGNOSTIC,
  modality: ImagingModality.CT,
  findings: [],
  impression: 'No acute findings',
  status: ReportStatus.FINAL,
  images: [],
  timestamps: {
    created: new Date()
  }
};
```

### Using MedicalReport Type

```typescript
import { MedicalReport } from '@/types/medical';

const medicalReport: MedicalReport = {
  id: 'med-report-123',
  patientId: 'patient-456',
  patientName: 'Jane Smith',
  createdAt: new Date(),
  updatedAt: new Date(),
  studyType: 'CT Chest',
  images: [],
  findings: [],
  summary: 'Chest CT performed for evaluation',
  recommendations: ['Follow-up in 6 months']
};
```

### API Response Types

```typescript
import { ImagingReportResponse, ImagingReportListResponse } from '@/types/medical';

// Single report response
const response: ImagingReportResponse = {
  success: true,
  data: report,
  metadata: {
    requestId: 'req-123',
    timestamp: new Date().toISOString(),
    processingTime: 250
  }
};

// List response with pagination
const listResponse: ImagingReportListResponse = {
  success: true,
  data: {
    reports: [report],
    pagination: {
      page: 1,
      pageSize: 20,
      totalItems: 100,
      totalPages: 5
    }
  }
};
```

### Working with Findings

```typescript
import { ImagingFinding, FindingCategory, FindingSeverity } from '@/types/medical';

const finding: ImagingFinding = {
  id: 'finding-001',
  category: FindingCategory.SUSPICIOUS,
  type: 'nodule',
  description: '8mm nodule in right upper lobe',
  location: {
    region: 'Right lung',
    subregion: 'Upper lobe',
    laterality: 'right'
  },
  measurements: [{
    type: 'linear',
    value: 8,
    unit: 'mm',
    label: 'Maximum diameter'
  }],
  severity: FindingSeverity.MODERATE,
  confidence: 0.92,
  followUpRecommended: true
};
```

### Request Types

```typescript
import { CreateImagingReportRequest, ImagingAnalysisRequest } from '@/types/medical';

// Create report request
const createRequest: CreateImagingReportRequest = {
  patientId: 'patient-123',
  studyType: StudyType.DIAGNOSTIC,
  modality: ImagingModality.MRI,
  images: [file1, file2], // File objects
  indication: 'Headache evaluation',
  urgency: 'routine'
};

// Analysis request
const analysisRequest: ImagingAnalysisRequest = {
  imageIds: ['img-1', 'img-2'],
  analysisType: 'full',
  aiModel: 'radiology-v2',
  enhancementOptions: {
    contrastAdjustment: true,
    noiseReduction: true
  }
};
```

## Type Compatibility

These types are designed to be compatible with:
- Frontend React components
- Backend API responses
- WebSocket messages
- DICOM metadata
- HL7 integration

## Best Practices

1. **Use Enums**: Prefer enums over string literals for consistency
   ```typescript
   // Good
   status: ReportStatus.FINAL
   
   // Avoid
   status: 'final'
   ```

2. **Type Guards**: Create type guards for runtime validation
   ```typescript
   function isImagingReport(obj: any): obj is ImagingReport {
     return obj && typeof obj.id === 'string' && obj.modality in ImagingModality;
   }
   ```

3. **Partial Types**: Use utility types for updates
   ```typescript
   type UpdateReport = Partial<ImagingReport>;
   ```

4. **Strict Null Checks**: Handle optional properties properly
   ```typescript
   if (report.recommendations?.length) {
     // Handle recommendations
   }
   ```

## Integration with Backend

The types are structured to match backend API responses. When receiving data from the backend:

```typescript
import { ImagingReportResponse } from '@/types/medical';

async function fetchReport(id: string): Promise<ImagingReport | null> {
  const response = await fetch(`/api/reports/${id}`);
  const data: ImagingReportResponse = await response.json();
  
  if (data.success && data.data) {
    return data.data;
  }
  
  console.error(data.error);
  return null;
}
```

## Extending Types

To extend types for specific use cases:

```typescript
// Extend for UI state
interface ImagingReportWithUI extends ImagingReport {
  isSelected: boolean;
  isExpanded: boolean;
  validationErrors?: string[];
}

// Extend for form handling
interface ImagingReportForm extends Partial<ImagingReport> {
  isDirty: boolean;
  touchedFields: Set<keyof ImagingReport>;
}
```