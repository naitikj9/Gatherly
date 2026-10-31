import React, { useEffect, useRef, useState } from "react";
import { SlidersHorizontal, AlertTriangle, Loader2, RotateCcw, Star } from "lucide-react";
import { api } from "../lib/api";
import { cn, inr } from "../lib/utils";

const SETTINGS = [
  { id: "any", label: "Either" },
  { id: "indoor", label: "Indoor" },
  { id: "outdoor", label: "Outdoor" },
];

/**
 * "What if we invite 50 more people?" Sliders re-price the plan on the server
 * with the same deterministic tools the agents use: instant, no AI calls.
 */
export default function WhatIf({ planId, requirements }) {
  const baseGuests = requirements?.guest_count || 100;
  const baseBudget = requirements?.budget_inr || 500000;
  const baseSetting = requirements?.setting_preference || "any";

  const [guests, setGuests] = useState(baseGuests);
  const [budget, setBudget] = useState(baseBudget);
  const [setting, setSetting] = useState(baseSetting);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const seq = useRef(0);

  // debounce slider drags, and ignore answers that arrive out of order
  useEffect(() => {
    const id = ++seq.current;
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const res = await api.whatIf(planId, { guest_count: guests, budget_inr: budget, setting });
        if (id === seq.current) {
          setResult(res);
          setError(null);
        }
      } catch (e) {
        if (id === seq.current) setError(e.message);
      } finally {
        if (id === seq.current) setBusy(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [planId, guests, budget, setting]);

  const reset = () => {
    setGuests(baseGuests);
    setBudget(baseBudget);
    setSetting(baseSetting);
  };
  const changed = guests !== baseGuests || budget !== baseBudget || setting !== baseSetting;
  const mix = result?.current_mix;

  return (
    <section className="border border-ivory-200 bg-white rounded-sm p-6" data-testid="whatif">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 inline-flex items-center gap-1.5">
            <SlidersHorizontal size={12} /> what-if simulator
          </div>
          <h2 className="font-serif text-2xl mt-1">Play with the numbers</h2>
          <p className="text-[13px] text-slate-mid mt-1">
            Change the guest list or budget and see the cost update instantly.
          </p>
        </div>
        {changed && (
          <button
            type="button"
            onClick={reset}
            data-testid="whatif-reset"
            className="inline-flex items-center gap-1 text-[12px] text-slate-mid hover:text-emerald-800 shrink-0"
          >
            <RotateCcw size={12} /> Reset
          </button>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <Slider
          label="Guests"
          value={guests}
          min={10}
          max={Math.max(1000, baseGuests * 2)}
          step={10}
          format={(v) => `${v} guests`}
          onChange={setGuests}
          testid="whatif-guests"
        />
        <Slider
          label="Budget"
          value={budget}
          min={50000}
          max={Math.max(3000000, baseBudget * 2)}
          step={25000}
          format={inr}
          onChange={setBudget}
          testid="whatif-budget"
        />
      </div>

      <div className="mt-5 flex items-center gap-2" role="radiogroup" aria-label="Setting">
        {SETTINGS.map((s) => (
          <button
            key={s.id}
            type="button"
            role="radio"
            aria-checked={setting === s.id}
            onClick={() => setSetting(s.id)}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-[12.5px] border transition-colors",
              setting === s.id
                ? "bg-emerald-800 border-emerald-800 text-ivory-50"
                : "border-ivory-200 text-slate-mid hover:border-emerald-800"
            )}
          >
            {s.label}
          </button>
        ))}
        {busy && <Loader2 size={14} className="animate-spin text-slate-soft ml-2" />}
      </div>

      {error && <p className="mt-4 text-[13px] text-rose-600">{error}</p>}

      {mix && (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4" data-testid="whatif-current">
          <Stat label="Your current vendors" value={inr(mix.total_cost_inr)} />
          <Stat
            label="Change vs. your plan"
            value={`${mix.delta_inr >= 0 ? "+" : "−"}${inr(Math.abs(mix.delta_inr))}`}
            tone={mix.delta_inr > 0 ? "warn" : "good"}
          />
          <Stat label="Per guest" value={inr(mix.per_guest_inr)} />
        </div>
      )}

      {result?.warnings?.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {result.warnings.map((w) => (
            <li key={w} className="flex items-start gap-2 text-[13px] text-gold-600">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {w}
            </li>
          ))}
        </ul>
      )}

      {result?.packages?.length > 0 && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="whatif-packages">
          {result.packages.map((p) => {
            const best = p.tier === result.recommended_tier;
            return (
              <div
                key={p.tier}
                className={cn(
                  "border rounded-sm p-4",
                  best ? "border-emerald-800 bg-emerald-50" : "border-ivory-200"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[14px]">{p.label}</span>
                  {best && (
                    <span className="inline-flex items-center gap-1 text-[10.5px] font-mono uppercase tracking-wider text-emerald-800">
                      <Star size={10} /> best fit
                    </span>
                  )}
                </div>
                <div className="font-serif text-2xl mt-1">{inr(p.total_cost_inr)}</div>
                <div className={cn("text-[12px] mt-0.5", p.fits_budget ? "text-emerald-800" : "text-rose-600")}>
                  {p.fits_budget ? "Fits the budget" : "Over budget"} · {inr(p.per_guest_inr)}/guest
                </div>
                <ul className="mt-3 space-y-0.5 text-[12px] text-slate-mid">
                  {Object.entries(p.vendors).map(([cat, name]) => (
                    <li key={cat} className="truncate" title={name}>
                      <span className="capitalize text-slate-soft">{cat}:</span> {name}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
      {result && result.packages?.length === 0 && (
        <p className="mt-6 text-[13px] text-slate-mid">
          No venue in {requirements?.city} fits {guests} guests on this date. Try fewer guests.
        </p>
      )}
    </section>
  );
}

function Slider({ label, value, min, max, step, format, onChange, testid }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between text-[13px]">
        <span className="text-slate-mid">{label}</span>
        <span className="font-medium text-slate-ink">{format(value)}</span>
      </div>
      <input
        type="range"
        data-testid={testid}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full mt-2 accent-emerald-800"
      />
    </label>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="border border-ivory-200 rounded-sm px-4 py-3">
      <div className="text-[11.5px] text-slate-soft">{label}</div>
      <div
        className={cn(
          "font-serif text-xl mt-0.5",
          tone === "warn" && "text-rose-600",
          tone === "good" && "text-emerald-800"
        )}
      >
        {value}
      </div>
    </div>
  );
}
