// NexusSwarm — WebSocket hook  (Phase 7)
// Connects to FastAPI /ws/agents and streams live agent events + health events

import { useEffect, useRef, useCallback } from 'react'
import { getApiErrorMessage, useNexusStore } from '../store/agentStore'
import type { AgentEvent } from '../types'

const WS_URL    = (import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000') + '/ws/agents'
const RECONNECT = 2500

/**
 * Normalise the backend WebSocket payload into the AgentEvent shape
 * the store expects.
 *
 * Backend sends:  { type, agent, status, message, output, model, level, ts, task_id }
 * Frontend wants: { agent_name, agent_level, status, message, timestamp, event_type, ... }
 */
function normaliseEvent(raw: Record<string, unknown>): AgentEvent {
  return {
    event_type:  (raw.event_type as AgentEvent['event_type']) ?? 'agent_action',
    agent_name:  (raw.agent_name as string) ?? (raw.agent as string) ?? '',
    agent_level: (raw.agent_level as AgentEvent['agent_level']) ?? (raw.level as AgentEvent['agent_level']) ?? 'worker',
    status:      (raw.status as AgentEvent['status']) ?? 'idle',
    message:     (raw.message as string) ?? '',
    timestamp:   (raw.timestamp as string) ?? (raw.ts as string) ?? new Date().toISOString(),
    task_id:     (raw.task_id as string) ?? null,
    pipeline:    (raw.pipeline as AgentEvent['pipeline']) ?? null,
    payload:     raw.output ? { output: raw.output, model: raw.model } : undefined,
  }
}

export function useAgentStream() {
  const wsRef        = useRef<WebSocket | null>(null)
  const retryRef     = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const setConnected       = useNexusStore((s) => s.setConnected)
  const handleEvent        = useNexusStore((s) => s.handleEvent)
  const handleHealthEvent  = useNexusStore((s) => s.handleHealthEvent)
  const setRoster          = useNexusStore((s) => s.setRoster)
  const setApiError        = useNexusStore((s) => s.setApiError)

  const fetchRoster = useCallback(async () => {
    try {
      const api = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const res = await fetch(`${api}/agents`)
      if (!res.ok) {
        setApiError(await getApiErrorMessage(res))
        return
      }
      const data = await res.json()
      // Normalise roster: backend sends { id, name, model, provider, level, status }
      // Store expects AgentRosterItem: { agent_name, agent_level, current_status, model, provider }
      const normalised = (data.agents ?? []).map((a: Record<string, unknown>) => ({
        agent_name:    a.agent_name ?? a.name ?? a.id ?? '',
        agent_level:   a.agent_level ?? a.level ?? 'worker',
        current_status: a.current_status ?? a.status ?? 'idle',
        model:         a.model ?? '',
        provider:      a.provider ?? 'NVIDIA NIM',
        pipeline:      a.pipeline ?? null,
        parent_manager: a.parent_manager ?? null,
      }))
      setRoster(normalised)
      setApiError(null)
    } catch {
      setApiError("Could not load agent roster. Check the backend connection.")
    }
  }, [setRoster, setApiError])

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (unmountedRef.current) { ws.close(); return }
      setConnected(true)
      fetchRoster()
    }

    ws.onmessage = (msg) => {
      try {
        const raw = JSON.parse(msg.data) as Record<string, unknown>

        // Health / pipeline progress events
        if (raw.event_type === 'health' || (raw.pipeline && raw.progress !== undefined && !raw.agent_name && !raw.agent)) {
          handleHealthEvent({
            pipeline: raw.pipeline as string,
            status:   (raw.status as string) ?? 'active',
            progress: (raw.progress as number) ?? 0,
          })
          return
        }

        // Standard agent events — normalise field names before passing to store
        const agentField = raw.agent_name ?? raw.agent
        if (agentField) {
          handleEvent(normaliseEvent(raw))
        }
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      if (unmountedRef.current) return
      setConnected(false)
      retryRef.current = setTimeout(connect, RECONNECT)
    }

    ws.onerror = () => { ws.close() }
  }, [setConnected, handleEvent, handleHealthEvent, fetchRoster])

  useEffect(() => {
    unmountedRef.current = false
    connect()
    return () => {
      unmountedRef.current = true
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected: useNexusStore((s) => s.connected) }
}
