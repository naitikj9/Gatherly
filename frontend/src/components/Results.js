import React from "react";
import { motion } from "framer-motion";
import {
  MapPin,
  Utensils,
  Sparkles,
  Music,
  Camera,
  Users,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { cn, inr, shortINR, unitLabel, vendorHighlights } from "../lib/utils";
import PlanInsights from "./PlanInsights";

const CAT_ICON = {
  venue: MapPin,
  caterer: Utensils,
  decorator: Sparkles,
  entertainment: Music,
  photographer: Camera,
};

const VENUE_IMG = {
  outdoor:
    "https://images.unsplash.com/photo-1772127822531-6a279b5aa968?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjB3ZWRkaW5nJTIwb3V0ZG9vciUyMHZlbnVlfGVufDB8fHx8MTc4MjQ5NDgwN3ww&ixlib=rb-4.1.0&q=85",
  indoor:
    "https://images.unsplash.com/photo-1772127822525-7eda37383b9f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjB3ZWRkaW5nJTIwb3V0ZG9vciUyMHZlbnVlfGVufDB8fHx8MTc4MjQ5NDgwN3ww&ixlib=rb-4.1.0&q=85",
};

export default function Results({ state, catalog = {} }) {
  if (!state || !state.requirements) return null;
  const isFail =
    state.status === "refused" ||
    state.status === "rejected" ||
    state.status === "declined";

  return (
    <section className="border-b hairline" data-testid="results-section">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10">
        <div className="flex items-baseline justify-between mb-6">
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-accent-orange">
              &gt; FINAL_OUTPUT
            </p>
            <h3 className="font-black text-2xl md:text-3xl tracking-tight mt-1">
              {isFail ? "Run terminated" : "Costed plan ready"}
            </h3>
          </div>
          <StatusPill status={state.status} />
        </div>

        {isFail && (
          <FailureCard state={state} />
        )}

        {!isFail && state.shortlist && state.plan && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 space-y-4">
              <SummaryBar state={state} />
              <VendorGrid shortlist={state.shortlist} setting={state.requirements?.setting_preference} catalog={catalog} />
            </div>
            <div className="lg:col-span-4 space-y-4">
              <BudgetCard plan={state.plan} budget={state.requirements?.budget_inr} />
              <ComplianceCard compliance={state.compliance} />
              <TimelineCard items={state.plan.timeline || []} />
            </div>
            <div className="lg:col-span-12">
              <PlanInsights state={state} planId={state.plan_id} theme="dark" />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function StatusPill({ status }) {
  const map = {
    booked: { label: "BOOKED", icon: CheckCircle2, color: "text-accent-green border-accent-green/50" },
    awaiting_approval: { label: "AWAITING APPROVAL", icon: AlertTriangle, color: "text-accent-orange border-accent-orange/60" },
    refused: { label: "REFUSED", icon: XCircle, color: "text-accent-red border-accent-red/50" },
    rejected: { label: "REJECTED", icon: XCircle, color: "text-accent-red border-accent-red/50" },
    declined: { label: "DECLINED", icon: XCircle, color: "text-accent-red border-accent-red/50" },
  };
  const m = map[status] || { label: (status || "READY").toUpperCase(), icon: CheckCircle2, color: "text-ink-secondary border-white/20" };
  const Icon = m.icon;
  return (
    <span
      data-testid="status-pill"
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 hairline rounded-sm bg-bg-surface font-mono text-[11px] uppercase tracking-widest",
        m.color
      )}
    >
      <Icon size={13} /> {m.label}
    </span>
  );
}

function SummaryBar({ state }) {
  const r = state.requirements || {};
  return (
    <div className="hairline bg-bg-surface rounded-sm p-4 grid grid-cols-2 md:grid-cols-5 gap-4">
      <Field label="event" value={r.event_type || "—"} />
      <Field label="city" value={r.city || "—"} />
      <Field label="guests" value={`${r.guest_count || 0}`} icon={<Users size={12} />} />
      <Field label="date" value={r.event_date || "—"} icon={<Clock size={12} />} />
      <Field label="setting" value={r.setting_preference || "any"} />
    </div>
  );
}

function Field({ label, value, icon }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-widest text-ink-muted flex items-center gap-1">
        {icon} {label}
      </div>
      <div className="text-ink-primary font-medium text-sm mt-0.5 capitalize truncate">
        {value}
      </div>
    </div>
  );
}

function VendorGrid({ shortlist, setting, catalog }) {
  const cats = ["venue", "caterer", "decorator", "entertainment", "photographer"];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="vendor-grid">
      {cats.map((cat, i) => {
        const v = shortlist[cat];
        if (!v) return <EmptyVendor key={cat} cat={cat} />;
        return (
          <motion.div
            key={cat}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.06 }}
          >
            <VendorCard
              cat={cat}
              v={v}
              entry={catalog?.[v.id]}
              image={cat === "venue" ? VENUE_IMG[setting === "outdoor" ? "outdoor" : "indoor"] : null}
              idx={i}
            />
          </motion.div>
        );
      })}
    </div>
  );
}

