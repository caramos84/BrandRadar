const API_BASE_URL = 'http://localhost:8000';

export type Asset = {
  id: number;
  analysis_id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  stored_path: string;
  preview_path: string | null;
  width: number | null;
  height: number | null;
  created_at: string;
  aspect_ratio: number | null;
  pixel_area: number | null;
  visual_load_score: number | null;
  conversion_signal_score: number | null;
  text_density: number | null;
  region_count: number | null;
  text_block_count: number | null;
  cta_detected: boolean | null;
  price_detected: boolean | null;
  promo_detected: boolean | null;
  legal_detected: boolean | null;
  product_candidate_detected: boolean | null;
  logo_candidate_detected: boolean | null;
  layout_density: number | null;
  analysis_cluster_label: string | null;
  ocr_text: string | null;
  vision_data_json: string | null;
  ocr_status: string | null;
  ocr_error: string | null;
};

export type Analysis = {
  id: number;
  user_id: number;
  brand_name: string;
  category: string;
  custom_category: string | null;
  status: string;
  asset_count: number;
  created_at: string;
  updated_at: string;
};

export type AnalysisDetail = Analysis & { assets: Asset[] };

export type AnalysisMapPoint = {
  asset_id: number;
  filename: string;
  preview_url: string | null;
  x: number;
  y: number;
  cluster_id: number | null;
  width: number | null;
  height: number | null;
  file_size: number;
  aspect_ratio: number | null;
  status: string;
};

export type AnalysisMapResponse = {
  analysis_id: number;
  brand_name: string;
  asset_count: number;
  points: AnalysisMapPoint[];
};

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? 'Request failed');
  return data as T;
}

export async function listAnalyses(token: string): Promise<Analysis[]> {
  const response = await fetch(`${API_BASE_URL}/api/analyses`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseResponse<Analysis[]>(response);
}

export async function createAnalysis(token: string, payload: { brand_name: string; category: string; custom_category?: string | null }): Promise<Analysis> {
  const response = await fetch(`${API_BASE_URL}/api/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  return parseResponse<Analysis>(response);
}

export async function uploadAssets(token: string, analysisId: number, files: File[]): Promise<AnalysisDetail> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetch(`${API_BASE_URL}/api/analyses/${analysisId}/assets`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  return parseResponse<AnalysisDetail>(response);
}

export async function getAnalysisDetail(token: string, analysisId: number): Promise<AnalysisDetail> {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${analysisId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseResponse<AnalysisDetail>(response);
}

export async function getAnalysisMap(token: string, analysisId: number): Promise<AnalysisMapResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${analysisId}/map`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseResponse<AnalysisMapResponse>(response);
}
