// NexusSwarm — Task Dashboard
// Task submission form + pipeline health bars

import { useState } from 'react'
import { Send, Loader2, CheckCircle2, Shield, Cpu, TestTube, Rocket, ClipboardList, Activity } from 'lucide-react'
import clsx from 'clsx'
import { getApiErrorMessage, useNexusStore } from '../store/agentStore'
import type { PipelineName, PipelineStatus } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const DEMO_TASK = {
  title: 'Build a secure REST API for a task management system',
  description:
    'Include JWT authentication, CRUD operations for tasks (create, read, update, delete, assign), ' +
    'PostgreSQL database with async SQLAlchemy, pytest test suite, and Docker deployment configuration.',
}

// ── Pipeline config ───────────────────────────────────────────────
const PIPELINE_CONFIG: Record<PipelineName, { label: string; Icon: React.ElementType; color: string }> = {
  planning:    { label: 'Planning',     Icon: ClipboardList, color: 'from-purple-500 to-purple-700' },
  engineering: { label: 'Engineering',  Icon: Cpu,           color: 'from-blue-500 to-blue-700' },
  qa:          { label: 'QA',           Icon: TestTube,      color: 'from-cyan-500 to-cyan-700' },
  security:    { label: 'Security',     Icon: Shield,        color: 'from-rose-500 to-rose-700' },
  devops:      { label: 'DevOps',       Icon: Rocket,        color: 'from-emerald-500 to-emerald-700' },
  reliability: { label: 'Reliability',  Icon: Activity,      color: 'from-teal-500 to-teal-700' },
}

const STATUS_LABEL: Record<PipelineStatus, string> = {
  idle:    'Waiting',
  active:  'Running',
  done:    'Complete',
  failed:  'Failed',
  blocked: 'Blocked',
}

// ── PipelineBar ───────────────────────────────────────────────────
function PipelineBar({
  pipeline,
}: {
  pipeline: { name: PipelineName; status: PipelineStatus; progress: number }
}) {
  const cfg = PIPELINE_CONFIG[pipeline.name]
  const { Icon } = cfg

  const isActive  = pipeline.status === 'active'
  const isDone    = pipeline.status === 'done'
  const isFailed  = pipeline.status === 'failed'
  const isBlocked = pipeline.status === 'blocked'

  return (
    <div className="glass rounded-xl p-3 flex items-center gap-3">
      {/* Icon */}
      <div
        className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          isDone    ? 'bg-emerald-500/20 text-emerald-400' :
          isFailed  ? 'bg-red-500/20 text-red-400' :
          isBlocked ? 'bg-orange-500/20 text-orange-400' :
          isActive  ? 'bg-brand-500/20 text-brand-400' :
          'bg-surface-500 text-slate-500',
        )}
      >
        {isDone ? <CheckCircle2 size={16} /> : <Icon size={16} />}
      </div>

      {/* Label + progress */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-slate-300">{cfg.label}</span>
          <span
            className={clsx(
              'text-[10px] font-medium uppercase tracking-wider',
              isDone    ? 'text-emerald-400' :
              isFailed  ? 'text-red-400' :
              isBlocked ? 'text-orange-400' :
              isActive  ? 'text-brand-400' :
              'text-slate-600',
            )}
          >
            {STATUS_LABEL[pipeline.status]}
          </span>
        </div>

        {/* Progress bar track */}
        <div className="h-1.5 bg-surface-500 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-700',
              isDone    ? 'bg-emerald-500' :
              isFailed  ? 'bg-red-500' :
              isBlocked ? 'bg-orange-500' :
              isActive  ? 'progress-shimmer' :
              'bg-transparent',
            )}
            style={{ width: `${pipeline.progress}%` }}
          />
        </div>
      </div>

      {/* Percentage */}
      <div
        className={clsx(
          'text-xs font-mono font-semibold w-10 text-right',
          isDone ? 'text-emerald-400' : 'text-slate-500',
        )}
      >
        {pipeline.progress}%
      </div>
    </div>
  )
}

