import axios from 'axios'
import {
  Repo,
  Capability,
  Playbook,
  Approval,
  QueryRequest,
  QueryResult,
  ExecuteRequest,
  IngestRequest,
  IngestResponse,
  AgentTask,
  FeedbackSubmission,
} from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const healthCheck = () => api.get('/health').then((r) => r.data)

export const ingestRepo = (req: IngestRequest) =>
  api.post<IngestResponse>('/repos', req).then((r) => r.data)

export const getRepo = (id: string) =>
  api.get<Repo>(`/repos/${id}`).then((r) => r.data)

export const getParse = (id: string) =>
  api.get(`/parse/${id}`).then((r) => r.data)

export const listCapabilities = (params?: { repo?: string; category?: string }) =>
  api.get<Capability[]>('/capabilities', { params }).then((r) => r.data)

export const listPlaybooks = (params?: { repo?: string; capability_id?: string }) =>
  api.get<Playbook[]>('/playbooks', { params }).then((r) => r.data)

export const listPlaybookVersions = (id: string) =>
  api.get<Playbook[]>(`/playbooks/${id}/versions`).then((r) => r.data)

export const transferPlaybook = (id: string, body: { repo: string }) =>
  api.post(`/playbooks/${id}/transfer`, body).then((r) => r.data)

export const query = (req: QueryRequest) =>
  api.post<QueryResult[]>('/query', req).then((r) => r.data)

export const executePlaybook = (req: ExecuteRequest) =>
  api.post('/execute', req).then((r) => r.data)

export const listApprovals = (params?: { status?: string }) =>
  api.get<Approval[]>('/approvals', { params }).then((r) => r.data)

export const getApprovalDiff = (id: string) =>
  api.get<string>(`/approvals/${id}/diff`).then((r) => r.data)

export const submitApprovalDecision = (id: string, decision: 'approved' | 'rejected') =>
  api.post(`/approvals/${id}/decision`, { decision }).then((r) => r.data)

export const getFeedbackMetrics = (playbookId: string) =>
  api.get(`/feedback/${playbookId}/metrics`).then((r) => r.data)

export const submitFeedback = (body: FeedbackSubmission) =>
  api.post('/feedback', body).then((r) => r.data)

export const searchKnowledge = (body: { query: string; language?: string }) =>
  api.post('/knowledge/search', body).then((r) => r.data)

export const executeAgent = (task: AgentTask) =>
  api.post('/agents/execute', task).then((r) => r.data)

export default api
