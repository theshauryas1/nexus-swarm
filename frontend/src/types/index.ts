// NexusSwarm — Shared TypeScript types  (Phase 7 — 28 agents)

export type AgentLevel   = 'orchestrator' | 'manager' | 'worker' | 'gateway'
export type AgentStatus  = 'idle' | 'in_progress' | 'active' | 'done' | 'error' | 'blocked'
export type PipelineName = 'planning' | 'engineering' | 'qa' | 'security' | 'devops' | 'reliability'
export type PipelineStatus = 'idle' | 'active' | 'blocked' | 'done' | 'failed'
export type EventType =
  | 'agent_action'
  | 'pipeline_update'
  | 'conflict'
  | 'escalation'
  | 'complete'
  | 'error'
  | 'health_check'
  | 'system'

export interface AgentEvent {
  event_id?:      string
  task_id?:       string | null
  event_type:     EventType
  agent_name:     string
  agent_level:    AgentLevel
  parent_manager?: string | null
  pipeline?:      PipelineName | null
  message:        string
  status:         AgentStatus
  payload?:       Record<string, unknown>
  timestamp:      string
}

export interface AgentRosterItem {
  agent_name:     string
  agent_level:    AgentLevel
  parent_manager?: string | null
  pipeline?:      PipelineName | null
  current_status: AgentStatus
  current_task?:  string | null
  model:          string
  provider:       string
}

export interface PipelineState {
  name:     PipelineName
  status:   PipelineStatus
  progress: number
}

export interface TaskSubmission {
  title:       string
  description: string
  priority:    number
}

export interface TaskResponse {
  task_id:    string
  status:     string
  message:    string
  created_at: string
}

export interface OutputItem {
  output_type:   string
  pipeline_name: string
  content?:      string
  file_path?:    string
  created_at:    string
}

export interface BenchmarkStats {
  total_benchmarks: number
  success_rate: number
  avg_score: number
  repair_success_rate: number
  security_pass_rate: number
  hallucination_pass_rate?: number
  hallucination_trap_defense_rate?: number
  adversarial_defense_rate?: number
  avg_cost?: number
  max_cost?: number
  total_tokens?: number
}

export interface BenchmarkResult {
  id: number
  benchmark_name: string
  task_id: string | null
  pass: boolean
  score: number
  execution_time: number
  created_at: string
  task_title?: string | null
  task_status?: string | null
  // Recovery metrics (v2)
  repair_iterations?: number
  failure_reason?: string | null
  root_cause?: string | null
  recovery_success?: boolean | null
  estimated_cost?: number
  total_tokens?: number
}

export interface LeaderboardData {
  stats: BenchmarkStats
  benchmarks: BenchmarkResult[]
}

