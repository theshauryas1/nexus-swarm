import React, { useState, useEffect, useRef } from 'react';
import { TitleBar } from '../IDE/TitleBar';
import { ActivityBar } from '../IDE/ActivityBar';
import { AgentTreePanel } from '../IDE/AgentTreePanel';
import { EditorArea } from '../IDE/EditorArea';
import { IDETerminalPanel } from '../IDE/IDETerminalPanel';
import { StatusBar } from '../IDE/StatusBar';
import { CommandPalette } from '../IDE/CommandPalette';
import { useNexusStore, safeGet } from '../../store/agentStore';

type Panel = 'agents' | 'files' | 'outputs' | 'pipelines' | 'leaderboard';

function ResizeHandle({ onDrag }: { onDrag: (dx: number) => void }) {
  const startX = useRef<number | null>(null);
  return (
    <div
      style={{ width: 4, cursor: 'col-resize', background: 'transparent', flexShrink: 0 }}
      onMouseDown={(e) => {
        startX.current = e.clientX;
        const onMove = (mv: MouseEvent) => {
          if (startX.current !== null) {
            onDrag(mv.clientX - startX.current);
            startX.current = mv.clientX;
          }
        };
        const onUp = () => {
          window.removeEventListener('mousemove', onMove);
          window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
      }}
    />
  );
}

function LiveLogPanel() {
  const events = useNexusStore((s) => s.events);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const LEVEL_COLOR: Record<string, string> = {
    orchestrator: '#73ffb9', // Terminal green accent
    manager: '#4ec9b0',
    gateway: '#c586c0',
    worker: '#9cdcfe',
  };

  const STATUS_DOT: Record<string, string> = {
    idle: '#555555',
    active: '#73ffb9',
    in_progress: '#73ffb9',
    done: '#4ec94e',
    error: '#f44747',
    blocked: '#f5a623',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#030303' }}>
      <div
        style={{
          padding: '6px 10px',
          fontSize: 11,
          fontWeight: 700,
          color: '#e5e7eb',
          letterSpacing: '0.1em',
          borderBottom: '1px solid #e5e7eb',
          userSelect: 'none',
          flexShrink: 0,
          background: '#030303',
        }}
      >
        NEXUSSWARM LIVE LOGS
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '6px 8px',
          fontFamily: "'Cascadia Code','Fira Code','Consolas',monospace",
          fontSize: 11,
          lineHeight: '1.6',
        }}
      >
        {events.length === 0 && (
          <div style={{ color: '#555555', padding: '8px 0', fontStyle: 'italic' }}>
            Waiting for swarm actions...
          </div>
        )}
        {[...events].reverse().map((ev, i) => (
          <div
            key={ev.event_id ?? i}
            className="log-entry"
            style={{
              display: 'flex',
              gap: 6,
              alignItems: 'flex-start',
              marginBottom: 4,
              padding: '2px 4px',
              borderRadius: 3,
            }}
          >
            {/* Status dot */}
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                flexShrink: 0,
                background: safeGet(STATUS_DOT, ev.status) ?? '#555555',
                marginTop: 4,
                boxShadow:
                  ev.status === 'active' || ev.status === 'in_progress'
                    ? `0 0 5px ${safeGet(STATUS_DOT, ev.status)}`
                    : 'none',
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 4 }}>
                <span
                  style={{
                    color: safeGet(LEVEL_COLOR, ev.agent_level) ?? '#9cdcfe',
                    fontSize: 10,
                    fontWeight: 600,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {ev.agent_name}
                </span>
                <span style={{ color: '#555555', fontSize: 9, flexShrink: 0 }}>
                  {new Date(ev.timestamp).toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </div>
              <div
                style={{
                  color: ev.status === 'error' ? '#f44747' : ev.event_type === 'complete' ? '#73ffb9' : '#e5e7eb',
                  fontSize: 10,
                  wordBreak: 'break-word',
                }}
              >
                {ev.message}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function WorkspacePage() {
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [terminalHeight, setTerminalHeight] = useState(220);
  const [activePanel, setActivePanel] = useState<Panel>('agents');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const user = useNexusStore((s) => s.user);
  const navigate = useNexusStore((s) => s.navigate);

  // Ctrl+Shift+P → open palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        setPaletteOpen((p) => !p);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div
      className="page-transition"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        background: '#030303',
        color: '#ffffff',
        fontFamily: "'Inter', system-ui, sans-serif",
        overflow: 'hidden',
      }}
    >
      {/* ── Title bar with Search & User Profile ── */}
      <TitleBar onOpenPalette={() => setPaletteOpen(true)} />

      {/* ── Main area ── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', borderBottom: '1px solid #e5e7eb' }}>
        {/* Activity bar */}
        <ActivityBar active={activePanel} onSelect={setActivePanel} />

        {/* Sidebar — agent tree / session explorer */}
        <div
          style={{
            width: sidebarWidth,
            minWidth: 160,
            maxWidth: 480,
            background: '#030303',
            borderRight: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          <AgentTreePanel activePanel={activePanel} />
        </div>

        {/* Drag handle */}
        <ResizeHandle onDrag={(dx) => setSidebarWidth((w) => Math.max(160, Math.min(480, w + dx)))} />

        {/* Centre + right column */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Editor row */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* Monaco editor */}
            <EditorArea style={{ flex: 1 }} />

            {/* Right live-log */}
            <div
              style={{
                width: 280,
                background: '#030303',
                borderLeft: '1px solid #e5e7eb',
                display: 'flex',
                flexDirection: 'column',
                flexShrink: 0,
              }}
            >
              <LiveLogPanel />
            </div>
          </div>

          {/* Terminal bottom panel (resizable) */}
          <div
            style={{
              height: terminalHeight,
              minHeight: 80,
              maxHeight: 520,
              borderTop: '1px solid #e5e7eb',
              background: '#030303',
              flexShrink: 0,
            }}
          >
            {/* Resize top edge */}
            <div
              style={{ height: 4, cursor: 'row-resize', background: 'transparent' }}
              onMouseDown={(e) => {
                const startY = e.clientY;
                const startH = terminalHeight;
                const onMove = (mv: MouseEvent) =>
                  setTerminalHeight(Math.max(80, Math.min(520, startH - (mv.clientY - startY))));
                const onUp = () => {
                  window.removeEventListener('mousemove', onMove);
                  window.removeEventListener('mouseup', onUp);
                };
                window.addEventListener('mousemove', onMove);
                window.addEventListener('mouseup', onUp);
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
  );
}
