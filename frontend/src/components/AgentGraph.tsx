// NexusSwarm — Live Agent Hierarchy Graph v2
// Full hierarchy: Exec → Managers → Gateway → Workers
// Includes all new agents, special HumanApprovalGateway, and pulsing animations

import { useMemo } from 'react'
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import clsx from 'clsx'
import { useNexusStore } from '../store/agentStore'
import type { AgentStatus } from '../types'

// ─────────────────────────────────────────────────────────────────────────────
// STATUS CONFIG
// ─────────────────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<
  AgentStatus,
  { border: string; glow: string; dot: string; label: string; ring: string }
> = {
  idle:        { border: 'border-slate-600/60',  glow: '',                              dot: 'bg-slate-500',    label: 'Idle',     ring: '' },
  in_progress: { border: 'border-indigo-400',    glow: 'shadow-indigo-500/50',         dot: 'bg-indigo-400',   label: 'Active',   ring: 'ring-2 ring-indigo-400/30' },
  active:      { border: 'border-indigo-400',    glow: 'shadow-indigo-500/50',         dot: 'bg-indigo-400',   label: 'Active',   ring: 'ring-2 ring-indigo-400/30' },
  done:        { border: 'border-emerald-500',   glow: 'shadow-emerald-500/40',        dot: 'bg-emerald-400',  label: 'Done',     ring: 'ring-1 ring-emerald-500/20' },
  error:       { border: 'border-red-500',       glow: 'shadow-red-500/50',            dot: 'bg-red-400',      label: 'Error',    ring: 'ring-2 ring-red-500/30' },
  blocked:     { border: 'border-amber-500',     glow: 'shadow-amber-500/40',          dot: 'bg-amber-400',    label: 'Blocked',  ring: 'ring-1 ring-amber-500/20' },
}

// ─────────────────────────────────────────────────────────────────────────────
// COLOR THEMES per manager domain
// ─────────────────────────────────────────────────────────────────────────────
type DomainKey =
  | 'orchestrator'
  | 'planning'
  | 'engineering'
  | 'qa'
  | 'security'
  | 'devops'
  | 'reliability'
  | 'cross-cutting'
  | 'gateway'