function VendorCard({ cat, v, entry, image, idx }) {
  const Icon = CAT_ICON[cat] || MapPin;
  const unit = unitLabel(v.price_unit, cat);
  const highlights = vendorHighlights(cat, entry);
  return (
    <div data-testid={`vendor-card-${idx}`} className="hairline bg-bg-surface rounded-sm overflow-hidden hover:border-white/25 transition-colors group">
      {image && (
        <div
          className="h-32 w-full bg-cover bg-center relative"
          style={{ backgroundImage: `url(${image})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-bg-surface via-bg-surface/40 to-transparent" />
          <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/80 hairline-strong text-[10px] font-mono uppercase tracking-widest text-accent-cyan">
            {cat}
          </div>
        </div>
      )}
      <div className="p-4">
        {!image && (
          <div className="flex items-center gap-2 mb-2 text-[10px] font-mono uppercase tracking-widest text-accent-cyan">
            <Icon size={12} /> {cat}
          </div>
        )}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-bold text-[15px] tracking-tight truncate">{v.name}</div>
            <div className="font-mono text-[11px] text-ink-muted mt-0.5">id: {v.id}</div>
          </div>
          <div className="text-right shrink-0">
            <div className="font-mono text-[15px] text-accent-orange font-bold">
              {shortINR(v.price_inr)}
            </div>
            <div className="font-mono text-[10px] text-ink-muted uppercase tracking-widest">{unit}</div>
          </div>
        </div>
        {highlights && (
          <div
            data-testid={`vendor-card-${idx}-highlights`}
            className="mt-2 text-[12px] text-accent-cyan font-medium"
          >
            {highlights}
          </div>
        )}
        <p className="mt-2 text-[12.5px] text-ink-secondary leading-relaxed line-clamp-3">
          <span className="text-accent-cyan font-mono">// </span>
          {v.reason}
        </p>
      </div>
    </div>
  );
}

function EmptyVendor({ cat }) {
  const Icon = CAT_ICON[cat] || MapPin;
  return (
    <div className="hairline rounded-sm p-4 bg-bg-surface/30 border-dashed flex items-center gap-3 text-ink-muted">
      <Icon size={14} />
      <span className="font-mono text-[12px] uppercase">{cat} — not selected</span>
    </div>
  );
}

function BudgetCard({ plan, budget }) {
  const total = plan?.total_cost_inr || 0;
  const cap = budget || 1;
  const used = Math.min(100, Math.round((total / cap) * 100));
  const over = total > cap;
  return (
    <div className="hairline bg-bg-surface rounded-sm p-4" data-testid="budget-card">
      <div className="flex items-baseline justify-between mb-3">
        <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan">
          &gt; BUDGET
        </p>
        <span className={cn("text-[11px] font-mono", over ? "text-accent-red" : "text-accent-green")}>
          {used}% used
        </span>
      </div>
      <div className="font-mono text-2xl text-ink-primary font-bold">{inr(total)}</div>
      <div className="font-mono text-[11px] text-ink-muted">of {inr(budget)} budget</div>

      <div className="h-1.5 bg-black hairline mt-3 relative overflow-hidden">
        <div
          className={cn("h-full transition-all duration-700", over ? "bg-accent-red" : "bg-accent-orange")}
          style={{ width: `${Math.min(used, 100)}%` }}
        />
      </div>

      <div className="mt-4 divide-y divide-white/5 border-y hairline">
        {(plan?.budget_breakdown || []).map((b, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 font-mono text-[12px]">
            <span className="uppercase tracking-wider text-ink-secondary">{b.category}</span>
            <span className="text-ink-primary">{inr(b.amount_inr)}</span>
          </div>
        ))}
        <div className="flex items-center justify-between py-2 font-mono text-[12px]">
          <span className="uppercase tracking-widest text-accent-orange font-bold">total</span>
          <span className="text-accent-orange font-bold">{inr(total)}</span>
        </div>
      </div>
    </div>
  );
}

function ComplianceCard({ compliance }) {
  if (!compliance) return null;
  const meta = {
    approve_auto: { tone: "green", label: "AUTO-APPROVED" },
    needs_human: { tone: "amber", label: "NEEDS HUMAN" },
    reject: { tone: "red", label: "REJECTED" },
  }[compliance.decision] || { tone: "secondary", label: compliance.decision };

  const toneClass = {
    green: "text-accent-green border-accent-green/40",
    amber: "text-accent-orange border-accent-orange/50",
    red: "text-accent-red border-accent-red/50",
    secondary: "text-ink-secondary border-white/15",
  }[meta.tone];

  return (
    <div className="hairline bg-bg-surface rounded-sm p-4" data-testid="compliance-card">
      <div className="flex items-center justify-between mb-3">
        <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan">
          &gt; COMPLIANCE
        </p>
        <span className={cn("px-2 py-0.5 hairline rounded-sm font-mono text-[10px] uppercase", toneClass)}>
          {meta.label}
        </span>
      </div>
      <div className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">risk</div>
      <div className={cn("font-bold text-lg capitalize", toneClass)}>{compliance.risk_level}</div>
      <p className="mt-2 text-[12.5px] text-ink-secondary leading-relaxed">
        {compliance.rationale}
      </p>
      {compliance.violations?.length > 0 && (
        <div className="mt-3 border-t hairline pt-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-accent-orange mb-1">
            flags
          </div>
          <ul className="space-y-1 text-[12px] text-ink-secondary">
            {compliance.violations.map((v, i) => (
              <li key={i} className="flex gap-2">
                <AlertTriangle size={12} className="text-accent-orange shrink-0 mt-0.5" />
                <span>{v}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TimelineCard({ items }) {
  return (
    <div className="hairline bg-bg-surface rounded-sm p-4" data-testid="timeline-card">
      <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan mb-3">
        &gt; TIMELINE
      </p>
      <div className="relative pl-4">
        <div className="absolute left-1 top-1 bottom-1 w-px bg-white/10" />
        {items.map((it, i) => (
          <div key={i} className="relative mb-3 last:mb-0">
            <div className="absolute -left-3 top-1.5 w-2 h-2 rounded-full bg-accent-orange" />
            <div className="font-mono text-[11px] text-accent-orange tracking-wider">{it.time}</div>
            <div className="text-[13px] text-ink-primary leading-snug">{it.activity}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FailureCard({ state }) {
  return (
    <div className="hairline bg-accent-red/5 border-accent-red/40 rounded-sm p-6" data-testid="failure-card">
      <div className="flex items-start gap-3">
        <XCircle className="text-accent-red shrink-0" />
        <div>
          <div className="font-bold text-lg">Pipeline halted</div>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[12.5px] text-ink-secondary">
            {state.final_message || state.compliance?.rationale || "No further information."}
          </pre>
        </div>
      </div>
    </div>
  );
}
