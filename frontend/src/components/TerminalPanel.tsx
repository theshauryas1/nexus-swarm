// NexusSwarm — TerminalPanel (VS Code integrated terminal)
// Shows execution logs and pipeline events in terminal style

import { useEffect, useRef, useState } from 'react'
import { Terminal, ChevronRight, X } from 'lucide-react'
import clsx from 'clsx'
import { useNexusStore } from '../store/agentStore'

const LEVEL_COLOR: Record<string, string> = {
  orchestrator: 'text-violet-400',
  manager:      'text-blue-400',
  worker:       'text-slate-400',
  gateway:      'text-amber-400',
}

const STATUS_COLOR: Record<string, string> = {
  idle:        'text-slate-600',
  active:      'text-cyan-400',
  in_progress: 'text-cyan-400',
  working:     'text-cyan-400',
  done:        'text-emerald-400',
  error:       'text-red-400',
  blocked:     'text-amber-400',
}

const STATUS_PREFIX: Record<string, string> = {
  idle:        '○',
  active:      '◉',
  in_progress: '◉',
  working:     '◉',
  done:        '✓',
  error:       '✗',
  blocked:     '⊘',
}

// Pipeline status compact view
function PipelineBar({ name, status, progress }: { name: string; status: string; progress: number }) {
  const barColor =
    status === 'done'    ? 'bg-emerald-500' :
    status === 'active'  ? 'bg-indigo-500' :
    status === 'failed'  ? 'bg-red-500' :
    status === 'blocked' ? 'bg-amber-500' : 'bg-surface-600'

  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className={clsx(
        'w-16 flex-shrink-0 capitalize font-mono',
        status === 'done'    ? 'text-emerald-400' :
        status === 'active'  ? 'text-indigo-400' :
        status === 'failed'  ? 'text-red-400' :
        status === 'blocked' ? 'text-amber-400' : 'text-slate-600',
      )}>
        {name}
      </span>
      <div className="flex-1 h-1 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="w-8 text-right text-slate-600 font-mono">{progress}%</span>
    </div>
  )
}

type TermTab = 'terminal' | 'pipelines' | 'problems'

