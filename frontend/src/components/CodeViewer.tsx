// NexusSwarm — CodeViewer (VS Code editor panel)
// Shows agent outputs as syntax-highlighted "files" with tab bar

import { useState, useEffect } from 'react'
import { X, Copy, CheckCircle2, FileCode2, FileText, File } from 'lucide-react'
import clsx from 'clsx'
import { useNexusStore } from '../store/agentStore'

// File icon per agent type
const FILE_ICON: Record<string, React.ElementType> = {
  BackendAgent:    FileCode2,
  APIAgent:        FileCode2,
  FrontendAgent:   FileCode2,
  TestAgent:       FileCode2,
  DeployAgent:     FileCode2,
  RepairAgent:     FileCode2,
  default:         FileText,
}

// File extension hint per agent
const FILE_EXT: Record<string, string> = {
  BackendAgent:        '.py',
  APIAgent:            '.yaml',
  FrontendAgent:       '.tsx',
  TestAgent:           '.py',
  DeployAgent:         'Dockerfile',
  RepairAgent:         '.py',
  RequirementAgent:    '.md',
  RiskAnalyzer:        '.md',
  ScannerAgent:        '.md',
  DiagnosticsAgent:    '.md',
  HeadOrchestrator:    '.json',
  KnowledgeMemoryAgent:'.md',
  default:             '.txt',
}

// Basic syntax colorizer (token-level, no full parser)
function colorize(code: string, ext: string): React.ReactNode[] {
  if (!ext.match(/\.(py|ts|tsx|js|yaml|json|md|dockerfile)/i) && ext !== 'Dockerfile') {
    return [<span key={0} className="text-slate-300">{code}</span>]
  }

  const lines = code.split('\n')
  return lines.map((line, i) => {
    let colored: React.ReactNode = line

    // Markdown headings
    if (ext === '.md') {
      if (line.startsWith('### ')) colored = <span className="text-brand-300 font-bold">{line}</span>
      else if (line.startsWith('## ')) colored = <span className="text-brand-200 font-bold text-sm">{line}</span>
      else if (line.startsWith('# '))  colored = <span className="text-white font-bold text-base">{line}</span>
      else if (line.startsWith('- ') || line.startsWith('* '))
        colored = <span><span className="text-indigo-400">•</span><span className="text-slate-300">{line.slice(1)}</span></span>
      else if (line.startsWith('```')) colored = <span className="text-slate-600">{line}</span>
      else colored = <span className="text-slate-300">{line}</span>
    }
    // Python/JS: keywords, strings, comments
    else if (ext === '.py' || ext === '.ts' || ext === '.tsx' || ext === '.js') {
      if (line.trim().startsWith('#') || line.trim().startsWith('//')) {
        colored = <span className="text-slate-600 italic">{line}</span>
      } else if (line.includes('def ') || line.includes('class ') || line.includes('async ') || line.includes('function ') || line.includes('const ') || line.includes('import ') || line.includes('from ')) {
        colored = <span className="text-violet-300">{line}</span>
      } else if (line.includes('"') || line.includes("'")) {
        colored = <span className="text-amber-300">{line}</span>
      } else if (line.includes('return') || line.includes('if') || line.includes('for') || line.includes('while')) {
        colored = <span className="text-blue-300">{line}</span>
      } else {
        colored = <span className="text-slate-300">{line}</span>
      }
    }
    // YAML
    else if (ext === '.yaml' || ext === '.yml') {
      if (line.trim().startsWith('#')) colored = <span className="text-slate-600 italic">{line}</span>
      else if (line.includes(':')) {
        const [key, ...rest] = line.split(':')
        colored = <span><span className="text-blue-300">{key}</span><span className="text-slate-500">:</span><span className="text-amber-300">{rest.join(':')}</span></span>
      } else colored = <span className="text-slate-300">{line}</span>
    }
    // JSON
    else if (ext === '.json') {
      if (line.includes('"')) {
        colored = <span className="text-amber-300">{line}</span>
      } else if (line.match(/true|false|null|\d+/)) {
        colored = <span className="text-cyan-300">{line}</span>
      } else {
        colored = <span className="text-slate-300">{line}</span>
      }
    } else {
      colored = <span className="text-slate-300">{line}</span>
    }

    return (
      <div key={i} className="flex">
        <span className="select-none text-right w-10 pr-3 text-slate-700 text-[10px] leading-5 flex-shrink-0 font-mono">
          {i + 1}
        </span>
        <span className="flex-1 text-[11px] leading-5 font-mono break-all">{colored}</span>
      </div>
    )
  })
}

interface Props {
  activeAgent: string | null
  onCloseTab:  (name: string) => void
  openTabs:    string[]
  onTabClick:  (name: string) => void
}

