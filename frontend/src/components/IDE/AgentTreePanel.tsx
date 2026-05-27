// components/IDE/AgentTreePanel.tsx — VS Code Explorer style agent hierarchy tree
// Reads live statuses from Zustand store

import { useState } from "react"
import { getApiErrorMessage, useNexusStore } from "../../store/agentStore"

type Panel = "agents" | "files" | "outputs" | "pipelines"
interface Props { activePanel: Panel }


const STATUS_DOT: Record<string, { color: string; pulse: boolean }> = {
  idle:        { color: "#555555", pulse: false },
  active:      { color: "#6fb3f2", pulse: true  },
  in_progress: { color: "#6fb3f2", pulse: true  },
  working:     { color: "#f5a623", pulse: true  },
  done:        { color: "#4ec94e", pulse: false },
  error:       { color: "#f44747", pulse: false },
  blocked:     { color: "#f44747", pulse: true  },
}

const MODEL_SHORT: Record<string, string> = {
  "mistralai/mistral-large-2-instruct":      "Mistral L",
  "mistralai/mistral-nemo-12b-instruct":     "Nemo",
  "qwen/qwen3-coder-480b-a35b-instruct":     "Qwen3",
  "meta/llama-4-maverick-17b-128e-instruct": "Llama 4",
  "deepseek-ai/deepseek-v4-flash":           "DeepSeek",
  "meta/llama-3.3-70b-instruct":             "Llama 3.3",
  "meta/llama-3.1-8b-instruct":              "Llama 3.1",
}

const TREE = [
  {
    name: "HeadOrchestrator", level: "orchestrator", icon: "⬡",
    children: [
      { name: "PlanningManager",    level: "manager", icon: "▸", children: ["RequirementAgent","RiskAnalyzer"] },
      { name: "EngineeringManager", level: "manager", icon: "▸", children: ["BackendAgent","APIAgent","FrontendAgent"] },
      { name: "QAManager",          level: "manager", icon: "▸", children: ["TestAgent","DiagnosticsAgent","RepairAgent","HallucinationValidator","SemanticValidator","ContractValidator"] },
      { name: "SecurityManager",    level: "manager", icon: "▸", children: ["ScannerAgent"] },
      { name: "HumanApprovalGateway", level: "gateway", icon: "◈", children: [] },
      { name: "DevOpsManager",      level: "manager", icon: "▸", children: ["DeployAgent"] },
      { name: "ReliabilityManager", level: "manager", icon: "▸", children: ["KnowledgeMemoryAgent"] },
    ]
  }
]

const LEVEL_COLOR: Record<string, string> = {
  orchestrator: "#6366f1",
  manager:      "#4ec9b0",
  gateway:      "#c586c0",
  worker:       "#9cdcfe",
}

