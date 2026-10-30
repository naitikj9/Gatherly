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

/** Human-friendlier label for a vendor's price unit. */
export const unitLabel = (unit, cat) => {
  if (unit === "per_plate") return "per guest";
  if (unit === "per_day") {
    if (cat === "venue") return "1-day rental";
    return "per day";
  }
  // flat
  if (cat === "decorator") return "package price";
  if (cat === "photographer") return "complete package";
  if (cat === "entertainment") return "full evening";
  return "package price";
};

/** Category-specific highlight line, pulled from the full catalog entry. */
export const vendorHighlights = (cat, entry) => {
  if (!entry) return null;
  if (cat === "venue") {
    const bits = [];
    if (entry.capacity) bits.push(`Seats up to ${entry.capacity}`);
    if (entry.setting) bits.push(entry.setting);
    if (entry.city) bits.push(entry.city);
    return bits.join(" · ");
  }
  if (cat === "caterer") {
    const bits = [];
    if (Array.isArray(entry.cuisine) && entry.cuisine.length) {
      bits.push(
        entry.cuisine
          .map((c) =>
            c.replace(/-/g, " ").replace(/\b\w/g, (m) => m.toUpperCase())
          )
          .join(", ")
      );
    }
    if (entry.diet) {
      const d = entry.diet
        .replace(/-/g, " ")
        .replace(/\bveg and nonveg\b/i, "Veg + Non-veg")
        .replace(/\bpure veg\b/i, "Pure veg")
        .replace(/\b\w/g, (m) => m.toUpperCase());
      bits.push(d);
    }
    return bits.join(" · ");
  }
  // decorator, entertainment, photographer → pretty tag list
  const tags = (entry.tags || []).filter(
    (t) =>
      !["budget", "premium", "small", "medium", "large", "luxury"].includes(t)
  );
  if (!tags.length) return null;
  return tags
    .slice(0, 4)
    .map((t) => t.replace(/-/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()))
    .join(" · ");
};
