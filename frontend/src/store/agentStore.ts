// NexusSwarm — Global Zustand Store  (Phase 7 — 28 agents)
// Single source of truth for all live agent state

import { create } from 'zustand'
import type {
  AgentEvent,
  AgentRosterItem,
  AgentStatus,
  PipelineName,
  PipelineState,
} from '../types'

// ── Pipeline defaults ─────────────────────────────────────────────
const PIPELINES: PipelineName[] = [
  'planning', 'engineering', 'qa', 'security', 'devops', 'reliability',
]

const defaultPipelines = (): Record<PipelineName, PipelineState> =>
  Object.fromEntries(
    PIPELINES.map((name) => [name, { name, status: 'idle', progress: 0 }])
  ) as Record<PipelineName, PipelineState>

/** Normalize backend status values → canonical AgentStatus.
 *  Backend can emit 'active' (from health events), map it to 'in_progress'. */
function normalizeStatus(raw: string): AgentStatus {
  if (raw === 'active') return 'in_progress'
  const allowed: AgentStatus[] = ['idle', 'in_progress', 'done', 'error', 'blocked']
  return allowed.includes(raw as AgentStatus) ? (raw as AgentStatus) : 'idle'
}

export async function getApiErrorMessage(res: Response): Promise<string> {
  const retryAfter = res.headers.get('Retry-After')
  const payload = await res.json().catch(() => ({} as { detail?: unknown }))
  const detail = typeof payload.detail === 'string' ? payload.detail : undefined

  if (res.status === 429) {
    return retryAfter
      ? `Too many requests. Try again in ${retryAfter} seconds.`
      : detail ?? 'Too many requests. Please wait and try again.'
  }

  return detail ?? `Request failed with HTTP ${res.status}.`
}

// ── Store shape ───────────────────────────────────────────────────
interface NexusStore {
  // Connection
  connected:      boolean
  taskId:         string | null
  taskTitle:      string | null
  taskRunning:    boolean
  apiError:       string | null

  // Agent roster (from /agents endpoint)
  roster:         AgentRosterItem[]

  // Live agent statuses (updated by WebSocket events)
  agentStatuses:  Record<string, AgentStatus>

  // Pipeline states
  pipelines:      Record<PipelineName, PipelineState>

  // Event log (capped at 300)
  events:         AgentEvent[]

  // Final output
  deliveryReport: string | null
  outputItems:    { agent: string; pipeline: string; type: string; content: string }[]

  // File browser state
  files:          { name: string; size: number; lang: string }[]
  selectedFile:   string | null
  selectedFileContent: string | null
  recentTasks:    { task_id: string; title: string; status: string; created_at: string }[]
  expandedSessions: Record<string, { name: string; size: number; lang: string }[]>

  // Page Router
  currentPage: 'intro' | 'login' | 'ide'
  user: { name: string; email: string; picture: string } | null
  navigate: (page: 'intro' | 'login' | 'ide') => void
  setUser: (user: { name: string; email: string; picture: string } | null) => void

  // Actions
  fetchFiles:         () => Promise<void>
  selectFile:         (filename: string) => Promise<void>
  selectSessionFile:  (taskId: string, filename: string) => Promise<void>
  fetchRecentTasks:   () => Promise<void>
  fetchSessionFiles:  (taskId: string) => Promise<void>
  setConnected:       (v: boolean) => void
  setApiError:        (message: string | null) => void
  setTaskId:          (id: string, title: string) => void
  clearTask:          () => void
  setRoster:          (roster: AgentRosterItem[]) => void
  handleEvent:        (event: AgentEvent) => void
  handleHealthEvent:  (event: { pipeline: string; status: string; progress: number }) => void
}