export function AgentTreePanel({ activePanel }: Props) {
  const agentStatuses = useNexusStore(s => s.agentStatuses)
  const roster        = useNexusStore(s => s.roster)
  const pipelines     = useNexusStore(s => s.pipelines)
  const outputItems   = useNexusStore(s => s.outputItems)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  const toggle = (name: string) => setCollapsed(s => {
    const n = new Set(s); n.has(name) ? n.delete(name) : n.add(name); return n
  })

  const rosterMap = Object.fromEntries(roster.map(a => [a.agent_name, a]))

  const Dot = ({ name }: { name: string }) => {
    const s = agentStatuses[name] ?? "idle"
    const { color, pulse } = STATUS_DOT[s] ?? STATUS_DOT.idle
    return (
      <span style={{
        display: "inline-block", width: 7, height: 7,
        borderRadius: "50%", background: color, flexShrink: 0,
        boxShadow: pulse ? `0 0 5px ${color}` : "none",
        animation: pulse ? "idepulse 1.2s infinite" : "none",
      }} />
    )
  }

  const ModelBadge = ({ name }: { name: string }) => {
    const model = rosterMap[name]?.model
    if (!model) return null
    const short = MODEL_SHORT[model] ?? model.split("/")[1]?.slice(0, 10) ?? ""
    return <span style={{ fontSize: 9, color: "#444", marginLeft: "auto", paddingRight: 8, whiteSpace: "nowrap" }}>{short}</span>
  }

  const renderNode = (node: any, depth = 0): React.ReactNode => {
    const isOpen = !collapsed.has(node.name)
    const hasChildren = node.children?.length > 0
    const indent = depth * 14 + 8
    const color = LEVEL_COLOR[node.level] ?? "#d4d4d4"

    return (
      <div key={node.name}>
        <div
          onClick={() => hasChildren && toggle(node.name)}
          style={{ display:"flex", alignItems:"center", gap:5, padding:`2px 0 2px ${indent}px`, cursor: hasChildren ? "pointer" : "default", fontSize: 12, color }}
          onMouseEnter={e => (e.currentTarget.style.background = "#2a2d2e")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
        >
          {hasChildren
            ? <span style={{ fontSize: 9, width: 10 }}>{isOpen ? "▾" : "▸"}</span>
            : <span style={{ width: 10 }} />}
          <span>{node.icon ?? "◦"}</span>
          <Dot name={node.name} />
          <span style={{ fontSize: 12 }}>{node.name}</span>
          <ModelBadge name={node.name} />
        </div>
        {isOpen && hasChildren && node.children.map((child: any) =>
          typeof child === "string"
            ? renderWorker(child, depth + 1)
            : renderNode(child, depth + 1)
        )}
      </div>
    )
  }

  const renderWorker = (name: string, depth: number) => {
    const indent = depth * 14 + 8
    return (
      <div key={name}
        style={{ display:"flex", alignItems:"center", gap:5, padding:`2px 0 2px ${indent}px`, fontSize:12, color:"#9cdcfe" }}
        onMouseEnter={e => (e.currentTarget.style.background = "#2a2d2e")}
        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ width: 10 }} />
        <span>◦</span>
        <Dot name={name} />
        <span>{name}</span>
        <ModelBadge name={name} />
      </div>
    )
  }

  const PipelineRows = () => (
    <div style={{ padding:"8px 12px", display:"flex", flexDirection:"column", gap:10 }}>
      {Object.values(pipelines).map(p => {
        const color =
          p.status === "done"    ? "#4ec94e" :
          p.status === "active"  ? "#6fb3f2" :
          p.status === "failed"  ? "#f44747" :
          p.status === "blocked" ? "#f5a623" : "#555"
        return (
          <div key={p.name}>
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, marginBottom:3 }}>
              <span style={{ color, textTransform:"capitalize" }}>{p.name}</span>
              <span style={{ color:"#555" }}>{p.progress}%</span>
            </div>
            <div style={{ height:3, background:"#3c3c3c", borderRadius:2 }}>
              <div style={{ height:"100%", borderRadius:2, width:`${p.progress}%`, background:color, transition:"width 0.4s" }} />
            </div>
          </div>
        )
      })}
    </div>
  )

  const OutputRows = () => (
    <div style={{ paddingTop:4 }}>
      {outputItems.length === 0
        ? <div style={{ padding:"16px 12px", fontSize:11, color:"#555" }}>No outputs yet — run a task.</div>
        : outputItems.map(o => (
          <div key={o.agent} style={{ display:"flex", alignItems:"center", gap:8, padding:"4px 12px", fontSize:12, color:"#cccccc", cursor:"pointer" }}
            onMouseEnter={e => (e.currentTarget.style.background = "#2a2d2e")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <span>📄</span>
            <span>{o.agent}</span>
            <span style={{ marginLeft:"auto", fontSize:10, color:"#555" }}>{o.content.length}c</span>
          </div>
        ))
      }
    </div>
  )

  const FilesRows = () => {
    const files = useNexusStore(s => s.files)
    const selectFile = useNexusStore(s => s.selectFile)
    const selectedFile = useNexusStore(s => s.selectedFile)
    const taskId = useNexusStore(s => s.taskId)
    const fetchFiles = useNexusStore(s => s.fetchFiles)
    const setApiError = useNexusStore(s => s.setApiError)

    const handleDownloadZip = async () => {
      if (!taskId) return
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      try {
        const response = await fetch(`${apiUrl}/files/${taskId}/download`)
        if (!response.ok) {
          setApiError(await getApiErrorMessage(response))
          return
        }
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `nexusswarm_task_${taskId}.zip`
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
        setApiError(null)
      } catch {
        setApiError("Could not download the generated files. Check the backend connection.")
      }
    }

    if (!taskId) {
      return <div style={{ padding:"16px 12px", fontSize:11, color:"#555" }}>No task active. Submit a task first.</div>
    }

    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", justifyContent: "space-between" }}>
        <div style={{ flex: 1, overflowY: "auto", paddingTop: 4 }}>
          {files.length === 0 ? (
            <div style={{ padding:"16px 12px", fontSize:11, color:"#555" }}>
              No files generated yet.
              <button 
                onClick={() => fetchFiles()}
                style={{
                  display: "block", marginTop: 8, background: "#3c3c3c", 
                  color: "#ccc", border: "none", padding: "4px 8px", 
                  borderRadius: 3, cursor: "pointer", fontSize: 10
                }}
              >Refresh</button>
            </div>
          ) : (
            files.map(f => {
              const isSelected = selectedFile === f.name
              const icon = 
                f.name.endsWith(".py") ? "🐍" :
                f.name.endsWith(".yaml") || f.name.endsWith(".yml") ? "📋" :
                f.name.endsWith(".tsx") ? "⚛️" :
                f.name.endsWith(".json") ? "🔒" :
                f.name.endsWith(".md") ? "📝" :
                f.name === "Dockerfile" ? "🐳" : "📄"

              return (
                <div key={f.name}
                  onClick={() => selectFile(f.name)}
                  style={{
                    display:"flex", alignItems:"center", gap:8,
                    padding:"6px 12px", fontSize:12,
                    color: isSelected ? "#ffffff" : "#cccccc",
                    background: isSelected ? "#37373d" : "transparent",
                    cursor:"pointer"
                  }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "#2a2d2e" }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent" }}
                >
                  <span>{icon}</span>
                  <span>{f.name}</span>
                  <span style={{ marginLeft:"auto", fontSize:9, color:"#555" }}>{(f.size / 1024).toFixed(1)} KB</span>
                </div>
              )
            })
          )}
        </div>
        {files.length > 0 && (
          <div style={{ padding: 12, borderTop: "1px solid #3c3c3c", display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
            <button
              onClick={handleDownloadZip}
              style={{
                width: "100%", background: "#6366f1", color: "#ffffff",
                border: "none", padding: "6px 10px", borderRadius: 4,
                cursor: "pointer", fontSize: 11, fontWeight: 600,
                textAlign: "center"
              }}
            >
              📥 Download ZIP
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden" }}>
      {/* Panel header */}
      <div style={{
        padding:"6px 12px", fontSize:11, fontWeight:700,
        color:"#bbbbbb", letterSpacing:"0.08em",
        borderBottom:"1px solid #3c3c3c", userSelect:"none",
        display:"flex", alignItems:"center", justifyContent:"space-between",
        flexShrink:0,
      }}>
        {activePanel === "agents"    && "AGENT HIERARCHY"}
        {activePanel === "files"     && "PROJECT FILES"}
        {activePanel === "outputs"   && "GENERATED OUTPUTS"}
        {activePanel === "pipelines" && "PIPELINE STATUS"}
        <span style={{ fontSize:14, cursor:"pointer", color:"#555" }}>⋯</span>
      </div>

      <div style={{ flex:1, overflowY:"auto", paddingTop:4 }}>
        {activePanel === "agents"    && TREE.map(n => renderNode(n))}
        {activePanel === "files"     && <FilesRows />}
        {activePanel === "outputs"   && <OutputRows />}
        {activePanel === "pipelines" && <PipelineRows />}
      </div>

      <style>{`
        @keyframes idepulse { 0%,100% { opacity:1; } 50% { opacity:0.35; } }
      `}</style>
    </div>
  )
}
