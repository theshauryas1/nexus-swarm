import React from 'react';
import { useNexusStore } from '../../store/agentStore';

export function IntroPage() {
  const navigate = useNexusStore((s) => s.navigate);

  return (
    <div className="page-transition min-h-screen w-screen bg-[#030303] text-white flex flex-col justify-between p-8 font-sans selection:bg-[#73ffb9] selection:text-[#030303]">
      {/* Header */}
      <header className="flex justify-between items-center max-w-6xl mx-auto w-full border-b border-[#e5e7eb]/10 pb-6">
        <div className="flex items-center gap-2">
          <span className="text-[#73ffb9] text-2xl font-bold tracking-wider">⬡</span>
          <span className="font-semibold tracking-tight text-lg font-pp-neue-montreal">Decide AI</span>
        </div>
        <nav className="flex items-center gap-6">
          <a
            href="https://decideai.xyz"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-[#e5e7eb]/70 hover:text-white transition"
          >
            decideai.xyz
          </a>
          <button
            onClick={() => navigate('login')}
            className="text-xs px-4 py-2 border border-[#e5e7eb] rounded-full text-white bg-transparent hover:border-[#73ffb9] hover:text-[#73ffb9] transition-all duration-300 font-medium"
          >
            Launch Swarm
          </button>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center max-w-4xl mx-auto px-4 py-16">
        {/* Stark Initializer Tag */}
        <div className="inline-flex items-center gap-2 border border-[#73ffb9]/30 px-3 py-1 rounded-full bg-[#030303] text-xs font-semibold text-[#73ffb9] uppercase tracking-widest mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-[#73ffb9] status-dot-active" />
          Autonomic Software Swarms
        </div>

        {/* Gigantic Crisp Heading */}
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-6 leading-tight select-none">
          The future of <br className="hidden md:inline" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-[#73ffb9]">
            swarm intelligence.
          </span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg md:text-xl text-[#e5e7eb]/70 font-light max-w-2xl mb-10 leading-relaxed">
          NexusSwarm mirrors corporate execution structures. 28 autonomous agents, 7 resizable pipelines, and real terminal diagnostics loops.
        </p>

        {/* Ghost Border CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 justify-center">
          <button
            onClick={() => navigate('login')}
            className="px-8 py-3.5 border border-[#e5e7eb] rounded-full bg-white text-[#030303] hover:bg-transparent hover:text-white hover:border-[#73ffb9] text-sm font-semibold transition-all duration-300 shadow-lg hover:shadow-[#73ffb9]/10"
          >
            Enter Workspace
          </button>
          <a
            href="file:///c:/hack/docs/PRD.md"
            target="_blank"
            rel="noreferrer"
            className="px-8 py-3.5 border border-[#e5e7eb]/35 rounded-full text-white bg-transparent hover:border-[#e5e7eb] hover:bg-white/5 text-sm font-medium transition-all duration-300"
          >
            Read Specifications
          </a>
        </div>
      </main>

      {/* Feature Cards Section (3-Column Grid) */}
      <section className="max-w-6xl mx-auto w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="ledger-card flex flex-col justify-between group">
          <div>
            <div className="text-xs font-semibold text-[#73ffb9] mb-4 font-mono">01. ORCHESTRATION</div>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-[#73ffb9] transition-colors">
              Hierarchical Governance
            </h3>
            <p className="text-sm text-[#e5e7eb]/70 leading-relaxed font-light">
              Mirrors actual enterprise pipelines. The Head Orchestrator delegates workloads to specialized Managers and Workers.
            </p>
          </div>
          <div className="mt-6 border-t border-[#e5e7eb]/10 pt-4 flex justify-between items-center text-xs text-[#e5e7eb]/50">
            <span>Roster: 28 Specialists</span>
            <span>Active</span>
          </div>
        </div>

        <div className="ledger-card flex flex-col justify-between group">
          <div>
            <div className="text-xs font-semibold text-[#73ffb9] mb-4 font-mono">02. EXECUTION</div>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-[#73ffb9] transition-colors">
              Autonomic Terminals
            </h3>
            <p className="text-sm text-[#e5e7eb]/70 leading-relaxed font-light">
              Real shell commands running in decoupled cloud builds. Features interactive repair modules and self-correcting diagnostics loops.
            </p>
          </div>
          <div className="mt-6 border-t border-[#e5e7eb]/10 pt-4 flex justify-between items-center text-xs text-[#e5e7eb]/50">
            <span>Terminal: Bash Shell</span>
            <span>Self-Correcting</span>
          </div>
        </div>

        <div className="ledger-card flex flex-col justify-between group">
          <div>
            <div className="text-xs font-semibold text-[#73ffb9] mb-4 font-mono">03. ACCELERATION</div>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-[#73ffb9] transition-colors">
              Free Code Generation
            </h3>
            <p className="text-sm text-[#e5e7eb]/70 leading-relaxed font-light">
              Accelerate product delivery with standard high-parameter coder models running via NVIDIA NIM microservices on direct cloud servers.
            </p>
          </div>
          <div className="mt-6 border-t border-[#e5e7eb]/10 pt-4 flex justify-between items-center text-xs text-[#e5e7eb]/50">
            <span>Model: Qwen3-Coder 480B</span>
            <span>NVIDIA NIM</span>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full flex flex-col sm:flex-row justify-between items-center border-t border-[#e5e7eb]/10 pt-6 text-xs text-[#e5e7eb]/50 gap-4">
        <div>© 2026 Decide AI Inc. All rights reserved. Registered under W3C tokens.</div>
        <div className="flex gap-6">
          <span>Version 1.0.0</span>
          <span>Status: Server Online</span>
        </div>
      </footer>
    </div>
  );
}