interface TaskDashboardProps {
  onTaskSubmitted?: (taskId: string) => void
}

// ── TaskDashboard ─────────────────────────────────────────────────
export function TaskDashboard({ onTaskSubmitted }: TaskDashboardProps) {
  const [title,       setTitle]       = useState('')
  const [description, setDescription] = useState('')
  const [submitting,  setSubmitting]  = useState(false)
  const [error,       setError]       = useState<string | null>(null)

  const pipelines  = useNexusStore((s) => s.pipelines)
  const taskId     = useNexusStore((s) => s.taskId)
  const taskTitle  = useNexusStore((s) => s.taskTitle)
  const taskRunning = useNexusStore((s) => s.taskRunning)
  const setTaskId  = useNexusStore((s) => s.setTaskId)
  const setApiError = useNexusStore((s) => s.setApiError)

  const fillDemo = () => {
    setTitle(DEMO_TASK.title)
    setDescription(DEMO_TASK.description)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/submit-task`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ title: title.trim(), description: description.trim(), priority: 1 }),
      })

      if (!res.ok) {
        throw new Error(await getApiErrorMessage(res))
      }

      const data = await res.json()
      setTaskId(data.task_id, title.trim())
      setApiError(null)
      setTitle('')
      setDescription('')
      onTaskSubmitted?.(data.task_id)
    } catch (err) {
      const message = (err as Error).message
      setError(message)
      setApiError(message)
    } finally {
      setSubmitting(false)
    }
  }

  const pipelineList = Object.values(pipelines)

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* ── Task Submission ─────────────────────────────────── */}
      <div className="glass rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">Submit Task</h2>
          <button
            type="button"
            onClick={fillDemo}
            className="text-[10px] text-brand-400 hover:text-brand-300 font-medium transition-colors px-2 py-1 rounded border border-brand-500/20 hover:border-brand-500/40"
          >
            Load Demo
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Task title..."
            disabled={submitting || taskRunning}
            className={clsx(
              'w-full bg-surface-600 border border-surface-400 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500',
              'focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/40 transition-all',
              (submitting || taskRunning) && 'opacity-50 cursor-not-allowed',
            )}
          />

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Task description (optional)..."
            rows={3}
            disabled={submitting || taskRunning}
            className={clsx(
              'w-full bg-surface-600 border border-surface-400 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500 resize-none',
              'focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/40 transition-all',
              (submitting || taskRunning) && 'opacity-50 cursor-not-allowed',
            )}
          />

          {error && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || taskRunning || !title.trim()}
            className={clsx(
              'flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-semibold text-sm transition-all',
              'bg-gradient-to-r from-brand-600 to-brand-500 text-white',
              'hover:from-brand-500 hover:to-brand-400 hover:shadow-lg hover:shadow-brand-500/25',
              'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none',
            )}
          >
            {submitting ? (
              <><Loader2 size={16} className="animate-spin" /> Submitting...</>
            ) : taskRunning ? (
              <><Loader2 size={16} className="animate-spin" /> Agents Running...</>
            ) : (
              <><Send size={16} /> Launch Swarm</>
            )}
          </button>
        </form>

        {/* Active task badge */}
        {taskId && (
          <div className="mt-3 px-3 py-2 bg-brand-500/10 border border-brand-500/20 rounded-xl">
            <div className="text-[10px] text-brand-400 font-medium uppercase tracking-wider mb-0.5">Active Task</div>
            <div className="text-xs text-white font-medium truncate">{taskTitle}</div>
            <div className="text-[9px] text-slate-500 font-mono">{taskId.slice(0, 8)}...</div>
          </div>
        )}
      </div>

      {/* ── Pipeline Health Bars ─────────────────────────────── */}
      <div className="glass rounded-2xl p-4 flex-1">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest mb-3">Pipeline Status</h2>
        <div className="flex flex-col gap-2">
          {pipelineList.map((p) => (
            <PipelineBar key={p.name} pipeline={p} />
          ))}
        </div>
      </div>
    </div>
  )
}
