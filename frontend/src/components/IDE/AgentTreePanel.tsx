// components/IDE/AgentTreePanel.tsx — VS Code Explorer style agent hierarchy tree
// Reads live statuses from Zustand store

import { useState, useEffect } from "react"
import { getApiErrorMessage, useNexusStore, safeGet } from "../../store/agentStore"

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
    const s = safeGet(agentStatuses, name) ?? "idle"
    const { color, pulse } = safeGet(STATUS_DOT, s) ?? safeGet(STATUS_DOT, "idle")
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
    const model = safeGet(rosterMap, name)?.model
    if (!model) return null
    const short = safeGet(MODEL_SHORT, model) ?? model.split("/")[1]?.slice(0, 10) ?? ""
    return <span style={{ fontSize: 9, color: "#444", marginLeft: "auto", paddingRight: 8, whiteSpace: "nowrap" }}>{short}</span>
  }

  const renderNode = (node: any, depth = 0): React.ReactNode => {
    const isOpen = !collapsed.has(node.name)
    const hasChildren = node.children?.length > 0
    const indent = depth * 14 + 8
    const color = safeGet(LEVEL_COLOR, node.level) ?? "#d4d4d4"

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
    const recentTasks = useNexusStore(s => s.recentTasks)
    const expandedSessions = useNexusStore(s => s.expandedSessions)
    const fetchRecentTasks = useNexusStore(s => s.fetchRecentTasks)
    const fetchSessionFiles = useNexusStore(s => s.fetchSessionFiles)
    const selectSessionFile = useNexusStore(s => s.selectSessionFile)
    const selectedFile = useNexusStore(s => s.selectedFile)
    const activeTaskId = useNexusStore(s => s.taskId)
    const setApiError = useNexusStore(s => s.setApiError)
    
    const [openFolders, setOpenFolders] = useState<Set<string>>(new Set([activeTaskId || ""]))
    const [searchQuery, setSearchQuery] = useState("")

    // Fetch recent tasks on mount
    useEffect(() => {
      fetchRecentTasks()
    }, [])

    // Synchronize open folders with the activeTaskId if changed
    useEffect(() => {
      if (activeTaskId) {
        setOpenFolders(prev => {
          const next = new Set(prev)
          next.add(activeTaskId)
          return next
        })
        fetchSessionFiles(activeTaskId)
      }
    }, [activeTaskId])

    const toggleFolder = async (taskId: string) => {
      setOpenFolders(prev => {
        const next = new Set(prev)
        if (next.has(taskId)) {
          next.delete(taskId)
        } else {
          next.add(taskId)
          // Always refresh files when expanding a folder to ensure it is up-to-date
          fetchSessionFiles(taskId)
        }
        return next
      })
    }

    const handleDownloadZip = async (taskId: string, title: string, e: React.MouseEvent) => {
      e.stopPropagation()
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
        a.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_files.zip`
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
        setApiError(null)
      } catch {
        setApiError("Could not download the generated files. Check the backend connection.")
      }
    }

    const getFileIcon = (name: string) => {
      if (name.endsWith(".py")) return "🐍"
      if (name.endsWith(".yaml") || name.endsWith(".yml")) return "📋"
      if (name.endsWith(".tsx")) return "⚛️"
      if (name.endsWith(".json")) return "🔒"
      if (name.endsWith(".md")) return "📝"
      if (name === "Dockerfile") return "🐳"
      return "📄"
    }

    // Filter recent tasks/sessions based on search
    const filteredTasks = recentTasks.filter(task => 
      task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.task_id.toLowerCase().includes(searchQuery.toLowerCase())
    )

    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
        {/* Search bar */}
        <div style={{ padding: "8px 12px", borderBottom: "1px solid #3c3c3c", display: "flex", gap: 6, flexShrink: 0 }}>
          <input
            type="text"
            placeholder="Search sessions/files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1, background: "#1e1e1e", border: "1px solid #3c3c3c",
              borderRadius: 3, padding: "4px 8px", color: "#ccc",
              fontSize: 11, outline: "none"
            }}
          />
          <button
            onClick={() => fetchRecentTasks()}
            title="Refresh Explorer"
            style={{
              background: "#3c3c3c", border: "none", color: "#ccc",
              padding: "4px 6px", borderRadius: 3, cursor: "pointer",
              fontSize: 11
            }}
          >
            ↻
          </button>
        </div>

        {/* Sessions list */}
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", paddingTop: 4 }}>
          {filteredTasks.length === 0 ? (
            <div style={{ padding: "16px 12px", fontSize: 11, color: "#555" }}>
              No sessions found. Launch a task using the Command Palette!
            </div>
          ) : (
            filteredTasks.map(task => {
              const isOpen = openFolders.has(task.task_id)
              const isActive = activeTaskId === task.task_id
              const filesInFolder = safeGet(expandedSessions, task.task_id) ?? []

              return (
                <div key={task.task_id} style={{ display: "flex", flexDirection: "column" }}>
                  {/* Folder row */}
                  <div
                    onClick={() => toggleFolder(task.task_id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 6,
                      padding: "6px 12px 6px 10px", fontSize: 12,
                      color: isActive ? "#6366f1" : "#cccccc",
                      background: isActive ? "rgba(99, 102, 241, 0.05)" : "transparent",
                      borderLeft: isActive ? "2px solid #6366f1" : "2px solid transparent",
                      cursor: "pointer", fontWeight: isActive ? 600 : 400,
                      userSelect: "none"
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = "#2a2d2e" }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent" }}
                  >
                    <span style={{ fontSize: 9, width: 8, color: "#858585" }}>{isOpen ? "▾" : "▸"}</span>
                    <span style={{ fontSize: 13 }}>{isOpen ? "📂" : "📁"}</span>
                    <span style={{
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1,
                      color: isActive ? "#ffffff" : "#cccccc"
                    }} title={task.title}>
                      {task.title}
                    </span>
                    {/* Hover Actions */}
                    <div style={{ display: "flex", gap: 6 }}>
                      <span 
                        onClick={(e) => handleDownloadZip(task.task_id, task.title, e)}
                        title="Download ZIP"
                        style={{ cursor: "pointer", fontSize: 11, color: "#858585" }}
                        onMouseEnter={e => e.currentTarget.style.color = "#ffffff"}
                        onMouseLeave={e => e.currentTarget.style.color = "#858585"}
                      >
                        📥
                      </span>
                    </div>
                  </div>

                  {/* Nested files */}
                  {isOpen && (
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      {filesInFolder.length === 0 ? (
                        <div style={{ padding: "4px 12px 4px 34px", fontSize: 10, color: "#666", fontStyle: "italic" }}>
                          Empty / Loading files...
                        </div>
                      ) : (
                        filesInFolder.map((f: any) => {
                          const isSelected = selectedFile === f.name && isActive
                          return (
                            <div key={f.name}
                              onClick={() => selectSessionFile(task.task_id, f.name)}
                              style={{
                                display: "flex", alignItems: "center", gap: 8,
                                padding: "4px 12px 4px 30px", fontSize: 11,
                                color: isSelected ? "#ffffff" : "#aaaaaa",
                                background: isSelected ? "#37373d" : "transparent",
                                cursor: "pointer",
                                userSelect: "none"
                              }}
                              onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "#2a2d2e" }}
                              onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent" }}
                            >
                              <span>{getFileIcon(f.name)}</span>
                              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                                {f.name}
                              </span>
                              <span style={{ fontSize: 9, color: "#555" }}>
                                {(f.size / 1024).toFixed(1)} KB
                              </span>
                            </div>
                          )
                        })
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
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
