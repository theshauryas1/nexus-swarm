// NexusSwarm — Task History Sidebar
// Shows all submitted tasks with status badges

import { useState, useEffect } from 'react'
import { Clock, CheckCircle2, XCircle, Loader2, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { getApiErrorMessage, safeGet } from '../store/agentStore'

interface TaskSummary {
  task_id: string
  title: string
  status: string
  created_at: string
  priority: number
}

const STATUS_CONFIG: Record<string, { color: string; icon: typeof Clock }> = {
  pending:    { color: 'text-yellow-400', icon: Clock },
  running:    { color: 'text-brand-400',  icon: Loader2 },
  complete:   { color: 'text-emerald-400', icon: CheckCircle2 },
  failed:     { color: 'text-red-400',     icon: XCircle },
}

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

interface Props {
  onSelect?: (taskId: string) => void
  selectedId?: string
}

export function TaskHistory({ onSelect, selectedId }: Props) {
  const [tasks, setTasks] = useState<TaskSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  const fetchTasks = async () => {
    try {
      const r = await fetch(`${API}/tasks?limit=20`)
      if (!r.ok) {
        setError(await getApiErrorMessage(r))
        return
      }
      const data = await r.json()
      setTasks(data.tasks ?? [])
      setError(null)
    } catch {
      setError('Could not load task history. Check the backend connection.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(fetchTasks, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="glass rounded-2xl flex flex-col overflow-hidden h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-500 flex-shrink-0">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest">Task History</h2>
        <span className="text-[10px] text-slate-500 font-mono">{tasks.length} tasks</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-20">
            <Loader2 size={16} className="text-slate-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="px-3 py-3 text-xs text-red-400 bg-red-500/10 border-b border-red-500/20">
            {error}
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-600">No tasks yet</div>
        ) : (
          tasks.map((task) => {
            const cfg   = safeGet(STATUS_CONFIG, task.status) ?? STATUS_CONFIG.pending
            const Icon  = cfg.icon
            const isSelected = task.task_id === selectedId

            return (
              <button
                key={task.task_id}
                onClick={() => onSelect?.(task.task_id)}
                className={clsx(
                  'w-full text-left px-3 py-2.5 border-b border-surface-600 last:border-0',
                  'flex items-start gap-2.5 transition-colors group',
                  isSelected ? 'bg-brand-500/10' : 'hover:bg-surface-700',
                )}
              >
                <Icon
                  size={14}
                  className={clsx(
                    cfg.color, 'flex-shrink-0 mt-0.5',
                    task.status === 'running' ? 'animate-spin' : '',
                  )}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-white truncate leading-tight">
                    {task.title}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={clsx('text-[9px] font-bold uppercase', cfg.color)}>
                      {task.status}
                    </span>
                    <span className="text-[9px] text-slate-600">{formatAge(task.created_at)}</span>
                  </div>
                </div>
                <ChevronRight size={12} className="text-slate-600 group-hover:text-slate-400 flex-shrink-0 mt-0.5" />
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
