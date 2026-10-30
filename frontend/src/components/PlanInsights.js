import React from "react";
import { motion } from "framer-motion";
import {
  Gauge,
  CloudRain,
  Sun,
  CloudSun,
  ListChecks,
  Package,
  Wand2,
  CalendarPlus,
  FileDown,
  AlertTriangle,
} from "lucide-react";
import { api } from "../lib/api";
import { cn, inr } from "../lib/utils";

// Two skins: the warm consumer page and the dark agent console.
const THEMES = {
  light: {
    card: "bg-ivory-50 border border-ivory-200 rounded-sm p-5",
    eyebrow: "font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600",
    title: "font-serif text-2xl tracking-tight text-slate-ink",
    text: "text-slate-mid",
    strong: "text-slate-ink",
    muted: "text-slate-soft",
    track: "bg-ivory-200",
    bar: "bg-emerald-800",
    divider: "divide-ivory-200 border-ivory-200",
    chip: "border border-ivory-200 bg-ivory-100",
    good: "text-emerald-800",
    warn: "text-gold-600",
    bad: "text-rose-600",
    button:
      "inline-flex items-center justify-center gap-1.5 px-4 py-2.5 border border-ivory-200 text-[12.5px] hover:border-emerald-800 hover:text-emerald-800 rounded-sm transition-colors",
    highlight: "border-emerald-800 bg-emerald-50",
  },
  dark: {
    card: "hairline bg-bg-surface rounded-sm p-4",
    eyebrow: "text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan",
    title: "font-bold text-lg tracking-tight text-ink-primary",
    text: "text-ink-secondary",
    strong: "text-ink-primary",
    muted: "text-ink-muted",
    track: "bg-black hairline",
    bar: "bg-accent-orange",
    divider: "divide-white/5 border-white/10",
    chip: "hairline bg-black/40",
    good: "text-accent-green",
    warn: "text-accent-orange",
    bad: "text-accent-red",
    button:
      "inline-flex items-center justify-center gap-1.5 px-3 py-2 hairline rounded-sm font-mono text-[11px] uppercase tracking-widest text-ink-secondary hover:text-accent-cyan hover:border-accent-cyan/50 transition-colors",
    highlight: "border-accent-orange/60 bg-accent-orange/5",
  },
};

const GRADE_TONE = { A: "good", B: "good", C: "warn", D: "bad" };
const RISK_TONE = { low: "good", medium: "warn", high: "bad", unknown: "muted" };
const RISK_ICON = { low: Sun, medium: CloudSun, high: CloudRain, unknown: CloudSun };

export default function PlanInsights({ state, planId, theme = "light" }) {
  const insights = state?.insights;
  if (!insights) return null;
  const t = THEMES[theme];
  const canExport = state.status === "booked" || state.status === "awaiting_approval";

  return (
    <div className="space-y-6" data-testid="plan-insights">
      <HealthCard health={insights.health} t={t} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <WeatherCard weather={insights.weather} insights={insights} t={t} />
        <OptimizerCard log={state.optimization_log} t={t} />
      </div>
      <PackagesCard
        packages={insights.packages}
        currentTotal={state.plan?.total_cost_inr}
        t={t}
      />
      <ChecklistCard items={insights.checklist} t={t} />
      {canExport && planId && <ExportCard planId={planId} hasDate={!!insights.event_date_iso} t={t} />}
    </div>
  );
}

function Eyebrow({ icon: Icon, children, t }) {
  return (
    <div className={cn(t.eyebrow, "flex items-center gap-1.5 mb-3")}>
      <Icon size={12} /> {children}
    </div>
  );
}

