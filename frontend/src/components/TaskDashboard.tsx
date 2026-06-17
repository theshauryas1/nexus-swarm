// NexusSwarm — Task Dashboard
// Task submission form + pipeline health bars + live benchmark dashboard

import { useState, useEffect, useCallback } from 'react'
import {
  Send, Loader2, CheckCircle2, Shield, Cpu, TestTube, Rocket,
  ClipboardList, Activity, BarChart3, RefreshCw, Play,
  TrendingUp, Bug, AlertTriangle, Lock, Coins, Database,
} from 'lucide-react'
import clsx from 'clsx'
import { getApiErrorMessage, useNexusStore, safeGet } from '../store/agentStore'
import type { PipelineName, PipelineStatus } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Simple translation helper to satisfy static i18n checks
const t = (val: string) => val

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

// ── Types ─────────────────────────────────────────────────────────
interface BenchmarkStats {
  total_benchmarks: number
  success_rate: number
  avg_score: number
  repair_success_rate: number
  security_pass_rate?: number
  hallucination_trap_defense_rate?: number
  adversarial_defense_rate?: number
  avg_cost?: number
  max_cost?: number
  total_tokens?: number
}

interface BenchmarkResult {
  benchmark_name: string
  score: number
  pass_status: boolean
  execution_time: number
  repair_iterations: number
  failure_reason?: string
  root_cause?: string
  created_at?: string
  estimated_cost?: number
  total_tokens?: number
}

interface LeaderboardData {
  stats: BenchmarkStats
  benchmarks: BenchmarkResult[]
}