const DOMAIN_THEME: Record<DomainKey, {
  managerBg: string
  workerBg: string
  badge: string
  accent: string
  icon: string
}> = {
  orchestrator: {
    managerBg: 'bg-[#1c1040]',
    workerBg:  'bg-[#12102e]',
    badge:     'bg-violet-600/25 text-violet-300 border-violet-500/40',
    accent:    'text-violet-300',
    icon:      '⬡',
  },
  planning: {
    managerBg: 'bg-[#0e1a2e]',
    workerBg:  'bg-[#091525]',
    badge:     'bg-blue-600/25 text-blue-300 border-blue-500/40',
    accent:    'text-blue-300',
    icon:      '◈',
  },
  engineering: {
    managerBg: 'bg-[#0d1f1a]',
    workerBg:  'bg-[#091a14]',
    badge:     'bg-emerald-600/25 text-emerald-300 border-emerald-500/40',
    accent:    'text-emerald-300',
    icon:      '◈',
  },
  qa: {
    managerBg: 'bg-[#1a1510]',
    workerBg:  'bg-[#14100a]',
    badge:     'bg-amber-600/25 text-amber-300 border-amber-500/40',
    accent:    'text-amber-300',
    icon:      '◈',
  },
  security: {
    managerBg: 'bg-[#1a0e10]',
    workerBg:  'bg-[#14090b]',
    badge:     'bg-red-600/25 text-red-300 border-red-500/40',
    accent:    'text-red-300',
    icon:      '◈',
  },
  devops: {
    managerBg: 'bg-[#0e1020]',
    workerBg:  'bg-[#090b18]',
    badge:     'bg-indigo-600/25 text-indigo-300 border-indigo-500/40',
    accent:    'text-indigo-300',
    icon:      '◈',
  },
  reliability: {
    managerBg: 'bg-[#091a1a]',
    workerBg:  'bg-[#071414]',
    badge:     'bg-teal-600/25 text-teal-300 border-teal-500/40',
    accent:    'text-teal-300',
    icon:      '◈',
  },
  'cross-cutting': {
    managerBg: 'bg-[#180e20]',
    workerBg:  'bg-[#120a18]',
    badge:     'bg-purple-600/25 text-purple-300 border-purple-500/40',
    accent:    'text-purple-300',
    icon:      '◉',
  },
  gateway: {
    managerBg: 'bg-[#1a1400]',
    workerBg:  'bg-[#1a1400]',
    badge:     'bg-amber-500/30 text-amber-200 border-amber-400/60',
    accent:    'text-amber-200',
    icon:      '⬡',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// NODE DATA SHAPE
// ─────────────────────────────────────────────────────────────────────────────
interface AgentNodeData extends Record<string, unknown> {
  label: string
  level: 'orchestrator' | 'manager' | 'worker' | 'gateway'
  status: AgentStatus
  model: string
  domain: DomainKey
  isNew: boolean
  tooltip: string
}

// ─────────────────────────────────────────────────────────────────────────────
// CUSTOM AGENT NODE
// ─────────────────────────────────────────────────────────────────────────────
function AgentNode({ data }: NodeProps) {
  const { label, level, status, model, domain, isNew, tooltip } = data as AgentNodeData
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.idle
  const theme = DOMAIN_THEME[domain]
  const bgClass = level === 'worker' || level === 'gateway' ? theme.workerBg : theme.managerBg
  const isActive = status === 'in_progress'

  return (
    <div
      title={tooltip}
      className={clsx(
        'relative px-3 py-2.5 rounded-xl border-2 transition-all duration-500 cursor-default select-none',
        'min-w-[148px]',
        bgClass,
        cfg.border,
        cfg.ring,
        isActive && `shadow-lg ${cfg.glow}`,
        isActive && 'node-active',
        level === 'orchestrator' && 'min-w-[180px] rounded-2xl',
      )}
    >
      {/* Target handle — top */}
      {level !== 'orchestrator' && (
        <Handle
          type="target"
          position={Position.Top}
          className="!bg-slate-500 !border-slate-600 !w-2 !h-2"
        />
      )}

      {/* Pulsing ring when active */}
      {isActive && (
        <span className="absolute inset-0 rounded-xl pointer-events-none animate-ping-once border border-indigo-400/40" />
      )}

      {/* New badge */}
      {isNew && (
        <span className="absolute -top-2 -right-2 text-[8px] font-bold bg-amber-400 text-black px-1 py-0.5 rounded-full leading-none z-10">
          NEW
        </span>
      )}

      {/* Status dot */}
      <span
        className={clsx(
          'absolute top-2 right-2 w-2 h-2 rounded-full',
          cfg.dot,
          isActive && 'status-dot-active',
        )}
      />

      {/* Domain badge */}
      <div className={clsx(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-semibold uppercase tracking-wider border mb-1.5',
        theme.badge,
      )}>
        <span>{theme.icon}</span>
        <span>{level}</span>
      </div>

      {/* Agent name */}
      <div className={clsx(
        'font-semibold leading-tight pr-4',
        level === 'orchestrator' ? 'text-[14px] text-white' : 'text-[11px] text-slate-100',
      )}>
        {label}
        {isNew && <span className="ml-1 text-amber-400 text-[9px]">★</span>}
      </div>

      {/* Model chip */}
      <div className="text-[8px] text-slate-500 font-mono mt-1 truncate max-w-[140px]">
        {model.split('/').pop() ?? model}
      </div>

      {/* Status label */}
      <div className={clsx(
        'text-[8px] font-semibold mt-1.5 uppercase tracking-widest',
        status === 'in_progress' ? 'text-indigo-400' :
        status === 'done'        ? 'text-emerald-400' :
        status === 'error'       ? 'text-red-400' :
        status === 'blocked'     ? 'text-amber-400' :
        'text-slate-600',
      )}>
        {cfg.label}
      </div>

      {/* Source handle — bottom */}
      {(level !== 'worker') && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!bg-slate-500 !border-slate-600 !w-2 !h-2"
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// HUMAN APPROVAL GATEWAY NODE (diamond style)
// ─────────────────────────────────────────────────────────────────────────────
function GatewayNode({ data }: NodeProps) {
  const { label, status, tooltip } = data as AgentNodeData
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.idle
  const isActive = status === 'in_progress'

  return (
    <div title={tooltip} className="relative flex flex-col items-center">
      {/* Top handle — receives from SecurityManager */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-amber-500 !border-amber-400 !w-2.5 !h-2.5"
        style={{ left: -6, top: '50%' }}
      />

      {/* Diamond shape */}
      <div
        className={clsx(
          'relative flex flex-col items-center justify-center',
          'w-[120px] h-[120px] rotate-45',
          'border-2 transition-all duration-500',
          'bg-[#1a1400]',
          isActive ? 'border-amber-400 shadow-lg shadow-amber-500/60' : 'border-amber-600/60',
          isActive && 'node-active',
        )}
      >
        {/* Counter-rotate inner content */}
        <div className="-rotate-45 flex flex-col items-center gap-1 px-2">
          {isActive && (
            <span className="absolute inset-0 rotate-45 pointer-events-none animate-ping-once border border-amber-400/40" />
          )}
          <span className="text-amber-300 text-[18px] leading-none">⬡</span>
          <div className="text-amber-200 font-bold text-[10px] text-center leading-tight whitespace-nowrap">
            {label}
          </div>
          <div className={clsx(
            'text-[7px] font-bold uppercase tracking-wider',
            status === 'in_progress' ? 'text-amber-300' :
            status === 'done'        ? 'text-emerald-400' :
            status === 'blocked'     ? 'text-orange-400' :
            'text-amber-600',
          )}>
            {cfg.label}
          </div>
          <div className="text-[7px] text-amber-700/80 font-medium mt-0.5">Approval Gate</div>
        </div>
      </div>

      {/* Bottom handle — exits to DevOpsManager */}
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-amber-500 !border-amber-400 !w-2.5 !h-2.5"
        style={{ right: -6, top: '50%' }}
      />
    </div>
  )
}

const nodeTypes = {
  agentNode:   AgentNode,
  gatewayNode: GatewayNode,
}

// ─────────────────────────────────────────────────────────────────────────────
// NODE LAYOUT DEFINITIONS
// Canvas is ~1500px wide. Tiers:
//   Y=0    → Orchestrator
//   Y=160  → Managers (7 + gateway inlined between Security & DevOps)
//   Y=370  → Workers
//   Y=160  → Cross-cutting workers (alongside managers, offset right)
// ─────────────────────────────────────────────────────────────────────────────

interface NodeDef {
  id: string
  x: number
  y: number
  level: AgentNodeData['level']
  domain: DomainKey
  manager: string | null
  model: string
  isNew: boolean
  tooltip: string
  type?: string
}

const NODE_LAYOUT: NodeDef[] = [
  // ── Tier 0: Orchestrator ──────────────────────────────────────────
  {
    id: 'HeadOrchestrator',
    x: 690, y: 10,
    level: 'orchestrator', domain: 'orchestrator',
    manager: null,
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'HeadOrchestrator — Top-level governance and delegation hub',
  },

  // ── Tier 1: Managers ─────────────────────────────────────────────
  {
    id: 'PlanningManager',
    x: 30, y: 200,
    level: 'manager', domain: 'planning',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'PlanningManager — Requirements and risk planning pipeline',
  },
  {
    id: 'EngineeringManager',
    x: 250, y: 200,
    level: 'manager', domain: 'engineering',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'EngineeringManager — Backend, API, and runtime execution',
  },
  {
    id: 'QAManager',
    x: 500, y: 200,
    level: 'manager', domain: 'qa',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'QAManager — Testing, diagnostics, and automated repair',
  },
  {
    id: 'SecurityManager',
    x: 740, y: 200,
    level: 'manager', domain: 'security',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'SecurityManager — Scanning, integrity, and dependency security',
  },
  {
    id: 'DevOpsManager',
    x: 1130, y: 200,
    level: 'manager', domain: 'devops',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'DevOpsManager — Deploy and rollback orchestration',
  },
  {
    id: 'ReliabilityManager',
    x: 1360, y: 200,
    level: 'manager', domain: 'reliability',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: true,
    tooltip: 'ReliabilityManager ★ NEW — Runtime monitoring and optimization [NEW]',
  },

  // ── Special Gateway ───────────────────────────────────────────────
  {
    id: 'HumanApprovalGateway',
    x: 972, y: 190,
    level: 'gateway', domain: 'gateway',
    manager: null, // edges handled manually
    model: 'human-in-the-loop',
    isNew: false,
    tooltip: 'HumanApprovalGateway — Manual approval gate between Security → DevOps',
    type: 'gatewayNode',
  },

  // ── Tier 2: Workers — Planning ────────────────────────────────────
  {
    id: 'RequirementAgent',
    x: -10, y: 420,
    level: 'worker', domain: 'planning',
    manager: 'PlanningManager',
    model: 'llama-3.1-8b-instruct',
    isNew: false,
    tooltip: 'RequirementAgent — Extracts and structures task requirements',
  },
  {
    id: 'RiskAnalyzer',
    x: 150, y: 420,
    level: 'worker', domain: 'planning',
    manager: 'PlanningManager',
    model: 'llama-3.1-8b-instruct',
    isNew: false,
    tooltip: 'RiskAnalyzer — Scores and ranks task risks',
  },

  // ── Tier 2: Workers — Engineering ────────────────────────────────
  {
    id: 'BackendAgent',
    x: 200, y: 420,
    level: 'worker', domain: 'engineering',
    manager: 'EngineeringManager',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'BackendAgent — Core service and data-layer development',
  },
  {
    id: 'APIAgent',
    x: 360, y: 420,
    level: 'worker', domain: 'engineering',
    manager: 'EngineeringManager',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'APIAgent — REST/GraphQL endpoint construction and docs',
  },
  {
    id: 'RuntimeExecutionAgent',
    x: 520, y: 420,
    level: 'worker', domain: 'engineering',
    manager: 'EngineeringManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'RuntimeExecutionAgent ★ NEW — Sandboxed code execution and result capture',
  },

  // ── Tier 2: Workers — QA ─────────────────────────────────────────
  {
    id: 'TestAgent',
    x: 620, y: 420,
    level: 'worker', domain: 'qa',
    manager: 'QAManager',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'TestAgent — Unit, integration, and regression test execution',
  },
  {
    id: 'DiagnosticsAgent',
    x: 770, y: 420,
    level: 'worker', domain: 'qa',
    manager: 'QAManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'DiagnosticsAgent ★ NEW — Root-cause analysis and failure triage',
  },
  {
    id: 'RepairAgent',
    x: 920, y: 420,
    level: 'worker', domain: 'qa',
    manager: 'QAManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'RepairAgent ★ NEW — Automated patch generation for detected failures',
  },

  // ── Tier 2: Workers — Security ────────────────────────────────────
  {
    id: 'ScannerAgent',
    x: 1070, y: 420,
    level: 'worker', domain: 'security',
    manager: 'SecurityManager',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'ScannerAgent — Static and dynamic vulnerability scanning',
  },
  {
    id: 'IntegrityValidator',
    x: 1220, y: 420,
    level: 'worker', domain: 'security',
    manager: 'SecurityManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'IntegrityValidator ★ NEW — Artifact and signature integrity checks',
  },
  {
    id: 'DependencySecurityAgent',
    x: 1370, y: 420,
    level: 'worker', domain: 'security',
    manager: 'SecurityManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'DependencySecurityAgent ★ NEW — Supply-chain and CVE analysis',
  },

  // ── Tier 2: Workers — DevOps ──────────────────────────────────────
  {
    id: 'DeployAgent',
    x: 1520, y: 420,
    level: 'worker', domain: 'devops',
    manager: 'DevOpsManager',
    model: 'llama-3.1-70b-instruct',
    isNew: false,
    tooltip: 'DeployAgent — Automated deployment and environment promotion',
  },
  {
    id: 'RollbackAgent',
    x: 1670, y: 420,
    level: 'worker', domain: 'devops',
    manager: 'DevOpsManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'RollbackAgent ★ NEW — Safe automated rollback on deployment failure',
  },

  // ── Tier 2: Workers — Reliability ────────────────────────────────
  {
    id: 'RuntimeMonitor',
    x: 1820, y: 420,
    level: 'worker', domain: 'reliability',
    manager: 'ReliabilityManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'RuntimeMonitor ★ NEW — Live health metrics and alert aggregation',
  },
  {
    id: 'OptimizationAgent',
    x: 1970, y: 420,
    level: 'worker', domain: 'reliability',
    manager: 'ReliabilityManager',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'OptimizationAgent ★ NEW — Performance tuning recommendations',
  },

  // ── Cross-cutting (under HeadOrchestrator) ────────────────────────
  {
    id: 'LoggerAgent',
    x: 1820, y: 200,
    level: 'worker', domain: 'cross-cutting',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-8b-instruct',
    isNew: false,
    tooltip: 'LoggerAgent — Structured event logging across all agents',
  },
  {
    id: 'RecoveryAgent',
    x: 1970, y: 200,
    level: 'worker', domain: 'cross-cutting',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-8b-instruct',
    isNew: false,
    tooltip: 'RecoveryAgent — Cross-system recovery coordination',
  },
  {
    id: 'RetryCoordinator',
    x: 2120, y: 200,
    level: 'worker', domain: 'cross-cutting',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-8b-instruct',
    isNew: true,
    tooltip: 'RetryCoordinator ★ NEW — Exponential-backoff retry orchestration',
  },
  {
    id: 'KnowledgeMemoryAgent',
    x: 2270, y: 200,
    level: 'worker', domain: 'cross-cutting',
    manager: 'HeadOrchestrator',
    model: 'llama-3.1-70b-instruct',
    isNew: true,
    tooltip: 'KnowledgeMemoryAgent ★ NEW — Long-term memory and retrieval for all agents',
  },
]

// ─────────────────────────────────────────────────────────────────────────────
// EDGE STYLE HELPER
// ─────────────────────────────────────────────────────────────────────────────
type EdgeStyle = 'normal' | 'gateway' | 'crosscutting'

function makeEdge(
  source: string,
  target: string,
  active: boolean,
  style: EdgeStyle = 'normal',
): Edge {
  const COLORS: Record<EdgeStyle, { active: string; idle: string }> = {
    normal:       { active: '#6366f1', idle: '#23233a' },
    gateway:      { active: '#f59e0b', idle: '#3d2e00' },
    crosscutting: { active: '#a855f7', idle: '#2d1a3a' },
  }

  const col = COLORS[style]
  const strokeColor = active ? col.active : col.idle
  const width = active ? (style === 'gateway' ? 3 : 2.5) : 1.5
  const filter = active ? `drop-shadow(0 0 6px ${col.active}90)` : 'none'

  return {
    id:       `${source}->${target}`,
    source,
    target,
    animated: active,
    style: {
      stroke:      strokeColor,
      strokeWidth: width,
      filter,
    },
    ...(style === 'gateway'
      ? {
          markerEnd: {
            type: 'arrowclosed' as const,
            color: active ? '#f59e0b' : '#3d2e00',
            width: 14,
            height: 14,
          },
        }
      : {}),
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AGENT GRAPH COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export function AgentGraph() {
  const agentStatuses = useNexusStore((s) => s.agentStatuses)

  // ── Build nodes ───────────────────────────────────────────────────
  const nodes: Node[] = useMemo(
    () =>
      NODE_LAYOUT.map(({ id, x, y, level, domain, model, isNew, tooltip, type }) => ({
        id,
        type:     type ?? 'agentNode',
        position: { x, y },
        draggable: true,
        data: {
          label:   id,
          level,
          domain,
          status:  agentStatuses[id] ?? 'idle',
          model,
          isNew,
          tooltip,
        } satisfies AgentNodeData,
      })),
    [agentStatuses],
  )

  // ── Build edges ───────────────────────────────────────────────────
  const edges: Edge[] = useMemo(() => {
    const result: Edge[] = []

    const isActive = (id: string) => (agentStatuses[id] ?? 'idle') === 'in_progress'

    // Regular parent→child edges (excluding gateway which is handled manually)
    for (const { id, manager, domain } of NODE_LAYOUT) {
      if (!manager) continue
      const active = isActive(manager) || isActive(id)
      const style: EdgeStyle =
        domain === 'cross-cutting' ? 'crosscutting' : 'normal'
      result.push(makeEdge(manager, id, active, style))
    }

    // Special gateway flow: SecurityManager → HumanApprovalGateway → DevOpsManager
    const gatewayIn  = isActive('SecurityManager') || isActive('HumanApprovalGateway')
    const gatewayOut = isActive('HumanApprovalGateway') || isActive('DevOpsManager')
    result.push(makeEdge('SecurityManager', 'HumanApprovalGateway', gatewayIn, 'gateway'))
    result.push(makeEdge('HumanApprovalGateway', 'DevOpsManager', gatewayOut, 'gateway'))

    return result
  }, [agentStatuses])

  return (
    <div
      className="w-full h-full rounded-xl overflow-hidden"
      style={{ background: '#07070f' }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 0.85 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{
          style: { strokeWidth: 1.5 },
        }}
      >
        {/* Subtle dot grid */}
        <Background
          variant={BackgroundVariant.Dots}
          gap={28}
          size={1}
          color="#1a1a2e"
        />

        {/* Legend overlay */}
        <div
          className="absolute bottom-3 left-3 z-10 flex flex-col gap-1.5 rounded-xl border border-slate-700/50 bg-slate-900/80 backdrop-blur-sm px-3 py-2.5 text-[9px] font-mono"
          style={{ pointerEvents: 'none' }}
        >
          <div className="text-slate-400 font-semibold uppercase tracking-widest mb-0.5">Legend</div>
          {(
            [
              { dot: 'bg-slate-500',   label: 'Idle' },
              { dot: 'bg-indigo-400',  label: 'Active', pulse: true },
              { dot: 'bg-emerald-400', label: 'Done' },
              { dot: 'bg-red-400',     label: 'Error' },
              { dot: 'bg-amber-400',   label: 'Blocked' },
            ] as const
          ).map(({ dot, label }) => (
            <div key={label} className="flex items-center gap-1.5 text-slate-400">
              <span className={`w-2 h-2 rounded-full ${dot}`} />
              {label}
            </div>
          ))}
          <div className="border-t border-slate-700/40 mt-1 pt-1 flex items-center gap-1.5 text-amber-600/80">
            <span className="text-[10px]">⬡</span>
            Approval Gate
          </div>
          <div className="flex items-center gap-1.5 text-amber-400/70">
            <span className="text-amber-400 text-[8px]">★</span>
            New in v2
          </div>
        </div>
      </ReactFlow>

      {/* Global CSS animations injected via style tag */}
      <style>{`
        @keyframes nexus-pulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
          50%      { box-shadow: 0 0 0 8px rgba(99,102,241,0.25); }
        }
        @keyframes nexus-dot-pulse {
          0%,100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.4; transform: scale(1.6); }
        }
        @keyframes ping-once {
          0%   { transform: scale(1);   opacity: 0.5; }
          100% { transform: scale(1.4); opacity: 0; }
        }
        .node-active {
          animation: nexus-pulse 2s ease-in-out infinite;
        }
        .status-dot-active {
          animation: nexus-dot-pulse 1.2s ease-in-out infinite;
        }
        .animate-ping-once {
          animation: ping-once 1.8s ease-out infinite;
        }
        /* Override React Flow default edge label background */
        .react-flow__edge-path {
          transition: stroke 0.4s ease, stroke-width 0.4s ease;
        }
      `}</style>
    </div>
  )
}