function HealthCard({ health, t }) {
  if (!health) return null;
  const tone = t[GRADE_TONE[health.grade] || "warn"];
  return (
    <div className={t.card} data-testid="health-card">
      <Eyebrow icon={Gauge} t={t}>plan health</Eyebrow>
      <div className="flex flex-col md:flex-row md:items-center gap-6">
        <div className="flex items-baseline gap-3 shrink-0">
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn("font-mono text-5xl font-bold", tone)}
          >
            {health.score}
          </motion.span>
          <span className={cn("text-[13px]", t.muted)}>/ 100</span>
          <span className={cn("ml-2 px-2 py-0.5 rounded-sm font-mono text-[12px]", t.chip, tone)}>
            grade {health.grade}
          </span>
        </div>
        <div className="flex-1 space-y-2.5 min-w-0">
          {(health.factors || []).map((f, i) => (
            <div key={f.name}>
              <div className="flex items-baseline justify-between text-[12px]">
                <span className={t.strong}>{f.name}</span>
                <span className={cn("font-mono", t.muted)}>
                  {f.score}/{f.max}
                </span>
              </div>
              <div className={cn("h-1 mt-1 relative overflow-hidden", t.track)}>
                <motion.div
                  className={cn("h-full", t.bar)}
                  initial={{ width: 0 }}
                  animate={{ width: `${(f.score / f.max) * 100}%` }}
                  transition={{ duration: 0.6, delay: i * 0.08 }}
                />
              </div>
              <div className={cn("text-[11.5px] mt-0.5 truncate", t.text)}>{f.note}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function WeatherCard({ weather, insights, t }) {
  if (!weather) return null;
  const Icon = RISK_ICON[weather.risk] || CloudSun;
  const tone = t[RISK_TONE[weather.risk] || "muted"];
  return (
    <div className={t.card} data-testid="weather-card">
      <Eyebrow icon={Icon} t={t}>weather outlook</Eyebrow>
      <div className="flex items-baseline gap-2">
        <span className={cn("font-bold text-xl capitalize", tone)}>{weather.risk} risk</span>
        {weather.month && <span className={cn("text-[12px]", t.muted)}>· {weather.month}</span>}
      </div>
      {weather.rain_probability !== null && weather.rain_probability !== undefined && (
        <div className={cn("mt-1 font-mono text-[12px]", t.text)}>
          ~{Math.round(weather.rain_probability * 100)}% rain chance · ~{weather.high_c}°C high
        </div>
      )}
      <p className={cn("mt-2 text-[13px] leading-relaxed", t.text)}>{weather.advice}</p>
      {insights.event_date_iso && (
        <div className={cn("mt-3 text-[12px]", t.muted)}>
          {insights.weekday}, {insights.event_date_iso}
          {insights.days_until !== null && ` · ${insights.days_until} days to go`}
          {insights.per_guest_cost_inr ? ` · ${inr(insights.per_guest_cost_inr)} per guest` : ""}
        </div>
      )}
    </div>
  );
}

function OptimizerCard({ log, t }) {
  const changes = log || [];
  return (
    <div className={t.card} data-testid="optimizer-card">
      <Eyebrow icon={Wand2} t={t}>budget optimizer</Eyebrow>
      {changes.length === 0 ? (
        <p className={cn("text-[13px] leading-relaxed", t.text)}>
          The first plan already fit the budget, so no vendor swaps were needed.
        </p>
      ) : (
        <>
          <p className={cn("text-[13px] mb-2", t.strong)}>
            Your first plan was over budget. The optimizer made {changes.length} change
            {changes.length > 1 ? "s" : ""} to fix it:
          </p>
          <ul className="space-y-1.5">
            {changes.map((c, i) => (
              <li key={i} className={cn("text-[12.5px] flex gap-2", t.text)}>
                <span className={t.good}>→</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function PackagesCard({ packages, currentTotal, t }) {
  if (!packages?.length) return null;
  return (
    <div className={t.card} data-testid="packages-card">
      <Eyebrow icon={Package} t={t}>compare packages</Eyebrow>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {packages.map((p) => {
          const isCurrent = p.total_cost_inr === currentTotal;
          return (
            <div
              key={p.tier}
              className={cn("rounded-sm p-4 border", t.chip, isCurrent && t.highlight)}
              data-testid={`package-${p.tier}`}
            >
              <div className="flex items-baseline justify-between">
                <span className={cn("font-bold", t.strong)}>{p.label}</span>
                <span className={cn("font-mono text-[11px]", p.fits_budget ? t.good : t.bad)}>
                  {p.fits_budget ? "fits budget" : "over budget"}
                </span>
              </div>
              <div className={cn("font-mono text-xl mt-1", t.strong)}>{inr(p.total_cost_inr)}</div>
              <div className={cn("text-[11.5px]", t.muted)}>
                {inr(p.per_guest_inr)} per guest{isCurrent ? " · your plan" : ""}
              </div>
              <p className={cn("text-[12px] mt-2", t.text)}>{p.blurb}</p>
              <ul className={cn("mt-2 space-y-0.5 text-[11.5px]", t.text)}>
                {Object.entries(p.vendors || {}).map(([cat, name]) => (
                  <li key={cat} className="truncate">
                    <span className={cn("capitalize", t.muted)}>{cat}:</span> {name}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChecklistCard({ items, t }) {
  if (!items?.length) return null;
  return (
    <div className={t.card} data-testid="checklist-card">
      <Eyebrow icon={ListChecks} t={t}>countdown checklist</Eyebrow>
      <ol className={cn("divide-y", t.divider)}>
        {items.map((it, i) => (
          <li key={i} className="py-2 flex items-start gap-3 text-[13px]">
            <span className={cn("font-mono text-[11.5px] w-24 shrink-0 pt-0.5", it.urgent ? t.bad : t.warn)}>
              {it.due}
            </span>
            <span className={cn("flex-1", t.strong)}>{it.task}</span>
            {it.urgent ? (
              <span className={cn("inline-flex items-center gap-1 text-[11px] font-mono shrink-0", t.bad)}>
                <AlertTriangle size={11} /> urgent
              </span>
            ) : (
              <span className={cn("text-[11px] font-mono shrink-0", t.muted)}>T-{it.days_before}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function ExportCard({ planId, hasDate, t }) {
  return (
    <div className={t.card} data-testid="export-card">
      <Eyebrow icon={FileDown} t={t}>take it with you</Eyebrow>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {hasDate && (
          <a href={api.exportUrl(planId, "ics")} className={t.button} data-testid="export-ics">
            <CalendarPlus size={13} /> Add to calendar (.ics)
          </a>
        )}
        <a href={api.exportUrl(planId, "md")} className={t.button} data-testid="export-md">
          <FileDown size={13} /> Download plan (.md)
        </a>
      </div>
      {hasDate && (
        <p className={cn("mt-2 text-[11.5px]", t.muted)}>
          The calendar file includes the event and every checklist deadline.
        </p>
      )}
    </div>
  );
}
