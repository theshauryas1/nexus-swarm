# ⬡ NexusSwarm — UI/UX Design Brief & App Flow

## 1. Design Aesthetics & Visual Identity
NexusSwarm's interface is modeled after a state-of-the-art, high-fidelity dark theme that blends modern software engineering design with premium aesthetic tokens. The interface is optimized to minimize cognitive load while providing maximum visual engagement.

```
┌────────────────────────────────────────────────────────────────────────┐
│  TITLEBAR (Command Palette, Swarm Health, Cloud Shell button)          │
├─────────┬───────────────────────────────────────────────┬──────────────┤
│  A   S  │  EDITOR TABS (welcome.md | backend.py [x])    │  LIVE        │
│  C   I  ├───────────────────────────────────────────────┤  LOG         │
│  T   D  │                                               │  FEED        │
│  I   E  │  MONACO CODE CANVAS                           │              │
│  V   B  │  (Syntax highlighting, line numbers)          │              │
│  I   A  │                                               │              │
│  T   R  ├───────────────────────────────────────────────┤              │
│  Y      │  TERMINAL DRAWER (resizable row-drag handle)  │              │
│         │  [TERMINAL] [OUTPUT] [PROBLEMS] [DEBUG]       │              │
└─────────┴───────────────────────────────────────────────┴──────────────┘
```

### 1.1. Color System (Curated Harmonies)
* **Backgrounds**: Slate Dark (`#1e1e1e` Editor Canvas, `#252526` Sidebars, `#1a1a2e` Flow canvas).
* **Borders & Grids**: Steel Gray (`#3c3c3c`).
* **Interactive Selections**: Deep Indigo Accent (`#6366f1` / `rgba(99, 102, 241, 0.05)`).
* **Tier-Specific Accents (Harmonious HSL Palette)**:
  * **Executive (Orchestration)**: Vibrant Violet (`#8b5cf6`) — represents top-tier command.
  * **Planning Manager**: Ice Blue (`#3b82f6`) — represents structure and logic.
  * **QA (Quality & Diagnostics)**: Electric Cyan (`#06b6d4`) — represents testing and verification.
  * **Security (Scanning & Verification)**: Safety Amber (`#f59e0b`) — represents audit compliance.
  * **DevOps (Containers & Releases)**: Emerald Green (`#10b981`) — represents growth and deployment.
  * **Reliability (Memory & Logs)**: Ocean Teal (`#14b8a6`) — represents performance.

### 1.2. Premium Typography
* **Primary Fonts**: Modern Sans-Serif (Inter, Roboto, Outfit) for headers, badges, and controls.
* **Code & Logs**: Monospace (Cascadia Code, Fira Code, Consolas) with custom line spacing (`line-height: 1.6`) for clear scannability.

---

## 2. Page Components & Layout Anatomy

### 2.1. TitleBar & Header Control
* **Command Palette Input**: Center-aligned dark search bar with magnifying glass trigger, displaying keyboard shortcuts `Ctrl+Shift+P`. Clicking expands a beautiful glassmorphic Command Palette overlay.
* **Open Cloud Shell Access**: Integrated button utilizing standard Google branding that triggers Google Cloud Shell in a dedicated browser tab, giving developers immediate terminal control.
* **Connection Status Pulse**: Glowing status badge (`bg-emerald-400` / `bg-red-400`) reflecting WebSocket connection state.

### 2.2. Vertical ActivityBar
* Leftmost compact bar containing high-contrast icons (Lucide library):
  * **Agent Graph icon** (Crown/Hexagon)
  * **Files Explorer icon** (Folders)
  * **Generated Outputs icon** (FileText)
  * **Pipeline Status icon** (Activity)
* Clicking an icon switches the active view inside the Sidebar panel instantly with smooth sliding transition animations.

### 2.3. Multi-Session Files Explorer (Left Sidebar)
* **Search / Filter Control**: A slick search bar allowing fuzzy matching across session task titles and generated code files.
* **Tree View Directory**:
  * Tasks/Sessions are displayed as collapsible directory folders (`📁` / `📂`) representing full project history.
  * Active sessions are highlighted with left border accents (`border-left: 2px solid #6366f1`).
  * Files nested inside task folders are displayed with specialized icons matching their development language (`🐍` Python, `⚛️` React TSX, etc.).
  * File size indicators (e.g. `2.5 KB`) are displayed on the right edge, matching typical VS Code explorer layouts.

### 2.4. Monaco Editor & Tabbed Workspace (Center Column)
* Tab bar displaying currently open files, complete with close handles (`x`).
* File tabs display the language icon matching the code file.
* Editor canvas embeds Monaco Editor with disabled minimaps for sleekness and custom dark-theme overrides matching VS Code's classic theme.
* Bottom status row shows language type, line counts, character counts, and tab size values.

### 2.5. Live Log Stream (Right Sidebar)
* Scroll-locked feed streaming WebSocket agent updates.
* Pulsing indicator dots showing which agents are active in real-time.
* Color-coded level badges (`ORCH`, `MGR`, `WORK`, `GATE`) matching pipeline managers and specialist workers.
* Age-relative timestamps representing log creation dates.

### 2.6. Resizable Terminal & Pipeline Drawer (Bottom Panel)
* Separated from the center editor by a resizable drag handle.
* Tab selection controls:
  * **Terminal**: Streaming raw command stdout/stderr.
  * **Output**: Compact dictionary of final agent files.
  * **Problems**: Logs any errors (`✗`) caught during execution.
  * **Debug**: A console for system monitoring.
* Pipeline health indicators rendering animated progress bars (`width: progress%`) matching the active pipeline colors.

---

## 3. Dynamic Interactive States & Animations

### 3.1. Pulsing Graph Nodes & Glowing Edges
* Active nodes inside the Agent Graph ReactFlow canvas show double pulsing rings using absolute CSS animations:
  ```css
  @keyframes nexus-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
    50%      { box-shadow: 0 0 0 8px rgba(99, 102, 241, 0.25); }
  }
  ```
* Edges (connecting arrows) transition from steel gray to animated glowing dotted lines showing flow of data between Managers and Specialist workers.

### 3.2. Micro-Animations & Hover States
* **Folder Toggle**: Directory icons rotate 90 degrees and fold/unfold with 150ms transitions.
* **Progress Bar Shimmer**: Active pipeline health bars have a glowing gradient shimmer running from left to right, indicating active processing.
* **Command Palette Entrance**: Palette slides down from the top header using absolute HSL transitions and backdrop-blur filters (`backdrop-filter: blur(12px)`).
