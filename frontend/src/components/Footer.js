import React from "react";
import { Github, Terminal as TermIcon } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t hairline">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-[12.5px] text-ink-secondary">
        <div>
          <div className="flex items-center gap-2 text-ink-primary font-black tracking-tight text-base">
            <TermIcon size={14} className="text-accent-orange" />
            OBSIDIAN <span className="text-ink-muted font-normal">·</span>{" "}
            <span className="text-ink-secondary font-medium">GATHERLY</span>
          </div>
          <p className="mt-2 leading-relaxed">
            A 4-agent LangGraph system with RAG-grounded vendor selection,
            deterministic budgeting, policy compliance and a human-in-the-loop
            booking gate.
          </p>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-2">
            stack
          </div>
          <ul className="space-y-1 font-mono text-[12px]">
            <li>· LangGraph orchestration</li>
            <li>· FastAPI + MongoDB backend</li>
            <li>· React 18 frontend</li>
            <li>· Pydantic structured handoffs</li>
          </ul>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-muted mb-2">
            architecture
          </div>
          <p className="font-mono text-[12px] leading-relaxed">
            INTAKE → VENDOR · RAG → PLANNER → COMPLIANCE
            <br />
            with 4 conditional edges and 1 human gate.
          </p>
        </div>
      </div>
      <div className="border-t hairline px-6 lg:px-10 py-3 flex items-center justify-between text-[11px] font-mono text-ink-muted uppercase tracking-widest">
        <span>obsidian v1.0 · all bookings paused for human approval</span>
        <span className="flex items-center gap-1.5">
          <Github size={11} /> multiagent-event-planner
        </span>
      </div>
    </footer>
  );
}
