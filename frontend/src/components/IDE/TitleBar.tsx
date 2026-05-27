// components/IDE/TitleBar.tsx — Windows-style title bar with menu + command palette trigger

interface Props { onOpenPalette: () => void }

export function TitleBar({ onOpenPalette }: Props) {
  return (
    <div style={{
      height: 32, background: "#252526",
      display: "flex", alignItems: "center",
      justifyContent: "space-between",
      borderBottom: "1px solid #3c3c3c",
      userSelect: "none", flexShrink: 0,
    }}>
      {/* Left — hex icon + menu items */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <div style={{
          width: 32, height: 32, display: "flex",
          alignItems: "center", justifyContent: "center",
          fontSize: 16, color: "#6366f1",
        }}>⬡</div>

        {["File","Edit","View","Run","Terminal","Help"].map(m => (
          <div key={m} style={{
            padding: "0 8px", fontSize: 12,
            color: "#cccccc", cursor: "pointer", height: 32,
            display: "flex", alignItems: "center",
          }}
          onMouseEnter={e => (e.currentTarget.style.background = "#3c3c3c")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >{m}</div>
        ))}
      </div>

      {/* Centre — command palette trigger */}
      <div
        onClick={onOpenPalette}
        style={{
          background: "#3c3c3c", borderRadius: 4,
          padding: "3px 80px", fontSize: 12,
          color: "#8c8c8c", cursor: "pointer",
          display: "flex", alignItems: "center", gap: 8,
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 11 }}>🔍</span>
        NexusSwarm — Hierarchical Agent Orchestration
      </div>

      {/* Right — Windows controls */}
      <div style={{ display: "flex" }}>
        {[
          { label: "─", danger: false },
          { label: "□", danger: false },
          { label: "✕", danger: true  },
        ].map(btn => (
          <div key={btn.label} style={{
            width: 46, height: 32,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, cursor: "pointer", color: "#cccccc",
            transition: "background 0.1s",
          }}
          onMouseEnter={e => (e.currentTarget.style.background = btn.danger ? "#e81123" : "#3c3c3c")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >{btn.label}</div>
        ))}
      </div>
    </div>
  )
}
