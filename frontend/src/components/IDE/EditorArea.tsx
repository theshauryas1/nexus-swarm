// components/IDE/EditorArea.tsx — Monaco editor with tabbed agent outputs

import { useState, useEffect } from "react"
import Editor from "@monaco-editor/react"
import { useNexusStore, safeGet } from "../../store/agentStore"

const WELCOME_CONTENT = `# ⬡ NexusSwarm — Hierarchical Multi-Agent Orchestration

## What is NexusSwarm?

An AI organizational hierarchy that mirrors real enterprise software delivery.
28 agents — 7 pipelines — governed at BOTH the hierarchy and the MCP tool layer.

## Architecture

  HEAD ORCHESTRATOR
  ├── PlanningManager
  │   ├── RequirementAgent
  │   └── RiskAnalyzer
  ├── EngineeringManager
  │   ├── BackendAgent      → Qwen3 Coder 480B
  │   ├── APIAgent          → Qwen3 Coder 480B
  │   └── FrontendAgent
  ├── QAManager
  │   ├── TestAgent         → Qwen3 Coder 480B
  │   ├── DiagnosticsAgent
  │   └── RepairAgent
  ├── SecurityManager
  │   └── ScannerAgent
  ├── ◈ HumanApprovalGateway
  ├── DevOpsManager
  │   └── DeployAgent
  └── ReliabilityManager
      └── KnowledgeMemoryAgent

## How to start

  1. Press Ctrl+Shift+P  ← open Command Palette
  2. Type your task in plain English
  3. Press Enter to launch the swarm
  4. Watch agents coordinate in real time in the Agent Explorer and Terminal
`

// Map agent name → Monaco language
const AGENT_LANG: Record<string, string> = {
  BackendAgent:        "python",
  APIAgent:            "yaml",
  FrontendAgent:       "typescript",
  TestAgent:           "python",
  DeployAgent:         "dockerfile",
  RepairAgent:         "python",
  ScannerAgent:        "json",
  RequirementAgent:    "markdown",
  RiskAnalyzer:        "markdown",
  HeadOrchestrator:    "json",
  KnowledgeMemoryAgent:"markdown",
  DiagnosticsAgent:    "markdown",
  default:             "plaintext",
}

const AGENT_LABEL: Record<string, string> = {
  BackendAgent:        "backend.py",
  APIAgent:            "openapi.yaml",
  FrontendAgent:       "components.tsx",
  TestAgent:           "test_backend.py",
  DeployAgent:         "Dockerfile",
  RepairAgent:         "repair.py",
  ScannerAgent:        "security_report.json",
  RequirementAgent:    "requirements.md",
  RiskAnalyzer:        "risk_analysis.md",
  HeadOrchestrator:    "execution_plan.json",
  KnowledgeMemoryAgent:"knowledge.md",
  DiagnosticsAgent:    "diagnostics.md",
  default:             "output.txt",
}

type CSSProperties = React.CSSProperties

interface Props { style?: CSSProperties }

