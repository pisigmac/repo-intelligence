export interface Repo {
  id: string
  url: string
  branch: string
  commit_hash: string | null
  status: string
  storage_path: string | null
  created_at: string
  updated_at: string
}

export interface IngestRequest {
  git_url: string
  branch?: string
  auth_token?: string | null
}

export interface IngestResponse {
  job_id: string
  status: string
  repo_id: string | null
}

export interface Capability {
  id: string
  name: string
  description: string
  category: string
  repo: string
  commit: string
  entry_points: EntryPoint[]
  interfaces: Record<string, unknown>
  dependencies: string[]
  signals: Record<string, unknown>
  created_at: string
}

export interface EntryPoint {
  file: string
  method?: string
  path?: string
  line?: number | null
}

export interface Playbook {
  id: string
  capability_id: string
  name: string
  description: string
  steps: PlaybookStep[]
  validation: ValidationSpec
  rollback: RollbackSpec
  observability: ObservabilitySpec
  created_at: string
  version: string
  status: string
  parent_id?: string | null
  improved_from?: string | null
  score?: number
  episodes?: number
}

export interface PlaybookStep {
  id: string
  type: string
  target: string
  payload: Record<string, unknown>
  condition?: string | null
}

export interface ValidationSpec {
  test_command?: string | null
  pre_conditions: Record<string, unknown>[]
  post_conditions: Record<string, unknown>[]
}

export interface RollbackSpec {
  strategy?: string
  steps: Record<string, unknown>[]
}

export interface ObservabilitySpec {
  log_level?: string
  metrics: string[]
}

export interface Approval {
  id: string
  playbook_id: string
  status: string
  proposed_by: string
  created_at: string
}

export interface QueryRequest {
  query: string
  repo?: string
  top_k?: number
}

export interface QueryResult {
  id: string
  score: number
  payload: Record<string, unknown>
}

export interface ExecuteRequest {
  playbook_id: string
  context: Record<string, unknown>
}

export interface AgentTask {
  task: string
  repo_id?: string
  context?: Record<string, unknown>
}

export interface FeedbackSubmission {
  playbook_id: string
  execution_id: string
  success: boolean
  duration_ms?: number
  error?: string
}