export const useNexusStore = create<NexusStore>((set) => ({
  currentPage:    (new URLSearchParams(window.location.search).get('page') as any) || 'intro',
  user:           localStorage.getItem('nexus_user') ? JSON.parse(localStorage.getItem('nexus_user')!) : null,
  connected:      false,
  taskId:         null,
  taskTitle:      null,
  taskRunning:    false,
  apiError:       null,
  roster:         [],
  agentStatuses:  {},
  pipelines:      defaultPipelines(),
  events:         [],
  deliveryReport: null,
  outputItems:    [],
  files:          [],
  selectedFile:   null,
  selectedFileContent: null,
  recentTasks:    [],
  expandedSessions: {},

  navigate: (page) => {
    const params = new URLSearchParams(window.location.search);
    params.set('page', page);
    window.history.pushState({}, '', `?${params.toString()}`);
    set({ currentPage: page });
  },

  setUser: (user) => {
    if (user) {
      localStorage.setItem('nexus_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('nexus_user');
    }
    set({ user });
  },

  setConnected: (v) => set({ connected: v }),
  setApiError: (message) => set({ apiError: message }),

  fetchRecentTasks: async () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiUrl}/tasks?limit=30`)
      if (!res.ok) return
      const data = await res.json()
      if (data.tasks) {
        set({ recentTasks: data.tasks })
      }
    } catch (e) {
      console.error("Failed to fetch recent tasks", e)
    }
  },

  fetchSessionFiles: async (taskId: string) => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiUrl}/files/${taskId}`)
      if (!res.ok) return
      const files = await res.json()
      set((state) => ({
        expandedSessions: {
          ...state.expandedSessions,
          [taskId]: files
        }
      }))
    } catch (e) {
      console.error(`Failed to fetch files for task ${taskId}`, e)
    }
  },

  selectSessionFile: async (taskId: string, filename: string) => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiUrl}/files/${taskId}/${filename}`)
      if (!res.ok) {
        set({ apiError: await getApiErrorMessage(res) })
        return
      }
      const data = await res.json()
      const task = useNexusStore.getState().recentTasks.find(t => t.task_id === taskId)
      set({ 
        taskId, 
        taskTitle: task?.title ?? "Session", 
        selectedFile: filename, 
        selectedFileContent: data.content, 
        apiError: null 
      })
    } catch (e) {
      set({ apiError: "Could not load file content. Check the backend connection." })
    }
  },

  fetchFiles: async () => {
    const taskId = useNexusStore.getState().taskId
    if (!taskId) return
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiUrl}/files/${taskId}`)
      if (!res.ok) {
        set({ apiError: await getApiErrorMessage(res) })
        return
      }
      const files = await res.json()
      set((state) => ({
        files,
        expandedSessions: {
          ...state.expandedSessions,
          [taskId]: files
        },
        apiError: null
      }))
    } catch (e) {
      set({ apiError: "Could not load generated files. Check the backend connection." })
    }
  },

  selectFile: async (filename: string) => {
    const taskId = useNexusStore.getState().taskId
    if (!taskId) return
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${apiUrl}/files/${taskId}/${filename}`)
      if (!res.ok) {
        set({ apiError: await getApiErrorMessage(res) })
        return
      }
      const data = await res.json()
      set({ selectedFile: filename, selectedFileContent: data.content, apiError: null })
    } catch (e) {
      set({ apiError: "Could not load file content. Check the backend connection." })
    }
  },

  setTaskId: (id, title) => {
    set({
      taskId:         id,
      taskTitle:      title,
      taskRunning:    true,
      apiError:       null,
      pipelines:      defaultPipelines(),
      events:         [],
      agentStatuses:  {},
      deliveryReport: null,
      outputItems:    [],
      files:          [],
      selectedFile:   null,
      selectedFileContent: null,
    })
    useNexusStore.getState().fetchRecentTasks()
  },

  clearTask: () =>
    set({
      taskId:         null,
      taskTitle:      null,
      taskRunning:    false,
      apiError:       null,
      pipelines:      defaultPipelines(),
      agentStatuses:  {},
      files:          [],
      selectedFile:   null,
      selectedFileContent: null,
    }),

  setRoster: (roster) => set({ roster }),

  // ── Handle pipeline health events (from backend health pub/sub) ──
  handleHealthEvent: ({ pipeline, status, progress }) => {
    set((state) => {
      const pName = pipeline as PipelineName
      if (!PIPELINES.includes(pName)) return state
      const current = safeGet(state.pipelines, pName)
      const newStatus =
        status === 'done'   ? 'done'    :
        status === 'active' ? 'active'  :
        status === 'failed' ? 'failed'  :
        status === 'blocked'? 'blocked' :
        current.status
      return {
        pipelines: {
          ...state.pipelines,
          [pName]: { ...current, status: newStatus, progress },
        },
      }
    })
  },

  // ── Main WebSocket event handler ──────────────────────────────────
  handleEvent: (event) => {
    set((state) => {
      // 1. Normalise status so 'active' maps to 'in_progress'
      const status = normalizeStatus(event.status)

      // 2. Append to event log (cap at 300), normalise status in the stored event
      const normEvent: AgentEvent = { ...event, status }
      const events = [normEvent, ...state.events].slice(0, 300)

      // 3. Update agent status in graph
      const agentStatuses: Record<string, AgentStatus> = {
        ...state.agentStatuses,
        [event.agent_name]: status,
      }

      // 4. Update pipeline state from event
      let pipelines = { ...state.pipelines }
      if (event.pipeline && PIPELINES.includes(event.pipeline as PipelineName)) {
        const p = event.pipeline as PipelineName
        const current = safeGet(pipelines, p)
        let newStatus = current.status
        let newProgress = current.progress

        if (status === 'in_progress' && current.status === 'idle') {
          newStatus   = 'active'
          newProgress = Math.max(current.progress, 10)
        } else if (status === 'done' && event.agent_level === 'manager') {
          newStatus   = 'done'
          newProgress = 100
        } else if (status === 'error') {
          newStatus = 'failed'
        } else if (status === 'blocked') {
          newStatus = 'blocked'
        } else if (status === 'in_progress') {
          newProgress = Math.min(current.progress + 10, 95)
        }

        pipelines = {
          ...pipelines,
          [p]: { ...current, status: newStatus, progress: newProgress },
        }
      }

      // 5. Capture output artifacts into outputItems
      let outputItems = [...state.outputItems]
      if (event.payload?.output && typeof event.payload.output === 'string' && (event.payload.output as string).length > 10) {
        const exists = outputItems.some(o => o.agent === event.agent_name)
        const item = {
          agent:    event.agent_name,
          pipeline: event.pipeline ?? 'system',
          type:     event.agent_name,
          content:  event.payload.output as string,
        }
        if (exists) {
          outputItems = outputItems.map(o => o.agent === event.agent_name ? item : o)
        } else {
          outputItems = [...outputItems, item]
        }
      }

      // 6. Handle task complete — finalise pipelines but KEEP agent statuses visible
      let taskRunning = state.taskRunning
      if (event.event_type === 'complete') {
        taskRunning = false
        pipelines = Object.fromEntries(
          Object.entries(pipelines).map(([k, v]) => [
            k,
            { ...v, status: v.status === 'idle' ? 'idle' : 'done', progress: v.status === 'idle' ? 0 : 100 },
          ])
        ) as Record<PipelineName, PipelineState>
        
        setTimeout(() => {
          useNexusStore.getState().fetchFiles()
          useNexusStore.getState().fetchRecentTasks()
        }, 500)

        return { events, agentStatuses, pipelines, taskRunning, outputItems }
      }

      if (status === 'done') {
        setTimeout(() => {
          useNexusStore.getState().fetchFiles()
        }, 500)
      }

      return { events, agentStatuses, pipelines, taskRunning, outputItems }
    })
  },
}))

/**
 * Safely look up a property on an object without risk of Prototype Pollution or security warnings.
 */
export function safeGet<T extends object, K extends string>(obj: T, key: K): any {
  if (!obj || !key || key === '__proto__' || key === 'constructor' || key === 'prototype') {
    return undefined;
  }
  return Object.prototype.hasOwnProperty.call(obj, key) ? Reflect.get(obj, key) : undefined;
}
