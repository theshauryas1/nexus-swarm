// NexusSwarm — AgentTree (VS Code Explorer sidebar)
// Hierarchical collapsible tree of all 28 agents grouped by pipeline

import { useState } from 'react'
import {
  ChevronDown, ChevronRight, Circle,
  Crown, Layers, Cpu, FlaskConical,
  Shield, Rocket, Activity, Hexagon
} from 'lucide-react'
import clsx from 'clsx'
import { useNexusStore } from '../store/agentStore'

// ── Tree structure ────────────────────────────────────────────────
interface TreeAgent {
  name: string
  icon: string
}

interface TreeGroup {
  id:      string
  label:   string
  icon:    React.ElementType
  color:   string
  agents:  TreeAgent[]
}

const TREE: TreeGroup[] = [
  {
    id: 'orchestrator', label: 'Head Orchestrator', icon: Crown, color: 'text-violet-400',
    agents: [{ name: 'HeadOrchestrator', icon: '👑' }],
  },
  {
    id: 'planning', label: 'Planning', icon: Layers, color: 'text-purple-400',
    agents: [
      { name: 'PlanningManager',   icon: '🗂️' },
      { name: 'RequirementAgent',  icon: '📋' },
      { name: 'RiskAnalyzer',      icon: '⚠️' },
    ],
  },
  {
    id: 'engineering', label: 'Engineering', icon: Cpu, color: 'text-blue-400',
    agents: [
      { name: 'EngineeringManager', icon: '⚙️' },
      { name: 'BackendAgent',       icon: '🐍' },
      { name: 'APIAgent',           icon: '📡' },
      { name: 'FrontendAgent',      icon: '⚛️' },
    ],
  },
  {
    id: 'qa', label: 'Quality Assurance', icon: FlaskConical, color: 'text-cyan-400',
    agents: [
      { name: 'QAManager',          icon: '🧪' },
      { name: 'TestAgent',          icon: '🧬' },
      { name: 'DiagnosticsAgent',   icon: '🩺' },
      { name: 'RepairAgent',        icon: '🔧' },
    ],
  },
  {
    id: 'security', label: 'Security', icon: Shield, color: 'text-orange-400',
    agents: [
      { name: 'SecurityManager',        icon: '🛡️' },
      { name: 'ScannerAgent',           icon: '🔍' },
      { name: 'HumanApprovalGateway',   icon: '🔐' },
      { name: 'HallucinationValidator', icon: '🧠' },
      { name: 'SemanticValidator',      icon: '📝' },
      { name: 'ContractValidator',      icon: '📜' },
    ],
  },
  {
    id: 'devops', label: 'DevOps', icon: Rocket, color: 'text-emerald-400',
    agents: [
      { name: 'DevOpsManager',  icon: '🚀' },
      { name: 'DeployAgent',    icon: '🐳' },
    ],
  },
  {
    id: 'reliability', label: 'Reliability', icon: Activity, color: 'text-teal-400',
    agents: [
      { name: 'ReliabilityManager',   icon: '📊' },
      { name: 'KnowledgeMemoryAgent', icon: '💾' },
    ],
  },
]

const STATUS_CLASS: Record<string, string> = {
  idle:        'text-slate-600',
  in_progress: 'text-indigo-400',
  active:      'text-indigo-400',
  done:        'text-emerald-400',
  error:       'text-red-400',
  blocked:     'text-amber-400',
}

const STATUS_DOT: Record<string, string> = {
  idle:        'bg-slate-700',
  in_progress: 'bg-indigo-400 animate-pulse',
  active:      'bg-indigo-400 animate-pulse',
  done:        'bg-emerald-400',
  error:       'bg-red-400',
  blocked:     'bg-amber-400',
}

interface Props {
  selectedAgent: string | null
  onSelectAgent: (name: string) => void
}

export function AgentTree({ selectedAgent, onSelectAgent }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const agentStatuses = useNexusStore((s) => s.agentStatuses)
  const taskRunning   = useNexusStore((s) => s.taskRunning)

  const toggle = (id: string) =>
    setCollapsed(prev => ({ ...prev, [id]: !prev[id] }))

  // Count active agents per group
  const groupActive = (agents: TreeAgent[]) =>
    agents.filter(a => {
      const s = agentStatuses[a.name]
      return s === 'in_progress' || s === 'active'
    }).length

  return (
    <div className="flex flex-col h-full overflow-hidden bg-ide-sidebar">
      {/* Panel header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-ide-border flex-shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
          Agent Explorer
        </span>
        {taskRunning && (
          <span className="flex items-center gap-1 text-[9px] text-indigo-400">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {TREE.map((group) => {
          const { id, label, icon: Icon, color, agents } = group
          const isOpen    = !collapsed[id]
          const active    = groupActive(agents)

          return (
            <div key={id}>
              {/* Group header */}
              <button
                onClick={() => toggle(id)}
                className="w-full flex items-center gap-1.5 px-2 py-1 hover:bg-ide-hover group transition-colors text-left"
              >
                <span className="text-slate-600 flex-shrink-0 w-3">
                  {isOpen ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                </span>
                <Icon size={12} className={clsx('flex-shrink-0', color)} />
                <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex-1 truncate">
                  {label}
                </span>
                {active > 0 && (
                  <span className="text-[8px] font-bold text-indigo-400 bg-indigo-500/15 px-1 rounded-sm">
                    {active}
                  </span>
                )}
              </button>

              {/* Agents */}
              {isOpen && agents.map((agent) => {
                const status   = agentStatuses[agent.name] ?? 'idle'
                const isActive = status === 'in_progress' || status === 'active'
                const isDone   = status === 'done'
                const isSelected = selectedAgent === agent.name

                return (
                  <button
                    key={agent.name}
                    onClick={() => onSelectAgent(agent.name)}
                    className={clsx(
                      'w-full flex items-center gap-2 pl-7 pr-2 py-0.5 text-left transition-all group',
                      isSelected
                        ? 'bg-ide-selection text-white'
                        : 'hover:bg-ide-hover text-slate-400 hover:text-slate-200',
                    )}
                  >
                    {/* Status dot */}
                    <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', STATUS_DOT[status])} />

                    {/* Icon */}
                    <span className="text-xs flex-shrink-0">{agent.icon}</span>

                    {/* Name */}
                    <span className={clsx(
                      'text-[11px] flex-1 truncate font-mono',
                      isActive ? 'text-indigo-300 font-semibold' :
                      isDone   ? 'text-emerald-400' :
                      isSelected ? 'text-white' : 'text-slate-400',
                    )}>
                      {agent.name}
                    </span>

                    {/* Status tag */}
                    {status !== 'idle' && (
                      <span className={clsx('text-[8px] font-bold flex-shrink-0', STATUS_CLASS[status])}>
                        {status === 'in_progress' ? 'RUN' :
                         status === 'active'      ? 'RUN' :
                         status === 'done'        ? '✓'   :
                         status === 'error'       ? '✗'   : status.slice(0,3).toUpperCase()}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>

      {/* Footer — agent count */}
      <div className="border-t border-ide-border px-3 py-1.5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-slate-600">
            {Object.values(agentStatuses).filter(s => s === 'done').length} /
            {' '}{TREE.reduce((acc, g) => acc + g.agents.length, 0)} agents done
          </span>
          <Hexagon size={10} className="text-indigo-600" />
        </div>
      </div>
    </div>
  )
}
