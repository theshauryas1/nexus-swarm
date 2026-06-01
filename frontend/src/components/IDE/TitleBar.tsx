// components/IDE/TitleBar.tsx — Windows-style title bar with menu + command palette trigger
// Styled for Decide AI "Midnight Terminal" — Deep Space background, Terminal Green accent

import { useNexusStore } from "../../store/agentStore"

interface Props { onOpenPalette: () => void }

export function TitleBar({ onOpenPalette }: Props) {
  const user = useNexusStore(s => s.user)
  const navigate = useNexusStore(s => s.navigate)

  return (
    <div style={{
      height: 36, background: "#030303",
      display: "flex", alignItems: "center",
      justifyContent: "space-between",
      borderBottom: "1px solid rgba(229,231,235,0.12)",
      userSelect: "none", flexShrink: 0,
      paddingRight: 4,
    }}>
      {/* Left — hex icon + Decide AI brand + menu items */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <div style={{
          width: 36, height: 36, display: "flex",
          alignItems: "center", justifyContent: "center",
          fontSize: 17, color: "#73ffb9",
          borderRight: "1px solid rgba(229,231,235,0.08)",
        }}>⬡</div>

        <span style={{
          fontSize: 12, fontWeight: 600,
          color: "#ffffff", letterSpacing: "0.02em",
          padding: "0 12px 0 10px",
          borderRight: "1px solid rgba(229,231,235,0.08)",
          height: 36, display: "flex", alignItems: "center",
          fontFamily: "'Inter', system-ui, sans-serif",
        }}>
          Decide AI
        </span>

        {["File","Edit","View","Run","Terminal","Help"].map(m => (
          <div key={m} style={{
            padding: "0 10px", fontSize: 12,
            color: "#888888", cursor: "pointer", height: 36,
            display: "flex", alignItems: "center",
            transition: "color 0.15s",
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = "rgba(229,231,235,0.06)"
            e.currentTarget.style.color = "#ffffff"
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = "transparent"
            e.currentTarget.style.color = "#888888"
          }}
          >{m}</div>
        ))}
      </div>

      {/* Centre — command palette trigger */}
      <div
        onClick={onOpenPalette}
        style={{
          background: "rgba(229,231,235,0.05)", border: "1px solid rgba(229,231,235,0.10)",
          borderRadius: 5, padding: "4px 64px", fontSize: 11,
          color: "#555555", cursor: "pointer",
          display: "flex", alignItems: "center", gap: 6,
          flexShrink: 0, transition: "border-color 0.2s, color 0.2s",
          fontFamily: "'JetBrains Mono', 'Consolas', monospace",
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = "#73ffb9"
          e.currentTarget.style.color = "#888888"
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = "rgba(229,231,235,0.10)"
          e.currentTarget.style.color = "#555555"
        }}
      >
        <span style={{ fontSize: 10, color: "#73ffb9" }}>⌕</span>
        NexusSwarm · Ctrl+Shift+P
      </div>

      {/* Right — user avatar + window controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {user && (
          <div
            onClick={() => navigate('intro')}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "0 8px", cursor: "pointer",
              borderRight: "1px solid rgba(229,231,235,0.08)",
              height: 36,
            }}
            title={`Signed in as ${user.email}`}
          >
            <img
              src={user.picture || 'https://www.gravatar.com/avatar/?d=mp'}
              alt={user.name}
              style={{ width: 20, height: 20, borderRadius: "50%", objectFit: "cover" }}
            />
            <span style={{ fontSize: 11, color: "#888888", maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {user.name}
            </span>
          </div>
        )}

        {[
          { label: "─", danger: false },
          { label: "□", danger: false },
          { label: "✕", danger: true  },
        ].map(btn => (
          <div key={btn.label} style={{
            width: 40, height: 36,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, cursor: "pointer", color: "#666666",
            transition: "background 0.1s, color 0.1s",
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = btn.danger ? "#c0392b" : "rgba(229,231,235,0.08)"
            e.currentTarget.style.color = "#ffffff"
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = "transparent"
            e.currentTarget.style.color = "#666666"
          }}
          >{btn.label}</div>
        ))}
      </div>
    </div>
  )
}
