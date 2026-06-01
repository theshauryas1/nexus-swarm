// components/IDE/ActivityBar.tsx — VS Code left icon strip

type Panel = "agents" | "files" | "outputs" | "pipelines" | "leaderboard"

interface Props { active: Panel; onSelect: (p: Panel) => void }

const ITEMS: { id: Panel; icon: string; label: string }[] = [
  { id: "agents",    icon: "⬡",  label: "Agents"    },
  { id: "files",     icon: "🗂️", label: "Files"     },
  { id: "outputs",   icon: "📄",  label: "Outputs"   },
  { id: "pipelines", icon: "⚡",  label: "Pipelines" },
  { id: "leaderboard", icon: "🏆", label: "Leaderboard" },
]

export function ActivityBar({ active, onSelect }: Props) {
  return (
    <div style={{
      width: 48, background: "#333333",
      display: "flex", flexDirection: "column",
      alignItems: "center", paddingTop: 4, gap: 2,
      borderRight: "1px solid #3c3c3c", flexShrink: 0,
    }}>
      {ITEMS.map(item => (
        <div
          key={item.id}
          title={item.label}
          onClick={() => onSelect(item.id)}
          style={{
            width: 48, height: 48,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, cursor: "pointer",
            color:      active === item.id ? "#ffffff" : "#858585",
            borderLeft: active === item.id ? "2px solid #6366f1" : "2px solid transparent",
            background: active === item.id ? "#1e1e1e" : "transparent",
            transition: "all 0.1s",
          }}
          onMouseEnter={e => { if (active !== item.id) (e.currentTarget as HTMLElement).style.color = "#cccccc" }}
          onMouseLeave={e => { if (active !== item.id) (e.currentTarget as HTMLElement).style.color = "#858585" }}
        >
          {item.icon}
        </div>
      ))}

      <div style={{ marginTop: "auto", marginBottom: 8 }}>
        <div style={{
          width: 48, height: 48,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18, cursor: "pointer", color: "#858585",
        }}>⚙</div>
      </div>
    </div>
  )
}
