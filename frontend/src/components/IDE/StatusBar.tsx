// components/IDE/StatusBar.tsx — VS Code bottom status bar

import { useNexusStore } from "../../store/agentStore"

export function StatusBar() {
  const agentStatuses = useNexusStore(s => s.agentStatuses)
  const taskId        = useNexusStore(s => s.taskId)
  const taskRunning   = useNexusStore(s => s.taskRunning)
  const connected     = useNexusStore(s => s.connected)
  const roster        = useNexusStore(s => s.roster)

  const active  = Object.values(agentStatuses).filter(s => s === "in_progress" || s === "active").length
  const done    = Object.values(agentStatuses).filter(s => s === "done").length
  const errors  = Object.values(agentStatuses).filter(s => s === "error" || s === "blocked").length

  return (
    <div style={{
      height: 22, background: errors > 0 ? "#5a1d1d" : "#007acc",
      display: "flex", alignItems: "center",
      padding: "0 10px", gap: 14, fontSize: 11,
      color: "#ffffff", flexShrink: 0, userSelect: "none",
    }}>
      {/* Left side */}
      <span style={{ display:"flex", alignItems:"center", gap:4 }}>⬡ NexusSwarm</span>
      <span style={{ color:"rgba(255,255,255,0.4)" }}>|</span>
      <span>{roster.length || 28} agents</span>
      {active > 0  && <span style={{ color: "#f5e642" }}>◎ {active} active</span>}
      {done > 0    && <span style={{ color: "#4ec94e" }}>✓ {done} done</span>}
      {errors > 0  && <span style={{ color: "#f44747" }}>✗ {errors} blocked</span>}

      {/* Right side */}
      <div style={{ marginLeft:"auto", display:"flex", gap:12, alignItems:"center" }}>
        <span style={{ color: connected ? "#4ec94e" : "#f44747" }}>
          {connected ? "● WS" : "○ WS"}
        </span>
        <span style={{ color:"rgba(255,255,255,0.4)" }}>|</span>
        <span>NVIDIA NIM</span>
        <span style={{ color:"rgba(255,255,255,0.4)" }}>|</span>
        <span>UTF-8</span>
        <span style={{ color:"rgba(255,255,255,0.4)" }}>|</span>
        {taskId
          ? <span style={{ color: "#f5e642" }}>⚡ Running</span>
          : <span style={{ color: "#4ec94e" }}>✓ Ready</span>
        }
      </div>
    </div>
  )
}