export function TerminalPanel() {
  const events    = useNexusStore((s) => s.events)
  const pipelines = useNexusStore((s) => s.pipelines)
  const connected = useNexusStore((s) => s.connected)
  const taskTitle = useNexusStore((s) => s.taskTitle)

  const [tab, setTab]       = useState<TermTab>('terminal')
  const scrollRef           = useRef<HTMLDivElement>(null)
  const [cleared, setCleared] = useState(0)

  const errorCount    = events.filter(e => e.status === 'error').length
  const visibleEvents = events.slice(0, events.length - cleared)

  // Auto-scroll terminal
  useEffect(() => {
    if (tab === 'terminal' && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events, tab])

  const tabs: { id: TermTab; label: string; badge?: number }[] = [
    { id: 'terminal',  label: 'TERMINAL' },
    { id: 'pipelines', label: 'PIPELINES' },
    { id: 'problems',  label: 'PROBLEMS', badge: errorCount || undefined },
  ]

  return (
    <div className="flex flex-col h-full bg-ide-terminal border-t border-ide-border overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center bg-ide-tabbar border-b border-ide-border flex-shrink-0">
        <div className="flex items-center">
          {tabs.map(({ id, label, badge }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold tracking-wider transition-all border-b-2',
                tab === id
                  ? 'border-indigo-500 text-white bg-ide-editor'
                  : 'border-transparent text-slate-500 hover:text-slate-300',
              )}
            >
              {label}
              {badge !== undefined && (
                <span className="text-[9px] bg-red-500/20 text-red-400 px-1 rounded-sm">{badge}</span>
              )}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1 pr-2">
          {/* Connection dot */}
          <span className={clsx('w-1.5 h-1.5 rounded-full', connected ? 'bg-emerald-400' : 'bg-red-400')} />
          <span className={clsx('text-[9px]', connected ? 'text-emerald-500' : 'text-red-500')}>
            {connected ? 'connected' : 'offline'}
          </span>
          {tab === 'terminal' && (
            <button
              onClick={() => setCleared(events.length)}
              className="ml-2 p-0.5 text-slate-600 hover:text-slate-300 transition-colors"
              title="Clear terminal"
            >
              <X size={11} />
            </button>
          )}
        </div>
      </div>

      {/* Terminal tab */}
      {tab === 'terminal' && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed"
        >
          {/* Prompt header */}
          <div className="text-slate-600 mb-2 select-none">
            <span className="text-indigo-400">nexusswarm</span>
            <span className="text-slate-600">@ide</span>
            <span className="text-slate-700"> — </span>
            <span className="text-slate-500">{taskTitle ?? 'No active task'}</span>
          </div>

          {visibleEvents.length === 0 ? (
            <div className="flex items-center gap-1 text-slate-700">
              <ChevronRight size={11} className="text-indigo-500" />
              <span className="animate-pulse">_</span>
            </div>
          ) : (
            visibleEvents.map((ev, i) => (
              <div key={ev.event_id ?? i} className="flex items-start gap-2 hover:bg-white/3 px-1 rounded group">
                {/* Timestamp */}
                <span className="text-slate-700 flex-shrink-0 select-none">
                  {new Date(ev.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>

                {/* Status symbol */}
                <span className={clsx('flex-shrink-0', STATUS_COLOR[ev.status] ?? 'text-slate-500')}>
                  {STATUS_PREFIX[ev.status] ?? '○'}
                </span>

                {/* Agent name */}
                <span className={clsx('flex-shrink-0', LEVEL_COLOR[ev.agent_level] ?? 'text-slate-400')}>
                  [{ev.agent_name}]
                </span>

                {/* Message */}
                <span className={clsx(
                  'flex-1 break-words',
                  ev.status === 'error'   ? 'text-red-300' :
                  ev.status === 'done'    ? 'text-slate-300' :
                  ev.event_type === 'complete' ? 'text-emerald-300 font-semibold' :
                  'text-slate-500',
                )}>
                  {ev.message}
                </span>
              </div>
            ))
          )}

          {/* Blinking cursor at end */}
          <div className="flex items-center gap-1 mt-1 text-slate-700">
            <ChevronRight size={11} className="text-indigo-600" />
            <span className="animate-[blink_1s_step-end_infinite]">█</span>
          </div>
        </div>
      )}

      {/* Pipelines tab */}
      {tab === 'pipelines' && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex flex-col gap-2.5">
            {Object.values(pipelines).map(p => (
              <PipelineBar key={p.name} name={p.name} status={p.status} progress={p.progress} />
            ))}
          </div>

          {/* Stats row */}
          <div className="mt-4 pt-3 border-t border-ide-border grid grid-cols-3 gap-3 text-center">
            {[
              { label: 'Running', value: Object.values(pipelines).filter(p => p.status === 'active').length, color: 'text-indigo-400' },
              { label: 'Done',    value: Object.values(pipelines).filter(p => p.status === 'done').length,   color: 'text-emerald-400' },
              { label: 'Total',   value: Object.values(pipelines).length,                                    color: 'text-slate-400' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className={clsx('text-xl font-bold font-mono', color)}>{value}</div>
                <div className="text-[9px] text-slate-600 uppercase tracking-wider">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Problems tab */}
      {tab === 'problems' && (
        <div className="flex-1 overflow-y-auto p-3 font-mono text-[11px]">
          {errorCount === 0 ? (
            <div className="flex items-center gap-2 text-emerald-500 py-2">
              <span>✓</span>
              <span>No problems detected</span>
            </div>
          ) : (
            events.filter(e => e.status === 'error').map((ev, i) => (
              <div key={i} className="flex items-start gap-2 text-red-300 py-1 border-b border-ide-border/50">
                <span className="text-red-500">✗</span>
                <span className="text-slate-600">[{ev.agent_name}]</span>
                <span>{ev.message}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