export function EditorArea({ style }: Props) {
  const [activeTab, setActiveTab]   = useState<string>("welcome")
  const [closedTabs, setClosedTabs] = useState<Set<string>>(new Set())
  const outputItems = useNexusStore(s => s.outputItems)
  const selectedFile = useNexusStore(s => s.selectedFile)
  const selectedFileContent = useNexusStore(s => s.selectedFileContent)
  const selectFile = useNexusStore(s => s.selectFile)
  const [openFiles, setOpenFiles] = useState<string[]>([])

  // Watch for selectedFile changes from the sidebar to open/focus tab
  useEffect(() => {
    if (selectedFile) {
      if (!openFiles.includes(selectedFile)) {
        setOpenFiles(prev => [...prev, selectedFile])
      }
      setActiveTab("file:" + selectedFile)
    }
  }, [selectedFile])

  // Build visible tabs: welcome + any agent outputs not closed
  const outputTabs = outputItems.filter(o => !closedTabs.has(o.agent))

  const closeTab = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setClosedTabs(s => new Set([...s, id]))
    if (activeTab === id) setActiveTab("welcome")
  }

  const closeFileTab = (fname: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setOpenFiles(prev => prev.filter(f => f !== fname))
    if (activeTab === "file:" + fname) {
      setActiveTab("welcome")
    }
  }

  const getContent = () => {
    if (activeTab === "welcome") return WELCOME_CONTENT
    if (activeTab.startsWith("file:")) {
      const fname = activeTab.slice(5)
      if (fname === selectedFile) {
        return selectedFileContent ?? `// Loading ${fname}...`
      }
      return `// Click tab to load ${fname}`
    }
    const found = outputItems.find(o => o.agent === activeTab)
    return found?.content ?? `// Waiting for ${activeTab} agent output…\n// Submit a task to begin.`
  }

  const getLang = () => {
    if (activeTab === "welcome") return "markdown"
    if (activeTab.startsWith("file:")) {
      const fname = activeTab.slice(5)
      if (fname.endsWith(".py")) return "python"
      if (fname.endsWith(".yaml") || fname.endsWith(".yml")) return "yaml"
      if (fname.endsWith(".tsx")) return "typescript"
      if (fname.endsWith(".json")) return "json"
      if (fname.endsWith(".md")) return "markdown"
      if (fname === "Dockerfile") return "dockerfile"
      return "plaintext"
    }
    return safeGet(AGENT_LANG, activeTab) ?? AGENT_LANG.default
  }

  const getLabel = (agent: string) => safeGet(AGENT_LABEL, agent) ?? AGENT_LABEL.default

  return (
    <div style={{ display:"flex", flexDirection:"column", overflow:"hidden", ...style }}>

      {/* Tab bar */}
      <div style={{
        display:"flex", background:"#252526",
        borderBottom:"1px solid #3c3c3c",
        overflowX:"auto", flexShrink:0,
        scrollbarWidth:"none", minHeight:35,
      }}>
        {/* Welcome tab */}
        <div
          onClick={() => setActiveTab("welcome")}
          style={{
            display:"flex", alignItems:"center", gap:6,
            padding:"0 12px", height:35, flexShrink:0,
            background:   activeTab === "welcome" ? "#1e1e1e" : "transparent",
            borderTop:    activeTab === "welcome" ? "1px solid #6366f1" : "1px solid transparent",
            borderRight:  "1px solid #3c3c3c",
            color:        activeTab === "welcome" ? "#cccccc" : "#7a7a7a",
            fontSize:12, cursor:"pointer", whiteSpace:"nowrap",
          }}
        >
          Welcome
        </div>

        {/* Output tabs */}
        {outputTabs.map(o => {
          const isActive = activeTab === o.agent
          return (
            <div key={o.agent}
              onClick={() => setActiveTab(o.agent)}
              style={{
                display:"flex", alignItems:"center", gap:6,
                padding:"0 12px", height:35, flexShrink:0,
                background:  isActive ? "#1e1e1e" : "transparent",
                borderTop:   isActive ? "1px solid #6366f1" : "1px solid transparent",
                borderRight: "1px solid #3c3c3c",
                color:       isActive ? "#cccccc" : "#7a7a7a",
                fontSize:12, cursor:"pointer", whiteSpace:"nowrap",
              }}
            >
              {getLabel(o.agent)}
              <span
                onClick={(e) => closeTab(o.agent, e)}
                style={{ fontSize:14, lineHeight:1, color:"#555", padding:"0 2px", borderRadius:2, cursor:"pointer" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#cccccc")}
                onMouseLeave={e => (e.currentTarget.style.color = "#555")}
              >×</span>
            </div>
          )
        })}

        {/* File tabs */}
        {openFiles.map(fname => {
          const isActive = activeTab === "file:" + fname
          return (
            <div key={fname}
              onClick={() => {
                setActiveTab("file:" + fname)
                selectFile(fname)
              }}
              style={{
                display:"flex", alignItems:"center", gap:6,
                padding:"0 12px", height:35, flexShrink:0,
                background:  isActive ? "#1e1e1e" : "transparent",
                borderTop:   isActive ? "1px solid #6366f1" : "1px solid transparent",
                borderRight: "1px solid #3c3c3c",
                color:       isActive ? "#cccccc" : "#7a7a7a",
                fontSize:12, cursor:"pointer", whiteSpace:"nowrap",
              }}
            >
              📄 {fname}
              <span
                onClick={(e) => closeFileTab(fname, e)}
                style={{ fontSize:14, lineHeight:1, color:"#555", padding:"0 2px", borderRadius:2, cursor:"pointer" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#cccccc")}
                onMouseLeave={e => (e.currentTarget.style.color = "#555")}
              >×</span>
            </div>
          )
        })}

        {/* New output indicator when incoming */}
        {outputItems.filter(o => !closedTabs.has(o.agent)).length < outputItems.length && (
          <div style={{ display:"flex", alignItems:"center", padding:"0 8px", color:"#6366f1", fontSize:11 }}>
            +{outputItems.length - outputTabs.length} more
          </div>
        )}
      </div>

      {/* Breadcrumb */}
      <div style={{
        padding:"3px 12px", fontSize:11, color:"#858585",
        borderBottom:"1px solid #3c3c3c", flexShrink:0,
        background:"#1e1e1e",
      }}>
        nexusswarm &gt; outputs &gt;{" "}
        {activeTab === "welcome" ? "Welcome" : activeTab.startsWith("file:") ? activeTab.slice(5) : getLabel(activeTab)}
      </div>

      {/* Monaco editor */}
      <div style={{ flex:1, overflow:"hidden" }}>
        <Editor
          height="100%"
          language={getLang()}
          value={getContent()}
          theme="vs-dark"
          options={{
            readOnly:             true,
            fontSize:             13,
            fontFamily:           "'Cascadia Code','Fira Code','Consolas',monospace",
            fontLigatures:        true,
            minimap:              { enabled: true },
            scrollBeyondLastLine: false,
            lineNumbers:          "on",
            folding:              true,
            wordWrap:             "on",
            renderLineHighlight:  "all",
            smoothScrolling:      true,
            cursorBlinking:       "smooth",
          }}
        />
      </div>
    </div>
  )
}
