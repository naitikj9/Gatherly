import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FileText, Search, CalendarRange, ShieldCheck, Gauge, Wand2 } from "lucide-react";
import { cn } from "../lib/utils";

const ICONS = {
  intake: FileText,
  research: Search,
  planner: CalendarRange,
  insights: Gauge,
  compliance: ShieldCheck,
  optimizer: Wand2,
};

// Determine each node's state based on what's available in the result state
function computeNodeStates(state, logs, running) {
  const visited = new Set(
    (logs || []).map((l) => (l.node === "venue" ? "research" : l.node))
  );
  const order = ["intake", "research", "planner", "insights", "compliance"];
  const out = {};
  for (const id of order) {
    if (visited.has(id)) out[id] = "done";
    else out[id] = "idle";
  }
  // mark the next idle as 'running' when we're still in-flight
  if (running) {
    for (const id of order) {
      if (out[id] === "idle") {
        out[id] = "running";
        break;
      }
    }
  }
  // the optimizer only runs when a plan is over budget
  out["optimizer"] = visited.has("optimizer") ? "done" : "idle";
  // refusal/reject paths
  if (state?.status === "refused") {
    out["intake"] = "fail";
  }
  if (state?.status === "rejected") {
    if (!state?.shortlist?.venue) out["research"] = "fail";
    else out["compliance"] = "fail";
  }
  return out;
}

export default function Pipeline({ state, logs, running, architecture }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTick((x) => x + 1), 300);
    return () => clearInterval(t);
  }, [running]);

  const nodeStates = computeNodeStates(state, logs, running);
  const nodes = architecture?.nodes || [
    { id: "intake", label: "Intake", role: "Parse + safety screen" },
    { id: "research", label: "Vendor & RAG", role: "Catalog search → select vendors" },
    { id: "planner", label: "Planner", role: "Timeline + exact budget" },
    { id: "insights", label: "Insights", role: "Weather, checklist, health score" },
    { id: "compliance", label: "Compliance", role: "Policy + safety gate" },
    { id: "optimizer", label: "Budget Optimizer", role: "Self-heals over-budget plans" },
  ];

  return (
    <section className="border-b hairline" data-testid="pipeline-section">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8">
        <div className="flex items-baseline justify-between mb-4">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan">
              &gt; ORCHESTRATION_GRAPH
            </p>
            <h3 className="font-bold text-lg tracking-tight mt-0.5">
              Multi-agent execution pipeline
            </h3>
          </div>
          <div className="hidden md:flex items-center gap-3 text-[11px] font-mono uppercase text-ink-muted">
            <LegendDot color="#52525B" label="idle" />
            <LegendDot color="#00F0FF" label="running" pulse />
            <LegendDot color="#22C55E" label="done" />
            <LegendDot color="#EF4444" label="failed" />
          </div>
        </div>

        <div className="hairline bg-bg-surface/50 rounded-sm p-5 md:p-7 relative overflow-hidden">
          <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
          <div className="relative flex flex-col md:flex-row md:items-stretch gap-4 md:gap-0">
            {nodes.map((n, i) => {
              const Icon = ICONS[n.id] || FileText;
              const st = nodeStates[n.id];
              return (
                <React.Fragment key={n.id}>
                  <NodeBox
                    idx={i}
                    icon={<Icon size={22} />}
                    label={n.label}
                    role={n.role}
                    state={st}
                  />
                  {i < nodes.length - 1 && (
                    <Connector active={nodeStates[nodes[i + 1].id] !== "idle" || st === "done"} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function NodeBox({ idx, icon, label, role, state }) {
  const palette = {
    idle: { ring: "border-white/15", dot: "bg-ink-muted", text: "text-ink-secondary", glow: "" },
    running: { ring: "border-accent-cyan", dot: "bg-accent-cyan animate-pulse", text: "text-accent-cyan", glow: "shadow-glowCyan" },
    done: { ring: "border-accent-green/70", dot: "bg-accent-green", text: "text-ink-primary", glow: "shadow-glowGreen" },
    fail: { ring: "border-accent-red", dot: "bg-accent-red", text: "text-accent-red", glow: "" },
  }[state];

  return (
    <div
      data-testid={`node-${idx}`}
      data-state={state}
      className={cn(
        "relative bg-black hairline rounded-sm p-4 transition-all duration-300 z-10 flex-1",
        palette.ring,
        palette.glow,
        state === "running" ? "border-accent-cyan" : "",
      )}
      style={{ borderColor: state === "running" ? "#00F0FF" : state === "done" ? "rgba(34,197,94,0.4)" : state === "fail" ? "#EF4444" : "" }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className={cn("font-mono text-[10px] uppercase tracking-widest", palette.text)}>
          NODE_{String(idx).padStart(2, "0")}
        </span>
        <span className={cn("w-2 h-2 rounded-full", palette.dot)} />
      </div>
      <div className={cn("text-accent-orange", state === "done" && "text-accent-green", state === "fail" && "text-accent-red")}>
        {icon}
      </div>
      <div className="mt-3">
        <div className={cn("font-bold text-[15px] tracking-tight", palette.text)}>{label}</div>
        <div className="font-mono text-[11px] text-ink-muted mt-1 leading-snug">{role}</div>
      </div>
      <div className="mt-3 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
        STATUS: <span className={cn(palette.text)}>{state}</span>
      </div>
    </div>
  );
}

function Connector({ active }) {
  return (
    <div className="hidden md:flex items-center justify-center w-8">
      <svg width="32" height="40" viewBox="0 0 32 40" className="overflow-visible">
        <line
          x1="0"
          y1="20"
          x2="32"
          y2="20"
          stroke={active ? "#F97316" : "#3a3a3a"}
          strokeWidth="1.5"
          strokeDasharray={active ? "0" : "4 4"}
          className={active ? "" : "edge-dash"}
        />
        <polygon
          points="28,16 32,20 28,24"
          fill={active ? "#F97316" : "#3a3a3a"}
        />
      </svg>
    </div>
  );
}

function LegendDot({ color, label, pulse }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn("w-2 h-2 rounded-full", pulse && "animate-pulse")}
        style={{ background: color }}
      />
      <span>{label}</span>
    </span>
  );
}
