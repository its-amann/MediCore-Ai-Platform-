import api from './api';

export interface Case {
  case_id: string;
  title: string;
  chief_complaint: string;
  symptoms: string[];
  status: string;
  priority: string;
  description?: string;
  medical_history?: string;
  medications?: string;
  allergies?: string;
  created_at: string;
  updated_at?: string;
  closed_at?: string;
  owner_id: string;
}

export const getCaseById = async (caseId: string): Promise<Case> => {
  const response = await api.get(`/cases/${caseId}`);
  return response.data;
};

export const getAllCases = async (): Promise<Case[]> => {
  const response = await api.get('/cases/user/cases');
  return response.data;
};

export const createCase = async (caseData: any): Promise<Case> => {
  const response = await api.post('/cases', caseData);
  return response.data;
};

export const updateCase = async (caseId: string, updates: any): Promise<Case> => {
  const response = await api.put(`/cases/${caseId}`, updates);
  return response.data;
};

export const deleteCase = async (caseId: string): Promise<void> => {
  await api.delete(`/cases/${caseId}`);
};