// components/IDE/CommandPalette.tsx — Ctrl+Shift+P overlay for task submission

import { useState, useEffect } from "react"
import { getApiErrorMessage, useNexusStore } from "../../store/agentStore"

interface Props { onClose: () => void }

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

const DEMOS = [
  "Build a secure REST API for task management with JWT authentication and PostgreSQL",
  "Create a real-time chat application with WebSocket support and user rooms",
  "Build an e-commerce backend with payment integration and inventory tracking",
  "Create a ML model serving API with FastAPI, batch inference, and rate limiting",
  "Build a microservices auth system with OAuth2, refresh tokens, and RBAC",
]

export function CommandPalette({ onClose }: Props) {
  const [input, setInput]   = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState<string | null>(null)

  const setTaskId = useNexusStore(s => s.setTaskId)
  const setApiError = useNexusStore(s => s.setApiError)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const launch = async (task: string) => {
    if (!task.trim() || loading) return
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API}/submit-task`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: task.trim(), description: "", priority: 1 }),
      })
      if (!res.ok) {
        throw new Error(await getApiErrorMessage(res))
      }
      const data = await res.json()
      setTaskId(data.task_id, task.trim())
      setApiError(null)
      onClose()
    } catch (e) {
      const message = (e as Error).message
      setError(message)
      setApiError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.65)", backdropFilter: "blur(2px)",
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        paddingTop: 60,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 600, background: "#252526",
          border: "1px solid #6366f1", borderRadius: 6,
          overflow: "hidden", boxShadow: "0 16px 48px rgba(0,0,0,0.7)",
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Input row */}
        <div style={{
          display:"flex", alignItems:"center", gap:10,
          padding:"10px 14px", borderBottom:"1px solid #3c3c3c",
        }}>
          <span style={{ color: "#6366f1", fontSize: 16 }}>⬡</span>
          <input
            autoFocus
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") launch(input) }}
            placeholder="Describe what to build... (Enter to launch swarm)"
            style={{
              flex:1, background:"transparent", border:"none",
              outline:"none", color:"#cccccc", fontSize:13,
              fontFamily:"inherit",
            }}
          />
          {loading
            ? <span style={{ color:"#6366f1", fontSize:12 }}>Launching…</span>
            : <kbd style={{ fontSize:10, color:"#555", border:"1px solid #555", borderRadius:3, padding:"1px 5px" }}>Esc</kbd>
          }
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding:"6px 14px", background:"#5a1d1d", fontSize:11, color:"#f44747" }}>
            ✗ {error}
          </div>
        )}

        {/* Demo suggestions */}
        <div style={{ padding:"6px 0" }}>
          <div style={{ padding:"4px 14px", fontSize:10, color:"#555", letterSpacing:"0.08em" }}>
            DEMO TASKS
          </div>
          {DEMOS.map((demo, i) => (
            <div key={i}
              onClick={() => launch(demo)}
              style={{
                padding:"7px 14px", fontSize:12,
                color:"#cccccc", cursor:"pointer",
                display:"flex", alignItems:"flex-start", gap:10,
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "#094771")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ color:"#555", flexShrink:0 }}>▶</span>
              {demo}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding:"7px 14px", borderTop:"1px solid #3c3c3c",
          fontSize:10, color:"#555", display:"flex", gap:16,
        }}>
          <span><kbd style={{ border:"1px solid #555", borderRadius:3, padding:"1px 4px" }}>↵</kbd> Launch swarm</span>
          <span><kbd style={{ border:"1px solid #555", borderRadius:3, padding:"1px 4px" }}>Esc</kbd> Close</span>
        </div>
      </div>
    </div>
  )
}
