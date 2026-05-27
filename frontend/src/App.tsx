// App.tsx — NexusSwarm IDE Layout
// VS Code-style: TitleBar → ActivityBar + Sidebar + Editor + LiveLog | Terminal | StatusBar

import { useState, useEffect, useRef } from "react"
import { TitleBar }        from "./components/IDE/TitleBar"
import { ActivityBar }     from "./components/IDE/ActivityBar"
import { AgentTreePanel }  from "./components/IDE/AgentTreePanel"
import { EditorArea }      from "./components/IDE/EditorArea"
import { IDETerminalPanel }from "./components/IDE/IDETerminalPanel"
import { StatusBar }       from "./components/IDE/StatusBar"
import { CommandPalette }  from "./components/IDE/CommandPalette"
import { useAgentStream }  from "./hooks/useAgentStream"
import { getApiErrorMessage, useNexusStore }   from "./store/agentStore"

type Panel = "agents" | "files" | "outputs" | "pipelines"

// Resize handle (drag sidebar)
function ResizeHandle({ onDrag }: { onDrag: (dx: number) => void }) {
  const startX = useRef<number | null>(null)
  return (
    <div
      style={{ width: 4, cursor: "col-resize", background: "transparent", flexShrink: 0 }}
      onMouseDown={(e) => {
        startX.current = e.clientX
        const onMove = (mv: MouseEvent) => {
          if (startX.current !== null) {
            onDrag(mv.clientX - startX.current)
            startX.current = mv.clientX
          }
        }
        const onUp = () => {
          window.removeEventListener("mousemove", onMove)
          window.removeEventListener("mouseup", onUp)
        }
        window.addEventListener("mousemove", onMove)
        window.addEventListener("mouseup", onUp)
      }}
    />
  )
}

