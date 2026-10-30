import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...args) => twMerge(clsx(args));

/** ₹ formatter — Indian grouping (1,00,000). */
export const inr = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  try {
    return "₹" + Number(n).toLocaleString("en-IN");
  } catch {
    return "₹" + n;
  }
};

export const shortINR = (n) => {
  if (!n && n !== 0) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)}L`;
  if (n >= 1e3) return `₹${(n / 1e3).toFixed(1)}k`;
  return `₹${n}`;
};

/** Map node id -> human label */
export const NODE_LABEL = {
  intake: "INTAKE",
  research: "VENDOR · RAG",
  planner: "PLANNER",
  insights: "INSIGHTS",
  compliance: "COMPLIANCE",
  optimizer: "OPTIMIZER",
  refusal: "REFUSE",
  reject: "REJECT",
  human_approval: "HITL",
  declined: "DECLINED",
  finalize: "FINALIZE",
  venue: "VENDOR · RAG",
};

export const STATUS_META = {
  booked: { label: "BOOKED", tone: "green" },
  awaiting_approval: { label: "AWAITING APPROVAL", tone: "amber" },
  needs_approval: { label: "AWAITING APPROVAL", tone: "amber" },
  refused: { label: "REFUSED", tone: "red" },
  rejected: { label: "REJECTED", tone: "red" },
  declined: { label: "DECLINED", tone: "red" },
  running: { label: "RUNNING", tone: "cyan" },
};

/** Returns the ordered set of agent nodes the run visited. */
export const visitedNodes = (logs = []) => {
  const order = ["intake", "venue", "planner", "insights", "compliance", "optimizer"];
  const visited = new Set(
    logs.map((l) => (l.node === "venue" ? "venue" : l.node))
  );
  return order.filter((n) => visited.has(n));
};
