// components/IDE/IDETerminalPanel.tsx — VS Code integrated terminal
// (Renamed to avoid clash with existing TerminalPanel.tsx)

import { useEffect, useRef, useState } from "react"
import { useNexusStore } from "../../store/agentStore"

const LEVEL_COLOR: Record<string, string> = {
  orchestrator: "#6366f1",
  manager:      "#4ec9b0",
  gateway:      "#c586c0",
  worker:       "#9cdcfe",
}

const STATUS_PREFIX: Record<string, string> = {
  active:      "▶",
  in_progress: "▶",
  working:     "◎",
  done:        "✓",
  error:       "✗",
  blocked:     "⛔",
  idle:        "○",
}

type TermTab = "TERMINAL" | "OUTPUT" | "PROBLEMS" | "DEBUG"

export function IDETerminalPanel() {
  const events    = useNexusStore(s => s.events)
  const taskTitle = useNexusStore(s => s.taskTitle)
  const [tab, setTab] = useState<TermTab>("TERMINAL")
  const bottomRef = useRef<HTMLDivElement>(null)

  const errors = events.filter(e => e.status === "error")

  useEffect(() => {
    if (tab === "TERMINAL")
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events.length, tab])

  const TABS: TermTab[] = ["TERMINAL", "OUTPUT", "PROBLEMS", "DEBUG"]

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%" }}>
      {/* Tab bar */}
      <div style={{
        display:"flex", alignItems:"center",
        background:"#252526", borderBottom:"1px solid #3c3c3c",
        height:28, flexShrink:0,
      }}>
        {TABS.map(t => (
          <div key={t}
            onClick={() => setTab(t)}
            style={{
              padding:"0 12px", fontSize:11,
              color:     tab === t ? "#cccccc" : "#7a7a7a",
              borderBottom: tab === t ? "1px solid #6366f1" : "1px solid transparent",
              height:"100%", display:"flex", alignItems:"center",
              cursor:"pointer", userSelect:"none",
              position:"relative",
            }}
          >
            {t}
            {t === "PROBLEMS" && errors.length > 0 && (
              <span style={{
                marginLeft:4, fontSize:9, background:"#f44747",
                color:"#fff", padding:"0 4px", borderRadius:8,
              }}>{errors.length}</span>
            )}
          </div>
        ))}
        <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:10, padding:"0 12px" }}>
          <button
            onClick={() => window.open("https://console.aws.amazon.com/cloudshell/home", "_blank")}
            style={{
              background: "#3c3c3c", color: "#cccccc", border: "none",
              padding: "2px 8px", borderRadius: 3, cursor: "pointer",
              fontSize: 10, display: "flex", alignItems: "center", gap: 4
            }}
          >
            💻 Open Cloud Shell
          </button>
          <span style={{ fontSize:11, color:"#555" }}>
            nexusswarm — agent pipeline {taskTitle ? `· ${taskTitle.slice(0,40)}` : ""}
          </span>
        </div>
      </div>

      {/* TERMINAL tab */}
      {tab === "TERMINAL" && (
        <div style={{
          flex:1, overflowY:"auto", padding:"6px 12px",
          fontFamily:"'Cascadia Code','Fira Code','Consolas',monospace",
          fontSize:12, lineHeight:"1.7", background:"#1e1e1e",
        }}>
          <div style={{ color:"#4ec9b0", marginBottom:6 }}>
            NexusSwarm v1.0.0 — 28 agents loaded | NVIDIA NIM active
          </div>
          <div style={{ color:"#333", marginBottom:8 }}>
            {"─".repeat(56)}
          </div>

          {events.length === 0 && (
            <div style={{ color:"#555" }}>
              Waiting for task... Open command palette (Ctrl+Shift+P) to launch swarm.
            </div>
          )}

          {[...events].reverse().map((log, i) => {
            const prefix = STATUS_PREFIX[log.status] ?? "○"
            const color  = log.status === "error" || log.status === "blocked"
              ? "#f44747" : LEVEL_COLOR[log.agent_level] ?? "#9cdcfe"
            return (
              <div key={log.event_id ?? i} style={{ display:"flex", gap:8, marginBottom:1 }}>
                <span style={{ color:"#444", flexShrink:0, minWidth:64, fontFamily:"monospace" }}>
                  {new Date(log.timestamp).toLocaleTimeString("en-US",{hour12:false})}
                </span>
                <span style={{ color, flexShrink:0, width:14 }}>{prefix}</span>
                <span style={{ color, flexShrink:0, minWidth:170 }}>[{log.agent_name}]</span>
                <span style={{ color: log.event_type === "complete" ? "#4ec94e" : "#d4d4d4" }}>
                  {log.message}
                </span>
              </div>
            )
          })}
          <div ref={bottomRef} />
        </div>
      )}

      {/* OUTPUT tab */}
      {tab === "OUTPUT" && (
        <div style={{ flex:1, overflowY:"auto", padding:"8px 12px", fontFamily:"monospace", fontSize:11, background:"#1e1e1e", color:"#888" }}>
          <div style={{ color:"#555", marginBottom:8 }}>nexusswarm agent output stream</div>
          {events.filter(e => e.payload?.output).map((e, i) => (
            <div key={i} style={{ marginBottom:4 }}>
              <span style={{ color:"#6366f1" }}>[{e.agent_name}]</span>
              <span style={{ color:"#555" }}> {String(e.payload!.output).slice(0, 120)}…</span>
            </div>
          ))}
        </div>
      )}

      {/* PROBLEMS tab */}
      {tab === "PROBLEMS" && (
        <div style={{ flex:1, overflowY:"auto", padding:"8px 12px", fontFamily:"monospace", fontSize:11, background:"#1e1e1e" }}>
          {errors.length === 0
            ? <div style={{ color:"#4ec94e" }}>✓ No problems detected</div>
            : errors.map((e, i) => (
              <div key={i} style={{ color:"#f44747", marginBottom:4 }}>
                ✗ [{e.agent_name}] {e.message}
              </div>
            ))
          }
        </div>
      )}

      {/* DEBUG tab */}
      {tab === "DEBUG" && (
        <div style={{ flex:1, overflowY:"auto", padding:"8px 12px", fontFamily:"monospace", fontSize:11, background:"#1e1e1e", color:"#555" }}>
          Debug console — no active debug session.
        </div>
      )}
    </div>
  )
}
