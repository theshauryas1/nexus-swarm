// NexusSwarm — Delivery Report Modal
// Renders the final executive delivery report in a beautiful full-screen overlay

import { useEffect, useState } from 'react'
import { X, Download, CheckCircle2, FileText, Loader2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { safeGet } from '../store/agentStore'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Backend sends outputs as a dict: { "BackendAgent": "...", "TestAgent": "..." }
interface TaskDetail {
  task_id:    string
  title:      string
  status:     string        // 'running' | 'complete' | 'failed'
  created_at: string
  pipelines?: Array<{ name: string; status: string; progress: number }>
  outputs:    Record<string, string> | Array<{ output_type: string; pipeline_name: string; content: string }>
}

interface Props {
  taskId:   string
  onClose:  () => void
}

const PIPELINE_COLORS: Record<string, string> = {
  planning:    'text-violet-400 bg-violet-500/10 border-violet-500/30',
  engineering: 'text-blue-400   bg-blue-500/10   border-blue-500/30',
  qa:          'text-cyan-400   bg-cyan-500/10   border-cyan-500/30',
  security:    'text-orange-400 bg-orange-500/10 border-orange-500/30',
  devops:      'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  reliability: 'text-teal-400   bg-teal-500/10   border-teal-500/30',
}

const AGENT_ICON: Record<string, string> = {
  HeadOrchestrator: '👑', PlanningManager: '🗂️', EngineeringManager: '⚙️',
  QAManager: '🧪', SecurityManager: '🛡️', DevOpsManager: '🚀',
  RequirementAgent: '📋', RiskAnalyzer: '⚠️', BackendAgent: '🐍',
  APIAgent: '📡', FrontendAgent: '⚛️', TestAgent: '🧬',
  ScannerAgent: '🔍', DeployAgent: '🐳', DiagnosticsAgent: '🩺',
  RepairAgent: '🔧', HallucinationValidator: '🧠', SemanticValidator: '📝',
  ContractValidator: '📜', KnowledgeMemoryAgent: '💾',
}

function ContentBlock({ content }: { content: string }) {
  const lines = content.split('\n')

  const renderStrongText = (line: string) => {
    const parts = line.split(/(\*\*.+?\*\*)/g)
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>
      }
      return <span key={index}>{part}</span>
    })
  }

  return (
    <div className="text-xs text-slate-300 leading-relaxed space-y-0.5">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) return <h3 key={i} className="text-sm font-bold text-brand-300 mt-3 mb-1">{line.slice(4)}</h3>
        if (line.startsWith('## '))  return <h2 key={i} className="text-base font-bold text-white mt-4 mb-1">{line.slice(3)}</h2>
        if (line.startsWith('# '))   return <h1 key={i} className="text-lg font-extrabold text-brand-200 mt-4 mb-2">{line.slice(2)}</h1>
        if (line.startsWith('```'))  return <div key={i} className="border-t border-surface-500 my-2" />
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-brand-400 flex-shrink-0">•</span>
              <span>{line.slice(2)}</span>
            </div>
          )
        }
        if (line.match(/^\d+\. /)) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-slate-500 flex-shrink-0 font-mono text-[10px]">{line.match(/^\d+/)![0]}.</span>
              <span>{line.replace(/^\d+\. /, '')}</span>
            </div>
          )
        }
        if (line.startsWith('|')) {
          return (
            <div key={i} className="text-[10px] font-mono text-slate-400 border-b border-surface-600 pb-0.5">
              {line}
            </div>
          )
        }
        if (line.trim() === '' || line === '---') return <div key={i} className="h-1" />
        return <p key={i}>{renderStrongText(line)}</p>
      })}
    </div>
  )
}

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`
}

export function DeliveryReport({ taskId, onClose }: Props) {
  const [detail,  setDetail]  = useState<TaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [tab,     setTab]     = useState<string>('summary')
  const [polling, setPolling] = useState(true)

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        // Try /status/ first (alias we added), fallback to /task/
        let r = await fetch(`${API}/status/${taskId}`)
        if (!r.ok) r = await fetch(`${API}/task/${taskId}`)
        if (!r.ok) { setError(`Task not found (${r.status})`); return }
        const data: TaskDetail = await r.json()
        setDetail(data)
        // Stop polling once complete or failed
        if (data.status === 'complete' || data.status === 'failed') setPolling(false)
      } catch (e) {
        setError('Could not connect to backend')
      } finally {
        setLoading(false)
      }
    }

    fetchDetail()
    if (!polling) return
    const iv = setInterval(fetchDetail, 3000)
    return () => clearInterval(iv)
  }, [taskId, polling])

  // Normalise outputs: dict or array → array of {agent, content}
  const outputEntries: Array<{ agent: string; content: string }> = (() => {
    if (!detail?.outputs) return []
    if (Array.isArray(detail.outputs)) {
      return detail.outputs.map(o => ({ agent: o.output_type ?? o.pipeline_name, content: o.content ?? '' }))
    }
    // Dict format: { "BackendAgent": "code...", "TestAgent": "tests..." }
    return Object.entries(detail.outputs)
      .filter(([, v]) => typeof v === 'string' && v.length > 0)
      .map(([k, v]) => ({ agent: k, content: v as string }))
  })()

  const pipelines = detail?.pipelines ?? []

  // Build tab list
  const outputTabs = outputEntries.length > 0
    ? ['summary', ...outputEntries.map(e => e.agent)]
    : ['summary']

  const downloadReport = () => {
    const sections = outputEntries.map(o => `# ${o.agent}\n\n${o.content}`).join('\n\n---\n\n')
    const blob = new Blob([sections || 'No output yet'], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `nexusswarm-${taskId.slice(0, 8)}.md`; a.click()
    URL.revokeObjectURL(url)
  }

  const isComplete = detail?.status === 'complete'
  const isFailed   = detail?.status === 'failed'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-5xl h-[88vh] glass rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-surface-400">

        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-500 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'w-9 h-9 rounded-xl flex items-center justify-center text-lg',
              isComplete ? 'bg-emerald-500/15 border border-emerald-500/30' :
              isFailed   ? 'bg-red-500/15 border border-red-500/30' :
              'bg-brand-500/15 border border-brand-500/30',
            )}>
              {isComplete ? '📦' : isFailed ? '💥' : '⚙️'}
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Delivery Report</h2>
              <p className="text-[10px] text-slate-500 font-mono">{taskId.slice(0, 20)}…</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Status badge */}
            <div className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border',
              isComplete ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' :
              isFailed   ? 'text-red-400 border-red-500/30 bg-red-500/10' :
              'text-brand-400 border-brand-500/30 bg-brand-500/10',
            )}>
              {!isComplete && !isFailed && <Loader2 size={11} className="animate-spin" />}
              {isComplete && <CheckCircle2 size={11} />}
              {detail?.status ?? 'loading'}
            </div>

            {/* Live indicator */}
            {polling && !isComplete && !isFailed && (
              <div className="flex items-center gap-1 text-[10px] text-slate-500">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
                Live
              </div>
            )}

            <button
              onClick={() => { setLoading(true); setPolling(true) }}
              className="p-2 rounded-lg hover:bg-surface-600 text-slate-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw size={13} />
            </button>
            <button
              onClick={downloadReport}
              disabled={outputEntries.length === 0}
              className="p-2 rounded-lg hover:bg-surface-600 text-slate-400 hover:text-white transition-colors disabled:opacity-30"
              title="Download as Markdown"
            >
              <Download size={13} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-surface-600 text-slate-400 hover:text-white transition-colors"
            >
              <X size={13} />
            </button>
          </div>
        </div>

        {/* ── Task meta ──────────────────────────────────────────── */}
        <div className="px-6 py-3 border-b border-surface-600 flex-shrink-0 bg-surface-800/40">
          <div className="flex items-start justify-between gap-4">
            <h3 className="text-sm font-bold text-white leading-tight flex-1">
              {detail?.title ?? <span className="text-slate-600">Loading…</span>}
            </h3>
            {detail?.created_at && (
              <span className="text-[10px] text-slate-500 flex-shrink-0 font-mono">
                {formatAge(detail.created_at)}
              </span>
            )}
          </div>

          {/* Pipeline status chips */}
          {pipelines.length > 0 && (
            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
              {pipelines.map(p => (
                <div
                  key={p.name}
                  className={clsx(
                    'flex items-center gap-1 px-2 py-0.5 rounded-lg border text-[9px] font-bold uppercase',
                    safeGet(PIPELINE_COLORS, p.name) ?? 'text-slate-400 bg-surface-600 border-surface-500',
                  )}
                >
                  <span>{p.name}</span>
                  <span className="opacity-50">{p.progress}%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Content tabs ───────────────────────────────────────── */}
        <div className="flex border-b border-surface-500 flex-shrink-0 overflow-x-auto scrollbar-hide">
          {outputTabs.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold whitespace-nowrap border-b-2 transition-all flex-shrink-0',
                tab === t
                  ? 'border-brand-500 text-brand-400 bg-brand-500/5'
                  : 'border-transparent text-slate-500 hover:text-slate-300',
              )}
            >
              {t === 'summary' ? '📊 Summary' : `${safeGet(AGENT_ICON, t) ?? '📄'} ${t}`}
            </button>
          ))}
        </div>

        {/* ── Content area ───────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && !detail ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
              <Loader2 size={24} className="animate-spin text-brand-400" />
              <span className="text-sm">Loading task data…</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <div className="text-3xl">⚠️</div>
              <div className="text-sm text-red-400">{error}</div>
              <div className="text-xs text-slate-600 font-mono">Task ID: {taskId}</div>
            </div>
          ) : tab === 'summary' ? (
            <div className="space-y-5">
              {/* Pipeline table */}
              {pipelines.length > 0 ? (
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Pipeline Summary</h4>
                  <div className="overflow-hidden rounded-xl border border-surface-500">
                    <table className="w-full text-xs">
                      <thead className="bg-surface-700">
                        <tr>
                          {['Pipeline', 'Status', 'Progress'].map(h => (
                            <th key={h} className="px-4 py-2.5 text-left text-slate-400 font-semibold text-[10px] uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {pipelines.map((p, i) => (
                          <tr key={p.name} className={clsx('border-t border-surface-600', i % 2 === 0 ? 'bg-surface-700/30' : '')}>
                            <td className="px-4 py-2.5 font-medium text-white capitalize">{p.name}</td>
                            <td className="px-4 py-2.5">
                              <span className={clsx(
                                'text-[9px] font-bold uppercase px-1.5 py-0.5 rounded',
                                p.status === 'done'    ? 'text-emerald-400 bg-emerald-500/10' :
                                p.status === 'active'  ? 'text-brand-400 bg-brand-500/10' :
                                p.status === 'failed'  ? 'text-red-400 bg-red-500/10' :
                                p.status === 'blocked' ? 'text-amber-400 bg-amber-500/10' :
                                'text-slate-500 bg-surface-600',
                              )}>
                                {p.status}
                              </span>
                            </td>
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-2">
                                <div className="w-24 bg-surface-600 rounded-full h-1.5">
                                  <div
                                    className={clsx('h-1.5 rounded-full transition-all', p.status === 'done' ? 'bg-emerald-400' : 'bg-brand-400')}
                                    style={{ width: `${p.progress}%` }}
                                  />
                                </div>
                                <span className="text-slate-500 font-mono text-[9px]">{p.progress}%</span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 gap-2 text-center">
                  <Loader2 size={20} className="animate-spin text-brand-400" />
                  <div className="text-sm text-slate-500">Pipeline data loading…</div>
                </div>
              )}

              {/* Output count */}
              <div className={clsx(
                'flex items-center gap-3 px-4 py-3 rounded-xl border',
                outputEntries.length > 0
                  ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
                  : 'bg-surface-700 border-surface-500 text-slate-500',
              )}>
                <FileText size={14} />
                <span className="text-xs font-medium">
                  {outputEntries.length > 0
                    ? `${outputEntries.length} output artifacts generated — click tabs above to view each`
                    : 'Outputs will appear here as agents complete their work'}
                </span>
              </div>

              {/* Output preview grid */}
              {outputEntries.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Output Artifacts</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {outputEntries.map(o => (
                      <button
                        key={o.agent}
                        onClick={() => setTab(o.agent)}
                        className="text-left px-3 py-2.5 bg-surface-700 hover:bg-surface-600 rounded-xl border border-surface-500 hover:border-brand-500/40 transition-all group"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-base">{safeGet(AGENT_ICON, o.agent) ?? '📄'}</span>
                          <span className="text-xs font-semibold text-white group-hover:text-brand-300 transition-colors">{o.agent}</span>
                        </div>
                        <div className="text-[9px] text-slate-600 font-mono line-clamp-2 leading-relaxed">
                          {o.content.slice(0, 80)}…
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Individual agent output tab
            (() => {
              const output = outputEntries.find(o => o.agent === tab)
              if (!output) return (
                <div className="text-center py-10 text-xs text-slate-600">No output for {tab}</div>
              )
              return (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 pb-2 border-b border-surface-600">
                    <span className="text-xl">{safeGet(AGENT_ICON, output.agent) ?? '📄'}</span>
                    <h4 className="text-sm font-bold text-white">{output.agent}</h4>
                    <span className="ml-auto text-[9px] text-slate-600 font-mono">{output.content.length} chars</span>
                  </div>
                  <div className="bg-surface-800/60 rounded-xl border border-surface-500 p-5">
                    <ContentBlock content={output.content} />
                  </div>
                </div>
              )
            })()
          )}
        </div>
      </div>
    </div>
  )
}