// Right-side live log
function LiveLogPanel() {
  const events     = useNexusStore(s => s.events)
  const bottomRef  = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events.length])

  const LEVEL_COLOR: Record<string, string> = {
    orchestrator: "#6366f1",
    manager:      "#4ec9b0",
    gateway:      "#c586c0",
    worker:       "#9cdcfe",
  }

  const STATUS_DOT: Record<string, string> = {
    idle:        "#555",
    active:      "#6fb3f2",
    in_progress: "#6fb3f2",
    done:        "#4ec94e",
    error:       "#f44747",
    blocked:     "#f44747",
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{
        padding: "6px 10px", fontSize: 11, fontWeight: 700,
        color: "#858585", letterSpacing: "0.1em",
        borderBottom: "1px solid #3c3c3c", userSelect: "none", flexShrink: 0,
        background: "#252526",
      }}>NEXUSSWARM LIVE</div>

      <div style={{
        flex: 1, overflowY: "auto", padding: "6px 8px",
        fontFamily: "'Cascadia Code','Fira Code','Consolas',monospace",
        fontSize: 11, lineHeight: "1.6",
      }}>
        {events.length === 0 && (
          <div style={{ color: "#444", padding: "8px 0" }}>Waiting for events…</div>
        )}
        {[...events].reverse().map((ev, i) => (
          <div key={ev.event_id ?? i} style={{
            display: "flex", gap: 6, alignItems: "flex-start",
            marginBottom: 2, padding: "1px 4px", borderRadius: 3,
          }}>
            {/* Status dot */}
            <span style={{
              width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
              background: STATUS_DOT[ev.status] ?? "#555", marginTop: 4,
              boxShadow: (ev.status === "active" || ev.status === "in_progress") ? `0 0 5px ${STATUS_DOT[ev.status]}` : "none",
            }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 4 }}>
                <span style={{ color: LEVEL_COLOR[ev.agent_level] ?? "#9cdcfe", fontSize: 10, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {ev.agent_name}
                </span>
                <span style={{ color: "#333", fontSize: 9, flexShrink: 0 }}>
                  {new Date(ev.timestamp).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>
              <div style={{
                color: ev.status === "error" ? "#f44747" : ev.event_type === "complete" ? "#4ec94e" : "#888",
                fontSize: 10, wordBreak: "break-word",
              }}>
                {ev.message}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ── Main App ────────────────────────────────────────────────────────
export default function App() {
  const [sidebarWidth,   setSidebarWidth]   = useState(260)
  const [terminalHeight, setTerminalHeight] = useState(220)
  const [activePanel,    setActivePanel]    = useState<Panel>("agents")
  const [paletteOpen,    setPaletteOpen]    = useState(false)
  const apiError = useNexusStore(s => s.apiError)
  const setApiError = useNexusStore(s => s.setApiError)

  // Connect WebSocket
  useAgentStream()

  // Load task from query param if present (?task=task_id)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlTaskId = params.get("task")
    if (urlTaskId) {
      const fetchPastTask = async () => {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        try {
          const res = await fetch(`${apiUrl}/status/${urlTaskId}`)
          if (!res.ok) {
            useNexusStore.getState().setApiError(await getApiErrorMessage(res))
            return
          }
          const taskData = await res.json()
          useNexusStore.getState().setTaskId(taskData.task_id, taskData.title)
          if (taskData.outputs) {
            const items = Object.entries(taskData.outputs).map(([agent, content]) => ({
              agent,
              pipeline: "system",
              type: agent,
              content: content as string
            }))
            useNexusStore.setState({ outputItems: items, taskRunning: false })
          }
          useNexusStore.getState().fetchFiles()
        } catch (e) {
          useNexusStore.getState().setApiError("Could not load the shared task. Check the backend connection.")
        }
      }
      fetchPastTask()
    }
  }, [])

  // Sync taskId to URL
  const taskId = useNexusStore(s => s.taskId)
  useEffect(() => {
    if (taskId) {
      const params = new URLSearchParams(window.location.search)
      if (params.get("task") !== taskId) {
        window.history.pushState({}, "", `?task=${taskId}`)
      }
    } else {
      // Clear query string if task is cleared
      const params = new URLSearchParams(window.location.search)
      if (params.has("task")) {
        window.history.pushState({}, "", window.location.pathname)
      }
    }
  }, [taskId])

  // Ctrl+Shift+P → open palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "P") {
        e.preventDefault()
        setPaletteOpen(p => !p)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "100vh", width: "100vw",
      background: "#1e1e1e", color: "#d4d4d4",
      fontFamily: "'Segoe UI', 'Inter', system-ui, sans-serif",
      overflow: "hidden",
    }}>

      {/* ── Title bar ── */}
      <TitleBar onOpenPalette={() => setPaletteOpen(true)} />

      {apiError && (
        <div style={{
          background: "#5a1d1d",
          color: "#ffd7d7",
          borderBottom: "1px solid #8a2f2f",
          padding: "6px 12px",
          fontSize: 12,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexShrink: 0,
        }}>
          <span>{apiError}</span>
          <button
            onClick={() => setApiError(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "#ffd7d7",
              cursor: "pointer",
              fontSize: 14,
            }}
            aria-label="Dismiss API error"
          >
            x
          </button>
        </div>
      )}

      {/* ── Main area ── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Activity bar */}
        <ActivityBar active={activePanel} onSelect={setActivePanel} />

        {/* Sidebar — agent tree / outputs / pipelines */}
        <div style={{
          width: sidebarWidth, minWidth: 160, maxWidth: 480,
          background: "#252526", borderRight: "1px solid #3c3c3c",
          display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0,
        }}>
          <AgentTreePanel activePanel={activePanel} />
        </div>

        {/* Drag handle */}
        <ResizeHandle onDrag={(dx) => setSidebarWidth(w => Math.max(160, Math.min(480, w + dx)))} />

        {/* Centre + right column */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Editor row */}
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            {/* Monaco editor */}
            <EditorArea style={{ flex: 1 }} />

            {/* Right live-log */}
            <div style={{
              width: 280, background: "#1e1e1e",
              borderLeft: "1px solid #3c3c3c",
              display: "flex", flexDirection: "column", flexShrink: 0,
            }}>
              <LiveLogPanel />
            </div>
          </div>

          {/* Terminal bottom panel (resizable) */}
          <div style={{
            height: terminalHeight, minHeight: 80, maxHeight: 520,
            borderTop: "2px solid #3c3c3c", background: "#1e1e1e",
            flexShrink: 0,
          }}>
            {/* Resize top edge */}
            <div
              style={{ height: 4, cursor: "row-resize", background: "transparent" }}
              onMouseDown={(e) => {
                const startY = e.clientY
                const startH = terminalHeight
                const onMove = (mv: MouseEvent) =>
                  setTerminalHeight(Math.max(80, Math.min(520, startH - (mv.clientY - startY))))
                const onUp = () => {
                  window.removeEventListener("mousemove", onMove)
                  window.removeEventListener("mouseup", onUp)
                }
                window.addEventListener("mousemove", onMove)
                window.addEventListener("mouseup", onUp)
              }}
            />
            <IDETerminalPanel />
          </div>

        </div>
      </div>

      {/* ── Status bar ── */}
      <StatusBar />

      {/* ── Command palette overlay ── */}
      {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} />}
    </div>
  )
}
