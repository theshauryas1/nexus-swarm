// NexusSwarm — Output Panel  
// Shows agent roster, live LLM outputs, and pipeline stats

import { useState } from 'react'
import { FileText, Users, Activity, Copy, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { useNexusStore } from '../store/agentStore'
import type { AgentLevel } from '../types'

const LEVEL_COLORS: Record<AgentLevel, { text: string; bg: string; border: string }> = {
  orchestrator: { text: 'text-violet-300', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
  manager:      { text: 'text-blue-300',   bg: 'bg-blue-500/10',   border: 'border-blue-500/30'   },
  worker:       { text: 'text-slate-300',  bg: 'bg-slate-500/10',  border: 'border-slate-500/30'  },
  gateway:      { text: 'text-amber-300',  bg: 'bg-amber-500/10',  border: 'border-amber-500/30'  },
}

const STATUS_DOT: Record<string, string> = {
  idle:        'bg-slate-600',
  in_progress: 'bg-indigo-400 animate-pulse',
  active:      'bg-indigo-400 animate-pulse',
  working:     'bg-indigo-400 animate-pulse',
  done:        'bg-emerald-400',
  error:       'bg-red-400',
  blocked:     'bg-amber-400',
}

const STATUS_EMOJI: Record<string, string> = {
  idle: '⬜', in_progress: '🔵', active: '🔵', done: '✅', error: '❌', blocked: '🚫',
}

const AGENT_ICON: Record<string, string> = {
  HeadOrchestrator:        '👑',
  PlanningManager:         '🗂️',
  EngineeringManager:      '⚙️',
  QAManager:               '🧪',
  SecurityManager:         '🛡️',
  DevOpsManager:           '🚀',
  ReliabilityManager:      '📊',
  RequirementAgent:        '📋',
  RiskAnalyzer:            '⚠️',
  BackendAgent:            '🐍',
  APIAgent:                '📡',
  FrontendAgent:           '⚛️',
  TestAgent:               '🧬',
  ReviewerAgent:           '👁️',
  ScannerAgent:            '🔍',
  DeployAgent:             '🐳',
  DiagnosticsAgent:        '🩺',
  RepairAgent:             '🔧',
  HallucinationValidator:  '🧠',
  SemanticValidator:       '📝',
  ContractValidator:       '📜',
  KnowledgeMemoryAgent:    '💾',
  HumanApprovalGateway:    '🔐',
}

type Tab = 'roster' | 'output' | 'stats'

export function OutputPanel() {
  const [tab, setTab]           = useState<Tab>('roster')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [copied, setCopied]     = useState<string | null>(null)

  const roster        = useNexusStore((s) => s.roster)
  const events        = useNexusStore((s) => s.events)
  const agentStatuses = useNexusStore((s) => s.agentStatuses)
  const pipelines     = useNexusStore((s) => s.pipelines)
  const outputItems   = useNexusStore((s) => s.outputItems)
  const taskId        = useNexusStore((s) => s.taskId)
  const taskRunning   = useNexusStore((s) => s.taskRunning)

  const stats = {
    totalEvents:   events.length,
    activeAgents:  Object.values(agentStatuses).filter(s => s === 'in_progress' || s === 'active').length,
    doneAgents:    Object.values(agentStatuses).filter(s => s === 'done').length,
    donePipelines: Object.values(pipelines).filter(p => p.status === 'done').length,
  }

  const tabs: { id: Tab; label: string; Icon: React.ElementType; badge?: number }[] = [
    { id: 'roster', label: 'Agents',   Icon: Users,     badge: roster.length > 0 ? roster.length : undefined },
    { id: 'output', label: 'Outputs',  Icon: FileText,  badge: outputItems.length > 0 ? outputItems.length : undefined },
    { id: 'stats',  label: 'Stats',    Icon: Activity },
  ]

  const copyToClipboard = (key: string, text: string) => {
    navigator.clipboard.writeText(text).catch(() => {})
    setCopied(key)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <div className="glass rounded-2xl flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-surface-500 flex-shrink-0">
        {tabs.map(({ id, label, Icon, badge }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'flex items-center gap-1 px-2 py-2.5 text-[10px] font-semibold transition-all border-b-2 flex-1 justify-center relative',
              tab === id
                ? 'border-brand-500 text-brand-400 bg-brand-500/5'
                : 'border-transparent text-slate-500 hover:text-slate-300',
            )}
          >
            <Icon size={11} />
            {label}
            {badge !== undefined && (
              <span className="ml-0.5 text-[8px] font-bold bg-brand-500/20 text-brand-300 px-1 py-0.5 rounded-full min-w-[14px] text-center">
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">

        {/* ── Agent Roster Tab ─────────────────────────────── */}
        {tab === 'roster' && (
          <div className="p-2 flex flex-col gap-0.5">
            {roster.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
                <div className="text-2xl animate-pulse">⬡</div>
                <div className="text-[10px] text-slate-600">Connecting to agent roster...</div>
              </div>
            ) : (
              roster.map((agent) => {
                const clr    = LEVEL_COLORS[agent.agent_level] ?? LEVEL_COLORS.worker
                const status = agentStatuses[agent.agent_name] ?? agent.current_status ?? 'idle'
                const icon   = AGENT_ICON[agent.agent_name] ?? '🤖'
                return (
                  <div
                    key={agent.agent_name}
                    className={clsx(
                      'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-all',
                      status === 'in_progress' || status === 'active' ? 'bg-brand-500/10 border border-brand-500/20' :
                      status === 'done'  ? 'bg-emerald-500/5' :
                      status === 'error' ? 'bg-red-500/5' :
                      'bg-surface-700/40 hover:bg-surface-600/40',
                    )}
                  >
                    <span className="text-sm flex-shrink-0">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-semibold text-white truncate leading-tight">{agent.agent_name}</div>
                      <div className="text-[8px] text-slate-600 font-mono truncate">{agent.model?.split('/').pop() ?? '—'}</div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <span className={clsx('w-1.5 h-1.5 rounded-full', STATUS_DOT[status] ?? 'bg-slate-600')} />
                      <span className={clsx('text-[7px] font-bold uppercase px-1 py-0.5 rounded border', clr.text, clr.bg, clr.border)}>
                        {agent.agent_level?.slice(0, 3)}
                      </span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* ── Outputs Tab ───────────────────────────────────── */}
        {tab === 'output' && (
          <div className="p-2 flex flex-col gap-1.5">
            {outputItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 gap-3 text-center">
                <div className="text-3xl">{taskRunning ? '⚙️' : '📭'}</div>
                <div className="text-[10px] text-slate-500 leading-relaxed px-2">
                  {taskId
                    ? taskRunning
                      ? 'Pipeline running...\nOutputs appear here as agents complete.'
                      : 'No outputs captured yet.'
                    : 'Submit a task to see agent outputs here.'}
                </div>
              </div>
            ) : (
              outputItems.map((item) => {
                const icon    = AGENT_ICON[item.agent] ?? '📄'
                const isOpen  = expanded === item.agent
                const preview = item.content.slice(0, 100).replace(/\n/g, ' ')
                const isCopied = copied === item.agent
                return (
                  <div key={item.agent} className="bg-surface-700/60 rounded-xl border border-surface-500/50 overflow-hidden">
                    <button
                      onClick={() => setExpanded(isOpen ? null : item.agent)}
                      className="w-full flex items-center justify-between px-2.5 py-2 text-left hover:bg-surface-600/40 transition-colors"
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-sm">{icon}</span>
                        <span className="text-[9px] font-bold text-slate-300 truncate">{item.agent}</span>
                        <span className="text-[8px] text-slate-600 bg-surface-600 px-1 rounded font-mono flex-shrink-0">
                          {item.pipeline}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className="text-[8px] text-slate-600">{item.content.length}c</span>
                        {isOpen ? <ChevronDown size={10} className="text-slate-500" /> : <ChevronRight size={10} className="text-slate-500" />}
                      </div>
                    </button>
                    {!isOpen && (
                      <div className="px-2.5 pb-2 text-[8px] text-slate-600 font-mono leading-relaxed line-clamp-2">
                        {preview}…
                      </div>
                    )}
                    {isOpen && (
                      <div className="relative border-t border-surface-600">
                        <button
                          onClick={() => copyToClipboard(item.agent, item.content)}
                          className="absolute top-1.5 right-1.5 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-600 hover:bg-surface-500 text-slate-400 hover:text-white transition-colors z-10 text-[8px]"
                        >
                          {isCopied ? <><CheckCircle2 size={9} className="text-emerald-400" /> Copied!</> : <><Copy size={9} /> Copy</>}
                        </button>
                        <pre className="px-2.5 py-2 pt-6 text-[8px] text-slate-300 font-mono leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap break-words">
                          {item.content}
                        </pre>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* ── Stats Tab ─────────────────────────────────────── */}
        {tab === 'stats' && (
          <div className="p-3 flex flex-col gap-2">
            {[
              { label: 'Total Events',    value: stats.totalEvents,               color: 'text-brand-400'   },
              { label: 'Active Agents',   value: stats.activeAgents,              color: 'text-blue-400'    },
              { label: 'Done Agents',     value: stats.doneAgents,                color: 'text-emerald-400' },
              { label: 'Pipelines Done',  value: `${stats.donePipelines}/6`,      color: 'text-violet-400'  },
              { label: 'Output Artifacts',value: outputItems.length,              color: 'text-amber-400'   },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between px-3 py-2 bg-surface-700 rounded-xl">
                <span className="text-[10px] text-slate-400">{label}</span>
                <span className={clsx('text-base font-bold font-mono', color)}>{value}</span>
              </div>
            ))}

            {/* Pipeline breakdown */}
            <div className="mt-1 bg-surface-700/50 rounded-xl overflow-hidden">
              <div className="px-3 py-1.5 border-b border-surface-600">
                <div className="text-[9px] text-slate-600 uppercase tracking-widest font-semibold">Pipelines</div>
              </div>
              {Object.values(pipelines).map((p) => (
                <div key={p.name} className="flex items-center gap-2 px-3 py-1.5 border-b border-surface-600 last:border-0">
                  <span className="text-[9px] text-slate-400 capitalize w-16 flex-shrink-0">{p.name}</span>
                  <div className="flex-1 bg-surface-600 rounded-full h-1">
                    <div
                      className={clsx('h-1 rounded-full transition-all duration-500',
                        p.status === 'done'    ? 'bg-emerald-400' :
                        p.status === 'active'  ? 'bg-brand-400' :
                        p.status === 'failed'  ? 'bg-red-400' :
                        p.status === 'blocked' ? 'bg-amber-400' : 'bg-surface-500',
                      )}
                      style={{ width: `${p.progress}%` }}
                    />
                  </div>
                  <span className={clsx(
                    'text-[7px] font-bold uppercase px-1 py-0.5 rounded flex-shrink-0',
                    p.status === 'done'    ? 'text-emerald-400 bg-emerald-500/10' :
                    p.status === 'active'  ? 'text-brand-400 bg-brand-500/10' :
                    p.status === 'failed'  ? 'text-red-400 bg-red-500/10' :
                    p.status === 'blocked' ? 'text-amber-400 bg-amber-500/10' :
                    'text-slate-600 bg-surface-600',
                  )}>
                    {p.status}
                  </span>
                </div>
              ))}
            </div>

            {/* Roster count */}
            <div className="px-3 py-2 bg-surface-700/50 rounded-xl flex items-center justify-between">
              <span className="text-[10px] text-slate-500">Registered Agents</span>
              <span className="text-xs font-bold text-emerald-400">{roster.length}</span>
            </div>

            {/* Status emoji key */}
            <div className="px-3 py-2 bg-surface-700/50 rounded-xl">
              <div className="text-[8px] text-slate-600 uppercase tracking-widest mb-1.5">Status Key</div>
              <div className="grid grid-cols-2 gap-0.5">
                {[
                  { emoji: '⬜', label: 'Idle' },
                  { emoji: '🔵', label: 'Active' },
                  { emoji: '✅', label: 'Done' },
                  { emoji: '❌', label: 'Error' },
                  { emoji: '🚫', label: 'Blocked' },
                  { emoji: '🔐', label: 'Gateway' },
                ].map(({ emoji, label }) => (
                  <div key={label} className="flex items-center gap-1 text-[8px] text-slate-500">
                    <span>{emoji}</span>{label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
