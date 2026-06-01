// NexusSwarm — Live Agent Log Feed
// Real-time scrolling log of all agent actions

import { useEffect, useRef } from 'react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'
import { useNexusStore, safeGet } from '../store/agentStore'
import type { AgentEvent, AgentLevel, AgentStatus } from '../types'

// ── Level badge styles ────────────────────────────────────────────
const LEVEL_STYLE: Record<AgentLevel, string> = {
  orchestrator: 'text-violet-400 bg-violet-500/10 border-violet-500/30',
  manager:      'text-blue-400   bg-blue-500/10   border-blue-500/30',
  worker:       'text-slate-400  bg-slate-500/10  border-slate-500/30',
  gateway:      'text-amber-400  bg-amber-500/10  border-amber-500/30',
}

// ── Status dot ────────────────────────────────────────────────────
const STATUS_DOT: Record<AgentStatus, string> = {
  idle:        'bg-slate-600',
  in_progress: 'bg-brand-400 animate-pulse',
  active:      'bg-brand-400 animate-pulse',
  done:        'bg-emerald-400',
  error:       'bg-red-400',
  blocked:     'bg-orange-400',
}

// ── Event type border accent ──────────────────────────────────────
const EVENT_BORDER: Partial<Record<string, string>> = {
  complete:        'border-l-emerald-500',
  error:           'border-l-red-500',
  conflict:        'border-l-orange-500',
  escalation:      'border-l-yellow-500',
  pipeline_update: 'border-l-blue-500',
  system:          'border-l-violet-500',
  agent_action:    'border-l-surface-400',
  health_check:    'border-l-cyan-500',
}

// ── LogEntry ──────────────────────────────────────────────────────
function LogEntry({ event }: { event: AgentEvent }) {
  const borderColor = safeGet(EVENT_BORDER, event.event_type) ?? 'border-l-surface-400'

  return (
    <div
      className={clsx(
        'log-entry border-l-2 pl-3 py-2 rounded-r-lg',
        'bg-surface-700/50 hover:bg-surface-600/50 transition-colors',
        borderColor,
      )}
    >
      <div className="flex items-center gap-2 flex-wrap">
        {/* Status dot */}
        <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', safeGet(STATUS_DOT, event.status) ?? 'bg-slate-600')} />

        {/* Agent level badge */}
        <span className={clsx('text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border tracking-wider', safeGet(LEVEL_STYLE, event.agent_level))}>
          {event.agent_level.slice(0, 4)}
        </span>

        {/* Agent name */}
        <span className="text-xs font-semibold text-white truncate max-w-[120px]">{event.agent_name}</span>

        {/* Pipeline tag */}
        {event.pipeline && (
          <span className="text-[9px] text-slate-500 bg-surface-600 px-1.5 py-0.5 rounded border border-surface-400 font-mono">
            {event.pipeline}
          </span>
        )}

        {/* Time */}
        <span className="text-[9px] text-slate-600 ml-auto flex-shrink-0">
          {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
        </span>
      </div>

      {/* Message */}
      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{event.message}</p>
    </div>
  )
}

// ── LiveLog ───────────────────────────────────────────────────────
export function LiveLog() {
  const events      = useNexusStore((s) => s.events)
  const connected   = useNexusStore((s) => s.connected)
  const scrollRef   = useRef<HTMLDivElement>(null)
  const atBottomRef = useRef(true)

  // Auto-scroll only if user is at bottom
  useEffect(() => {
    const el = scrollRef.current
    if (!el || !atBottomRef.current) return
    el.scrollTop = 0  // newest is at top
  }, [events])

  const activeCount = events.filter((e) => e.status === 'in_progress').length

  return (
    <div className="glass rounded-2xl flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-500 flex-shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">Live Log</h2>
          {activeCount > 0 && (
            <span className="text-[9px] font-bold text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded px-1.5 py-0.5">
              {activeCount} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={clsx(
              'w-2 h-2 rounded-full',
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400',
            )}
          />
          <span className={clsx('text-[10px] font-medium', connected ? 'text-emerald-400' : 'text-red-400')}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
          <span className="text-[9px] text-slate-600 ml-2">{events.length} events</span>
        </div>
      </div>

      {/* Log entries (newest at top) */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-1.5"
        onScroll={(e) => {
          const el = e.currentTarget
          atBottomRef.current = el.scrollTop < 40
        }}
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-8">
            <div className="w-12 h-12 rounded-full bg-surface-600 flex items-center justify-center text-2xl">
              ⬡
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-400">Awaiting Task</div>
              <div className="text-xs text-slate-600 mt-1">Submit a task to see agents activate in real-time</div>
            </div>
          </div>
        ) : (
          events.map((ev) => <LogEntry key={ev.event_id ?? ev.timestamp + ev.agent_name} event={ev} />)
        )}
      </div>
    </div>
  )
}