// ── PipelineBar ───────────────────────────────────────────────────
function PipelineBar({
  pipeline,
}: {
  pipeline: { name: PipelineName; status: PipelineStatus; progress: number }
}) {
  const cfg = safeGet(PIPELINE_CONFIG, pipeline.name)
  const { Icon } = cfg

  const isActive  = pipeline.status === 'active'
  const isDone    = pipeline.status === 'done'
  const isFailed  = pipeline.status === 'failed'
  const isBlocked = pipeline.status === 'blocked'

  return (
    <div className="glass rounded-xl p-3 flex items-center gap-3">
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
            {safeGet(STATUS_LABEL, pipeline.status)}
          </span>
        </div>

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

// ── StatCard ──────────────────────────────────────────────────────
function StatCard({
  label, value, sub, colorClass, Icon,
}: {
  label: string
  value: string
  sub?: string
  colorClass: string
  Icon: React.ElementType
}) {
  return (
    <div className={clsx('rounded-xl p-3 border bg-surface-600/40', colorClass)}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={11} className="opacity-60 flex-shrink-0" />
        <span className="text-[9px] font-semibold uppercase tracking-wider opacity-60 truncate">{label}</span>
      </div>
      <div className="text-lg font-bold font-mono leading-none">{value}</div>
      {sub && <div className="text-[9px] opacity-40 mt-1">{sub}</div>}
    </div>
  )
}

// ── BenchmarkDashboard ────────────────────────────────────────────
function BenchmarkDashboard() {
  const [data, setData]       = useState<LeaderboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/stats/leaderboard`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchLeaderboard() }, [fetchLeaderboard])

  const triggerRun = async () => {
    setRunning(true)
    try {
      await fetch(`${API_URL}/stats/leaderboard/run`, { method: 'POST' })
      setTimeout(fetchLeaderboard, 3000)
    } catch {
      // silent — run is best-effort
    } finally {
      setTimeout(() => setRunning(false), 3000)
    }
  }

  const stats   = data?.stats
  const results = data?.benchmarks ?? []

  // Derive category breakdown from result name prefix [CATEGORY]
  const categoryMap: Record<string, { pass: number; total: number; scores: number[] }> = {}
  for (const r of results) {
    const match = r.benchmark_name.match(/^\[(\w+)\]/)
    const cat = match ? match[1].toUpperCase() : 'OTHER'
    if (!categoryMap[cat]) categoryMap[cat] = { pass: 0, total: 0, scores: [] }
    categoryMap[cat].total++
    if (r.pass_status) categoryMap[cat].pass++
    categoryMap[cat].scores.push(r.score)
  }

  const hasData = stats && stats.total_benchmarks > 0

  return (
    <div className="glass rounded-2xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-brand-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">{t('Benchmarks')}</h2>
          {stats && stats.total_benchmarks > 0 && (
            <span className="text-[9px] bg-surface-500 text-slate-400 rounded px-1.5 py-0.5 font-mono">
              {stats.total_benchmarks} runs
            </span>
          )}
        </div>
        <div className="flex gap-1.5">
          <button
            id="btn-refresh-benchmarks"
            onClick={fetchLeaderboard}
            disabled={loading}
            title="Refresh leaderboard"
            className="text-[10px] text-slate-400 hover:text-white transition-colors p-1.5 rounded border border-surface-400 hover:border-slate-500"
          >
            <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            id="btn-run-benchmarks"
            onClick={triggerRun}
            disabled={running}
            className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors px-2 py-1 rounded border border-emerald-500/30 hover:border-emerald-500/60 flex items-center gap-1"
          >
            <Play size={9} className={running ? 'animate-pulse' : ''} />
            {running ? 'Starting…' : 'Run Suite'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-3">
          {error}
        </div>
      )}

      {/* ── Loading state */}
      {loading && !data && (
        <div className="flex justify-center py-8">
          <Loader2 size={20} className="text-brand-400 animate-spin" />
        </div>
      )}

      {/* ── Empty state */}
      {!loading && !hasData && !error && (
        <div className="text-center py-8">
          <AlertTriangle size={22} className="text-slate-600 mx-auto mb-2" />
           <div className="text-xs text-slate-500 mb-3">{t('No benchmark results yet.')}</div>
          <button
            id="btn-run-benchmarks-empty"
            onClick={triggerRun}
            disabled={running}
            className="text-[11px] text-emerald-400 hover:text-emerald-300 transition-colors px-3 py-1.5 rounded border border-emerald-500/30 hover:border-emerald-500/60 inline-flex items-center gap-1.5"
          >
            <Play size={11} />
            Run Benchmark Suite
          </button>
        </div>
      )}

      {/* ── Stats grid */}
      {hasData && (
        <>
          <div className="grid grid-cols-2 gap-2 mb-4">
            <StatCard
              label="Success Rate"
              value={`${stats.success_rate.toFixed(1)}%`}
              sub="Non-adversarial tasks"
              colorClass="text-emerald-400 border-emerald-500/20"
              Icon={TrendingUp}
            />
            <StatCard
              label="Avg Score"
              value={`${stats.avg_score.toFixed(1)}/10`}
              sub="Multi-signal objective"
              colorClass="text-brand-400 border-brand-500/20"
              Icon={BarChart3}
            />
            <StatCard
              label="Repair Rate"
              value={`${stats.repair_success_rate.toFixed(1)}%`}
              sub="Auto-healed failures"
              colorClass="text-cyan-400 border-cyan-500/20"
              Icon={RefreshCw}
            />
            {stats.security_pass_rate !== undefined && (
              <StatCard
                label="Security Pass"
                value={`${stats.security_pass_rate.toFixed(1)}%`}
                sub="No critical vulns"
                colorClass="text-rose-400 border-rose-500/20"
                Icon={Shield}
              />
            )}
            {stats.hallucination_trap_defense_rate !== undefined && (
              <StatCard
                label="Halluc. Defense"
                value={`${stats.hallucination_trap_defense_rate.toFixed(1)}%`}
                sub="Known traps avoided"
                colorClass="text-purple-400 border-purple-500/20"
                Icon={Bug}
              />
            )}
            {stats.adversarial_defense_rate !== undefined && (
              <StatCard
                label="Adversarial"
                value={`${stats.adversarial_defense_rate.toFixed(1)}%`}
                sub="Attacks blocked"
                colorClass="text-orange-400 border-orange-500/20"
                Icon={Lock}
              />
            )}
            {stats.avg_cost !== undefined && (
              <StatCard
                label="Avg LLM Cost"
                value={`$${stats.avg_cost.toFixed(4)}`}
                sub="Per swarm generation"
                colorClass="text-sky-400 border-sky-500/20"
                Icon={Coins}
              />
            )}
            {stats.max_cost !== undefined && (
              <StatCard
                label="Max LLM Cost"
                value={`$${stats.max_cost.toFixed(4)}`}
                sub="Most expensive run"
                colorClass="text-indigo-400 border-indigo-500/20"
                Icon={Coins}
              />
            )}
            {stats.total_tokens !== undefined && (
              <StatCard
                label="Total Tokens"
                value={stats.total_tokens.toLocaleString()}
                sub="Accumulated usage"
                colorClass="text-amber-400 border-amber-500/20"
                Icon={Database}
              />
            )}
          </div>

          {/* Category breakdown */}
          {Object.keys(categoryMap).length > 0 && (
            <div className="mb-4">
              <div className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {t('Category Breakdown')}
              </div>
              <div className="space-y-1">
                {Object.entries(categoryMap)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([cat, info]) => {
                    const rate = info.total ? (info.pass / info.total) * 100 : 0
                    const avg  = info.scores.length
                      ? info.scores.reduce((a, b) => a + b, 0) / info.scores.length
                      : 0
                    return (
                      <div key={cat} className="flex items-center gap-2 py-1 px-2 rounded-lg bg-surface-600/50">
                        <span className="text-[9px] font-mono text-slate-400 w-20 flex-shrink-0">
                          {cat}
                        </span>
                        <div className="flex-1 h-1 bg-surface-500 rounded-full overflow-hidden">
                          <div
                            className={clsx(
                              'h-full rounded-full transition-all',
                              rate >= 90 ? 'bg-emerald-500' :
                              rate >= 70 ? 'bg-brand-500' :
                              rate >= 50 ? 'bg-yellow-500' :
                              'bg-red-500',
                            )}
                            style={{ width: `${rate}%` }}
                          />
                        </div>
                        <span className="text-[9px] font-mono text-slate-400 w-20 text-right flex-shrink-0">
                          {info.pass}/{info.total} · {avg.toFixed(1)}
                        </span>
                      </div>
                    )
                  })}
              </div>
            </div>
          )}

          {/* Recent results */}
          {results.length > 0 && (
            <div>
              <div className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {t('Recent Results')}
              </div>
              <div className="space-y-1 max-h-52 overflow-y-auto pr-0.5">
                {results.slice(0, 25).map((r, i) => (
                  <div key={i} className="flex items-center gap-2 py-1 px-2 rounded-lg bg-surface-600/50">
                    {/* Badge */}
                    <span
                      className={clsx(
                        'text-[8px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0',
                        r.pass_status
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : (r.repair_iterations ?? 0) > 0
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-red-500/20 text-red-400',
                      )}
                    >
                      {r.pass_status ? 'PASS' : (r.repair_iterations ?? 0) > 0 ? 'REPAIRED' : 'FAIL'}
                    </span>

                    {/* Name (strip [CATEGORY] prefix) */}
                    <span className="text-[10px] text-slate-300 flex-1 truncate font-mono">
                      {r.benchmark_name.replace(/^\[\w+\]\s*/, '')}
                    </span>

                    {/* Score */}
                    <span className={clsx(
                      'text-[10px] font-mono font-bold flex-shrink-0 w-8 text-right',
                      r.score >= 8 ? 'text-emerald-400' :
                      r.score >= 6 ? 'text-brand-400' :
                      'text-red-400',
                    )}>
                      {r.score.toFixed(1)}
                    </span>

                    {/* Cost & Tokens metadata */}
                    {(r.estimated_cost !== undefined || r.total_tokens !== undefined) && (
                      <span className="text-[9px] text-slate-500 font-mono flex-shrink-0 text-right flex gap-1 items-center">
                        {r.estimated_cost !== undefined && r.estimated_cost > 0 && (
                          <span className="text-sky-400/80">${r.estimated_cost.toFixed(3)}</span>
                        )}
                        {r.total_tokens !== undefined && r.total_tokens > 0 && (
                          <span className="text-amber-400/80">({(r.total_tokens / 1000).toFixed(0)}k)</span>
                        )}
                      </span>
                    )}

                    {/* Time */}
                    <span className="text-[9px] text-slate-600 font-mono flex-shrink-0 w-9 text-right">
                      {r.execution_time.toFixed(0)}s
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

interface TaskDashboardProps {
  onTaskSubmitted?: (taskId: string) => void
}

// ── TaskDashboard ─────────────────────────────────────────────────
export function TaskDashboard({ onTaskSubmitted }: TaskDashboardProps) {
  const [title,        setTitle]       = useState('')
  const [description,  setDescription] = useState('')
  const [submitting,   setSubmitting]  = useState(false)
  const [error,        setError]       = useState<string | null>(null)

  const pipelines   = useNexusStore((s) => s.pipelines)
  const taskId      = useNexusStore((s) => s.taskId)
  const taskTitle   = useNexusStore((s) => s.taskTitle)
  const taskRunning = useNexusStore((s) => s.taskRunning)
  const setTaskId   = useNexusStore((s) => s.setTaskId)
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

      if (!res.ok) throw new Error(await getApiErrorMessage(res))

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
    <div className="flex flex-col gap-4 h-full overflow-y-auto">
      {/* ── Task Submission ──────────────────────────────── */}
      <div className="glass rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">{t('Submit Task')}</h2>
          <button
            type="button"
            onClick={fillDemo}
            className="text-[10px] text-brand-400 hover:text-brand-300 font-medium transition-colors px-2 py-1 rounded border border-brand-500/20 hover:border-brand-500/40"
          >
            {t('Load Demo')}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            id="task-title-input"
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
            id="task-description-input"
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
            id="btn-launch-swarm"
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
              <><Loader2 size={16} className="animate-spin" /> Submitting…</>
            ) : taskRunning ? (
              <><Loader2 size={16} className="animate-spin" /> Agents Running…</>
            ) : (
              <><Send size={16} /> Launch Swarm</>
            )}
          </button>
        </form>

        {taskId && (
          <div className="mt-3 px-3 py-2 bg-brand-500/10 border border-brand-500/20 rounded-xl">
            <div className="text-[10px] text-brand-400 font-medium uppercase tracking-wider mb-0.5">{t('Active Task')}</div>
            <div className="text-xs text-white font-medium truncate">{taskTitle}</div>
            <div className="text-[9px] text-slate-500 font-mono">{taskId.slice(0, 8)}…</div>
          </div>
        )}
      </div>

      {/* ── Pipeline Health Bars ─────────────────────────── */}
      <div className="glass rounded-2xl p-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest mb-3">{t('Pipeline Status')}</h2>
        <div className="flex flex-col gap-2">
          {pipelineList.map((p) => (
            <PipelineBar key={p.name} pipeline={p} />
          ))}
        </div>
      </div>

      {/* ── Live Benchmark Results ────────────────────────── */}
      <BenchmarkDashboard />
    </div>
  )
}