export function CodeViewer({ activeAgent, onCloseTab, openTabs, onTabClick }: Props) {
  const outputItems = useNexusStore((s) => s.outputItems)
  const [copied, setCopied] = useState(false)

  const activeOutput = outputItems.find(o => o.agent === activeAgent)
  const ext = activeAgent ? (FILE_EXT[activeAgent] ?? FILE_EXT.default) : '.txt'
  const IconComp = activeAgent ? (FILE_ICON[activeAgent] ?? FILE_ICON.default) : File

  const copyContent = () => {
    if (activeOutput) {
      navigator.clipboard.writeText(activeOutput.content).catch(() => {})
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  // Auto-open new tabs when outputItems arrives
  const newItemAgents = outputItems.map(o => o.agent)
  
  return (
    <div className="flex flex-col h-full overflow-hidden bg-ide-editor">
      {/* Tab bar */}
      <div className="flex items-center bg-ide-tabbar border-b border-ide-border flex-shrink-0 overflow-x-auto scrollbar-hide min-h-[35px]">
        {openTabs.length === 0 ? (
          <div className="px-4 py-2 text-[11px] text-slate-600 italic">
            No files open — select an agent or wait for pipeline to start
          </div>
        ) : (
          openTabs.map((agentName) => {
            const isActive = agentName === activeAgent
            const hasOutput = outputItems.some(o => o.agent === agentName)
            const agentExt = FILE_EXT[agentName] ?? '.txt'
            const AgentIcon = FILE_ICON[agentName] ?? FileText

            return (
              <div
                key={agentName}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2 border-r border-ide-border cursor-pointer select-none flex-shrink-0 group',
                  'text-[11px] font-mono transition-all',
                  isActive
                    ? 'bg-ide-editor text-white border-t-2 border-t-indigo-500'
                    : 'bg-ide-tabbar text-slate-500 hover:text-slate-300 hover:bg-ide-tabbar-hover',
                )}
                onClick={() => onTabClick(agentName)}
              >
                <AgentIcon size={11} className={isActive ? 'text-indigo-400' : 'text-slate-600'} />
                <span>{agentName}{agentExt}</span>
                {!hasOutput && isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); onCloseTab(agentName) }}
                  className="opacity-0 group-hover:opacity-100 hover:text-white ml-0.5 transition-opacity"
                >
                  <X size={10} />
                </button>
              </div>
            )
          })
        )}
        {/* Copy button */}
        {activeOutput && (
          <button
            onClick={copyContent}
            className="ml-auto mr-2 flex items-center gap-1 px-2 py-1 text-[10px] text-slate-500 hover:text-white transition-colors flex-shrink-0"
          >
            {copied ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>

      {/* Breadcrumb */}
      {activeAgent && (
        <div className="flex items-center gap-1.5 px-4 py-1 bg-ide-editor border-b border-ide-border/50 flex-shrink-0 text-[10px] text-slate-600">
          <span>nexusswarm</span>
          <span>›</span>
          <span>agents</span>
          <span>›</span>
          <span className="text-slate-400">{activeAgent}{ext}</span>
        </div>
      )}

      {/* Editor content */}
      <div className="flex-1 overflow-auto">
        {!activeAgent ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 select-none">
            <div className="text-center">
              <div className="text-6xl mb-4 opacity-20">⬡</div>
              <div className="text-slate-600 text-sm font-medium">NexusSwarm IDE</div>
              <div className="text-slate-700 text-xs mt-1">Submit a task or select an agent from the explorer</div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-700">
              {[
                ['Ctrl+Shift+P', 'Command Palette'],
                ['Submit Task', 'Top bar input'],
                ['Agent Explorer', 'Left sidebar'],
                ['Live Log', 'Right panel'],
              ].map(([key, val]) => (
                <div key={key} className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 rounded bg-surface-700 border border-surface-500 font-mono text-[9px]">{key}</kbd>
                  <span>{val}</span>
                </div>
              ))}
            </div>
          </div>
        ) : !activeOutput ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-8">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <IconComp size={20} className="text-indigo-400 animate-pulse" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-300">{activeAgent}</div>
              <div className="text-xs text-slate-600 mt-1">
                {/* Status-driven message */}
                Waiting for agent output...
              </div>
            </div>
          </div>
        ) : (
          <div className="p-0">
            {/* Line number + code area */}
            <div className="py-2">
              {colorize(activeOutput.content, ext)}
            </div>
          </div>
        )}
      </div>

      {/* Editor status bar row */}
      {activeOutput && (
        <div className="flex items-center justify-between px-4 py-0.5 bg-ide-statusbar text-[10px] text-indigo-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            <span>{ext.replace('.', '').toUpperCase() || 'TEXT'}</span>
            <span>{activeOutput.content.split('\n').length} lines</span>
            <span>{activeOutput.content.length} chars</span>
          </div>
          <div className="flex items-center gap-3">
            <span>UTF-8</span>
            <span>Spaces: 2</span>
          </div>
        </div>
      )}
    </div>
  )
}
