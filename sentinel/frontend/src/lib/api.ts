/**
 * SENTINEL v2.0 — Centralized API Client Module
 * Connects Frontend Subsystems to FastAPI Intelligence Core.
 */

const API_BASE = '/api';

export interface GraphResponse {
  nodes: any[];
  edges: any[];
  total_nodes?: number;
  total_edges?: number;
}

async function request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const res = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json();
  }
  return res.text() as any;
}

const get = <T = any>(endpoint: string) => request<T>(endpoint, { method: 'GET' });
const post = <T = any>(endpoint: string, body?: any) =>
  request<T>(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
const del = <T = any>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' });

const postFormData = <T = any>(endpoint: string, formData: FormData) =>
  request<T>(endpoint, {
    method: 'POST',
    body: formData,
  });

// ==========================================
// 1. DASHBOARD & SYSTEM METRICS
// ==========================================
export const getDashboard = () => get('/dashboard');
export const getHealth = () => get('/health');

// ==========================================
// 2. KNOWLEDGE GRAPH
// ==========================================
export const getFullGraph = (): Promise<GraphResponse> => get<GraphResponse>('/graph/full');
export const getNode = (nodeId: string) => get(`/graph/node/${encodeURIComponent(nodeId)}`);
export const expandNode = (nodeId: string, depth: number = 2): Promise<GraphResponse> =>
  get<GraphResponse>(`/graph/node/${encodeURIComponent(nodeId)}/expand?depth=${depth}`);
export const oneClickExpand = (nodeId: string, depth: number = 2): Promise<GraphResponse> =>
  get<GraphResponse>(`/graph/one-click-expand/${encodeURIComponent(nodeId)}?depth=${depth}`);
export const getShortestPath = (source: string, target: string) =>
  get(`/graph/shortest-path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
export const searchNodes = (query: string) =>
  get(`/graph/search?q=${encodeURIComponent(query)}`);
export const getGraphStats = () => get('/graph/stats');
export const deleteGraphNode = (nodeId: string) => del(`/graph/node/${encodeURIComponent(nodeId)}`);
export const clearGraph = () => post('/graph/clear');
export const loadSampleData = () => post('/admin/load-sample-data');

// ==========================================
// 3. ANALYTICAL ENGINES
// ==========================================
export const getCentrality = () => get('/analysis/centrality');
export const getCommunities = () => get('/analysis/communities');
export const getKingpins = (n: number = 10) => get(`/analysis/kingpins?n=${n}`);
export const getHawala = (maxHours: number = 72, threshold: number = 50000) =>
  get(`/analysis/hawala?max_hours=${maxHours}&threshold=${threshold}`);
export const getBurnerPhones = () => get('/analysis/burner-phones');
export const getTemporal = () => get('/analysis/temporal');
export const getRiskScores = () => get('/analysis/risk-scores');
export const getSuspectCriminalHistory = (suspectId: string) =>
  get(`/analysis/suspect/${encodeURIComponent(suspectId)}/criminal-history`);

// ==========================================
// 4. GEO-INTELLIGENCE & REAL MAP
// ==========================================
export const getCellTowers = (district?: string) =>
  get(`/geo/towers${district ? `?district=${encodeURIComponent(district)}` : ''}`);
export const getSuspectTrail = (phoneNumber: string) =>
  get(`/geo/trail/${encodeURIComponent(phoneNumber)}`);
export const getColocations = () => get('/geo/colocations');
export const getGeofences = () => get('/geo/geofences');
export const getMapIncidents = () => get('/geo/incidents');
export const getCrimeHotspots = () => get('/geo/hotspots');
export const compareSuspectTrails = (phones: string[]) =>
  post('/geo/compare', { phones });

// ==========================================
// 5. NATURAL LANGUAGE CHAT & AI AGENT
// ==========================================
export const sendQuery = (
  message: string,
  optionsOrForceAi?: boolean | { image_url?: string; force_ai?: boolean },
  imageUrl?: string
) => {
  let forceAi = false;
  let img = imageUrl;
  if (typeof optionsOrForceAi === 'boolean') {
    forceAi = optionsOrForceAi;
  } else if (typeof optionsOrForceAi === 'object' && optionsOrForceAi !== null) {
    forceAi = !!optionsOrForceAi.force_ai;
    img = optionsOrForceAi.image_url || img;
  }
  return post('/chat/query', { message, force_ai: forceAi, image_url: img });
};

// ==========================================
// 6. AUTOMATED ALERTS & THREAT CENTER
// ==========================================
export const getAllAlerts = (limit: number = 100, unacknowledged: boolean = false) =>
  get(`/alerts?limit=${limit}&unacknowledged=${unacknowledged}`);
export const getAlertsSummary = () => get('/alerts/summary');
export const acknowledgeAlert = (alertId: string) => post(`/alerts/acknowledge/${encodeURIComponent(alertId)}`);
export const dismissAlert = (alertId: string) => post(`/alerts/dismiss/${encodeURIComponent(alertId)}`);
export const escalateAlert = (alertId: string) => post(`/alerts/escalate/${encodeURIComponent(alertId)}`);
export const deleteAlert = (alertId: string) => del(`/alerts/${encodeURIComponent(alertId)}`);
export const clearAlerts = () => post('/alerts/clear');

// ==========================================
// 7. COLLABORATIVE CASE BOARD
// ==========================================
export const getCaseCards = () => get('/caseboard/cards');
export const moveCaseCard = (caseId: string, newStatus: string) =>
  post('/caseboard/move', { case_id: caseId, new_status: newStatus });
export const addCaseCard = (card: any) => post('/caseboard/add', card);
export const deleteCaseCard = (caseId: string) => del(`/caseboard/cards/${encodeURIComponent(caseId)}`);
export const clearCaseCards = () => post('/caseboard/clear');

// ==========================================
// 8. EVIDENCE VAULT & BLOCKCHAIN AUDIT
// ==========================================
export const getAllEvidence = () => get('/evidence/all');
export const verifyEvidence = (evidenceId: string) => get(`/evidence/verify/${encodeURIComponent(evidenceId)}`);
export const verifyChainIntegrity = () => get('/export/verify');
export const simulateEvidenceTamper = (blockIndex: number = 1) =>
  post(`/evidence/simulate-tamper?block_index=${blockIndex}`);
export const restoreEvidenceIntegrity = () => post('/evidence/restore');
export const deleteEvidence = (evidenceId: string) => del(`/evidence/${encodeURIComponent(evidenceId)}`);
export const clearEvidenceVault = () => post('/evidence/clear');

// ==========================================
// 9. BIOMETRIC FACE TRACKER
// ==========================================
export const uploadFaceImage = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/faces/upload', formData);
};

export const registerFaceProfile = (faceIdOrData: any, suspectName?: string) => {
  const body = typeof faceIdOrData === 'object'
    ? faceIdOrData
    : { face_id: faceIdOrData, suspect_name: suspectName };
  return post('/faces/register', body);
};

export const searchFaceMatches = (faceId: string, minSimilarity?: number) =>
  get(`/faces/search/${encodeURIComponent(faceId)}${minSimilarity ? `?min_similarity=${minSimilarity}` : ''}`);

export const getAllFaceProfiles = () => get('/faces/profiles');
export const deleteFaceProfile = (faceId: string) => del(`/faces/profiles/${encodeURIComponent(faceId)}`);
export const scanAllEvidenceFaces = (faceId: string, minSimilarity?: number) =>
  post(`/faces/scan-all/${encodeURIComponent(faceId)}`);

export const getFaceMatchReport = async (faceId: string): Promise<Blob> => {
  const res = await fetch(`${API_BASE}/faces/report/${encodeURIComponent(faceId)}`);
  if (!res.ok) throw new Error('Failed to download face match report');
  return res.blob();
};

// ==========================================
// 10. TACTICAL PERSON TRACKER (YOLOv8)
// ==========================================
export const detectPersonsInImage = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return postFormData('/persons/detect', formData);
};

export const detectPersonsInFrame = (frame: Blob) => {
  const formData = new FormData();
  formData.append('frame', frame, 'frame.jpg');
  return postFormData('/persons/detect-frame', formData);
};

export const captureAndSaveFrame = (frame: Blob) => {
  const formData = new FormData();
  formData.append('frame', frame, 'capture.jpg');
  return postFormData('/persons/capture', formData);
};

export const getActiveTargetPerson = () => get('/persons/target');
export const clearActiveTargetPerson = () => post('/persons/target/clear');

export const getPersonDetectionHistory = () => get('/persons/history');

export const batchDetectPersons = (files: File[]) => {
  const formData = new FormData();
  files.forEach(f => formData.append('files', f));
  return postFormData('/persons/batch-detect', formData);
};

export const exportDetectionLog = async (): Promise<Blob> => {
  const res = await fetch(`${API_BASE}/persons/export-log`);
  if (!res.ok) throw new Error('Failed to export detection log');
  return res.blob();
};

// ==========================================
// 11. INGESTION PIPELINE
// ==========================================
export const uploadFile = (fileOrFormData: File | FormData, autoCommit: boolean = true) => {
  if (fileOrFormData instanceof FormData) {
    return postFormData(`/ingest/upload?auto_commit=${autoCommit}`, fileOrFormData);
  }
  const formData = new FormData();
  formData.append('file', fileOrFormData);
  return postFormData(`/ingest/upload?auto_commit=${autoCommit}`, formData);
};

export const processFile = (uploadId: string) => post(`/ingest/process/${encodeURIComponent(uploadId)}`);
export const getUploadHistory = () => get('/ingest/history');
export const getPreview = (uploadId: string) => get(`/ingest/preview/${encodeURIComponent(uploadId)}`);
export const autoIngestSamplePDF = (sampleType: string = 'fir') =>
  post(`/ingest/auto-test-sample?sample_type=${encodeURIComponent(sampleType)}`);
export const deleteUploadHistoryItem = (uploadId: string) => del(`/ingest/history/${encodeURIComponent(uploadId)}`);
export const clearUploadHistory = () => post('/ingest/clear-history');

// ==========================================
// 12. REPORT GENERATOR & EXPORT
// ==========================================
export const generateDossier = (suspectId: string) => post('/export/dossier', { suspect_id: suspectId });
export const getDailyDigest = () => get('/export/reports/daily');
export const getWeeklyBrief = () => get('/export/reports/weekly');
export const getMonthlyStats = () => get('/export/reports/monthly');

// ==========================================
// 13. ADMIN COMMAND SUITE & DATA PURGE
// ==========================================
export const getAdminUsers = () => get('/admin/users');
export const getAdminAudit = () => get('/admin/audit');
export const getAdminHealth = () => get('/admin/health');
export const clearAllSystemData = () => post('/admin/clear-all-data');
export const loadSampleDemoData = () => post('/admin/load-sample-data');
export const purgeAdminGraph = () => post('/admin/purge-graph');
export const purgeAdminCases = () => post('/admin/purge-cases');
export const purgeAdminEvidence = () => post('/admin/purge-evidence');
export const purgeAdminAlerts = () => post('/admin/purge-alerts');
export const purgeAdminUploads = () => post('/admin/purge-uploads');
