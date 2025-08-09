import medicalImagingApi from './medicalImagingApi';

interface UploadImagesResponse {
  report_id: string;
  case_id?: string;
  status: string;
  images_processed: number;
  message: string;
  workflow_id?: string;
  findings_detected?: number;
  urgency_level?: string;
  quality_score?: number;
  workflow_type?: string;
  success?: boolean;
}

interface ImagingReport {
  report_id: string;
  case_id: string;
  images: ImageAnalysis[];
  overall_analysis: string;
  clinical_impression: string;
  recommendations: string[];
  key_findings?: string[];
  citations?: any[];
  created_at: string;
  completed_at?: string;
  status: string;
}

interface ImageAnalysis {
  image_id: string;
  filename: string;
  image_type: string;
  analysis_text: string;
  findings: string[];
  keywords: string[];
  heatmap_data: {
    original_image: string;
    heatmap_overlay: string;
    heatmap_only: string;
    attention_regions: any[];
  };
}

export const medicalImagingService = {
  async uploadImages(
    files: File[],
    caseId: string,
    imageType?: string
  ): Promise<UploadImagesResponse> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    if (imageType) {
      formData.append('image_type', imageType);
    }
    
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await medicalImagingApi.post(
      '/medical-imaging/upload-images',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  async analyzeImages(
    files: File[],
    caseId: string,
    imageType?: string,
    useTemporal: boolean = false
  ): Promise<UploadImagesResponse> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    if (imageType) {
      formData.append('image_type', imageType);
    }
    formData.append('use_temporal', useTemporal.toString());
    
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await medicalImagingApi.post(
      '/medical-imaging/workflow/analyze',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  async getReport(reportId: string): Promise<ImagingReport> {
    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/${reportId}`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async getReportDetail(reportId: string): Promise<any> {
    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/${reportId}/detail`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async getCaseReports(caseId: string): Promise<ImagingReport[]> {
    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/case/${caseId}`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async downloadReport(reportId: string): Promise<Blob> {
    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/${reportId}/download`,
      {
        headers: {
                  },
        responseType: 'blob',
      }
    );

    return response.data;
  },

  async findSimilarReports(reportId: string, limit: number = 5): Promise<any[]> {
    const response = await medicalImagingApi.post(
      `/medical-imaging/imaging-reports/${reportId}/similar`,
      { limit },
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async searchReports(
    query: string,
    filters?: {
      patientId?: string;
      studyType?: string;
      severity?: string;
      startDate?: string;
      endDate?: string;
    },
    limit: number = 20
  ): Promise<any[]> {
    const params = new URLSearchParams({
      query,
      limit: limit.toString(),
    });

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          params.append(key, value);
        }
      });
    }

    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/search?${params.toString()}`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async getRecentReports(limit: number = 10, studyType?: string): Promise<any[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
    });

    if (studyType) {
      params.append('study_type', studyType);
    }

    const response = await medicalImagingApi.get(
      `/medical-imaging/imaging-reports/recent?${params.toString()}`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },

  async getSupportedImageTypes(): Promise<string[]> {
    const response = await medicalImagingApi.get(
      `/medical-imaging/image-types`,
      {
        headers: {
                  },
      }
    );

    return response.data;
  },
};

export default medicalImagingService;