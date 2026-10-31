import React, { useEffect, useState, useCallback } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MapPin,
  Utensils,
  Sparkles,
  Music,
  Camera,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ArrowLeft,
  Users,
  Calendar,
  Share2,
  Mail,
} from "lucide-react";
import ConsumerNav from "../components/ConsumerNav";
import ConsumerFooter from "../components/ConsumerFooter";
import PlanInsights from "../components/PlanInsights";
import { api } from "../lib/api";
import { cn, inr, unitLabel, vendorHighlights } from "../lib/utils";

const CONTACT_EMAIL = process.env.REACT_APP_CONTACT_EMAIL || "hello@gatherly.example";

const CAT_ICON = {
  venue: MapPin,
  caterer: Utensils,
  decorator: Sparkles,
  entertainment: Music,
  photographer: Camera,
};

const VENUE_IMG_OUTDOOR =
  "https://images.unsplash.com/photo-1772127822531-6a279b5aa968?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjB3ZWRkaW5nJTIwb3V0ZG9vciUyMHZlbnVlfGVufDB8fHx8MTc4MjQ5NDgwN3ww&ixlib=rb-4.1.0&q=85";
const VENUE_IMG_INDOOR =
  "https://images.unsplash.com/photo-1772127822525-7eda37383b9f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjB3ZWRkaW5nJTIwb3V0ZG9vciUyMHZlbnVlfGVufDB8fHx8MTc4MjQ5NDgwN3ww&ixlib=rb-4.1.0&q=85";

export default function PlanView() {
  const { planId } = useParams();
  const location = useLocation();
  const [state, setState] = useState(location.state?.initial || null);
  const [loading, setLoading] = useState(!state);
  const [error, setError] = useState(null);
  const [catalog, setCatalog] = useState({}); // id → full vendor entry

  // load full vendor catalog once so we can show category-specific highlights
  useEffect(() => {
    api
      .vendors()
      .then((d) => {
        const map = {};
        (d.vendors || []).forEach((v) => {
          map[v.id] = v;
        });
        setCatalog(map);
      })
      .catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const doc = await api.getPlan(planId);
      const s = doc.state || {};
      setState({ plan_id: doc.plan_id, ...s });
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    if (!state) load();
  }, [state, load]);

  // poll every 5 seconds if still pending so user sees status updates after admin acts
  useEffect(() => {
    if (!state) return;
    if (state.status !== "awaiting_approval") return;
    const t = setInterval(() => {
      api.getPlan(planId).then((doc) => {
        if (doc.state?.status !== "awaiting_approval") {
          setState({ plan_id: doc.plan_id, ...doc.state });
        }
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, [state, planId]);

  return (
    <div className="min-h-screen bg-ivory-50 text-slate-ink flex flex-col" data-testid="plan-view-root">
      <ConsumerNav />
      <div className="flex-1">
        <div className="max-w-6xl mx-auto px-6 lg:px-10 py-10 md:py-14">
          <Link to="/plan" className="inline-flex items-center gap-1.5 text-[12px] text-slate-mid hover:text-emerald-800 mb-6">
            <ArrowLeft size={12} /> Plan another event
          </Link>

          {loading && !state && <PendingSpinner />}
          {error && (
            <div className="border border-rose-600/30 bg-rose-600/5 text-rose-600 px-4 py-3 rounded-sm text-[13px]">
              {error}
            </div>
          )}
          {state && <PlanContent state={state} planId={planId} catalog={catalog} />}
        </div>
      </div>
      <ConsumerFooter />
    </div>
  );
}

function PendingSpinner() {
  return (
    <div className="py-32 grid place-items-center text-slate-mid" data-testid="plan-loading">
      <Loader2 className="animate-spin mb-3" />
      <p className="font-mono text-[12px] tracking-widest uppercase">loading your plan…</p>
    </div>
  );
}

function PlanContent({ state, planId, catalog }) {
  const isFail =
    state.status === "refused" ||
    state.status === "rejected" ||
    state.status === "declined";

  return (
    <div data-testid="plan-content">
      <StatusBanner state={state} />

      {isFail && <FailureBlock state={state} />}

      {!isFail && state.requirements && state.shortlist && state.plan && (
        <>
          <Headline state={state} />
          <div className="mt-10 grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-8 space-y-6">
              <VendorList
                shortlist={state.shortlist}
                setting={state.requirements?.setting_preference}
                catalog={catalog}
              />
              <Timeline items={state.plan.timeline || []} />
            </div>
            <div className="lg:col-span-4 space-y-6">
              <BudgetSummary plan={state.plan} budget={state.requirements?.budget_inr} />
              <NextSteps state={state} planId={planId} />
            </div>
          </div>
          <div className="mt-6">
            <PlanInsights state={state} planId={planId} theme="light" />
          </div>
        </>
      )}
    </div>
  );
}

function StatusBanner({ state }) {
  const isAwait = state.status === "awaiting_approval";
  const isBooked = state.status === "booked";
  const isFail =
    state.status === "refused" ||
    state.status === "rejected" ||
    state.status === "declined";

  if (isAwait) {
    return (
      <div
        data-testid="status-banner"
        className="flex items-center gap-3 px-5 py-4 bg-gold-200/30 border border-gold-400/40 rounded-sm"
      >
        <div className="w-9 h-9 rounded-full bg-gold-500 text-ivory-50 grid place-items-center shrink-0">
          <Clock size={16} />
        </div>
        <div>
          <div className="font-serif text-lg text-slate-ink leading-tight">
            Your plan is with a Gatherly coordinator.
          </div>
          <div className="text-[13px] text-slate-mid mt-0.5">
            We&apos;ll confirm within a few hours — you can keep this page open or share it.
          </div>
        </div>
      </div>
    );
  }
  if (isBooked) {
    return (
      <div
        data-testid="status-banner"
        className="flex items-center gap-3 px-5 py-4 bg-emerald-50 border border-emerald-700/30 rounded-sm"
      >
        <div className="w-9 h-9 rounded-full bg-emerald-800 text-ivory-50 grid place-items-center shrink-0">
          <CheckCircle2 size={16} />
        </div>
        <div>
          <div className="font-serif text-lg text-slate-ink leading-tight">
            Confirmed — your event is booked.
          </div>
          <div className="text-[13px] text-slate-mid mt-0.5">
            A coordinator will reach out shortly with vendor confirmations and contracts.
          </div>
        </div>
      </div>
    );
  }
  if (isFail) {
    return (
      <div
        data-testid="status-banner"
        className="flex items-center gap-3 px-5 py-4 bg-rose-600/5 border border-rose-600/30 rounded-sm"
      >
        <div className="w-9 h-9 rounded-full bg-rose-600 text-ivory-50 grid place-items-center shrink-0">
          <XCircle size={16} />
        </div>
        <div>
          <div className="font-serif text-lg text-slate-ink leading-tight">
            {state.status === "refused" ? "We couldn't take this on." :
              state.status === "rejected" ? "We couldn't find a fit for these details." :
              "Plan was declined."}
          </div>
          <div className="text-[13px] text-slate-mid mt-0.5">Try adjusting the city, guest count or budget.</div>
        </div>
      </div>
    );
  }
  return null;
}

function Headline({ state }) {
  const r = state.requirements || {};
  return (
    <div className="mt-8" data-testid="plan-headline">
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-2">
        your plan
      </div>
      <h1 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight">
        A <span className="capitalize">{r.event_type || "celebration"}</span> in{" "}
        <span className="italic text-emerald-800">{r.city || "—"}</span>
      </h1>
      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-slate-mid">
        <span className="inline-flex items-center gap-1.5"><Users size={13} /> {r.guest_count} guests</span>
        {r.event_date && (
          <span className="inline-flex items-center gap-1.5"><Calendar size={13} /> {r.event_date}</span>
        )}
        {r.setting_preference && r.setting_preference !== "any" && (
          <span className="capitalize">· {r.setting_preference} setting</span>
        )}
      </div>
    </div>
  );
}

function VendorList({ shortlist, setting, catalog }) {
  const cats = ["venue", "caterer", "decorator", "entertainment", "photographer"];
  return (
    <div className="bg-ivory-50 border border-ivory-200 rounded-sm" data-testid="vendor-list">
      <div className="px-5 py-3 border-b border-ivory-200 flex items-center justify-between">
        <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600">
          › vendors
        </div>
        <div className="text-[11px] text-slate-soft">curated from our trusted partners</div>
      </div>
      <div className="divide-y divide-ivory-200">
        {cats.map((cat, i) => {
          const v = shortlist[cat];
          if (!v) return <EmptyVendor key={cat} cat={cat} />;
          return (
            <motion.div
              key={cat}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <VendorRow
                cat={cat}
                v={v}
                entry={catalog?.[v.id]}
                image={
                  cat === "venue"
                    ? setting === "outdoor"
                      ? VENUE_IMG_OUTDOOR
                      : VENUE_IMG_INDOOR
                    : null
                }
                idx={i}
              />
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function VendorRow({ cat, v, entry, image, idx }) {
  const Icon = CAT_ICON[cat] || MapPin;
  const unit = unitLabel(v.price_unit, cat);
  const highlights = vendorHighlights(cat, entry);
  return (
    <div data-testid={`vendor-${idx}`} className="grid grid-cols-12 gap-4 p-5 items-start">
      <div className="col-span-12 md:col-span-3">
        {image ? (
          <div
            className="aspect-[4/3] bg-cover bg-center rounded-sm border border-ivory-200"
            style={{ backgroundImage: `url(${image})` }}
          />
        ) : (
          <div className="aspect-[4/3] bg-ivory-100 border border-ivory-200 rounded-sm grid place-items-center text-emerald-800">
            <Icon size={28} />
          </div>
        )}
      </div>
      <div className="col-span-12 md:col-span-6">
        <div className="font-mono text-[10px] tracking-[0.25em] uppercase text-gold-600">
          {cat}
        </div>
        <div className="font-serif text-2xl tracking-tight mt-1">{v.name}</div>
        {highlights && (
          <div
            data-testid={`vendor-${idx}-highlights`}
            className="mt-1.5 text-[12.5px] text-emerald-800 font-medium tracking-tight"
          >
            {highlights}
          </div>
        )}
        <p className="mt-2 text-[13.5px] text-slate-mid leading-relaxed">{v.reason}</p>
      </div>
      <div className="col-span-12 md:col-span-3 md:text-right">
        <div className="font-serif text-2xl text-emerald-800">{inr(v.price_inr)}</div>
        <div className="text-[11px] tracking-widest uppercase font-mono text-slate-soft">
          {unit}
        </div>
      </div>
    </div>
  );
}

function EmptyVendor({ cat }) {
  const Icon = CAT_ICON[cat] || MapPin;
  return (
    <div className="px-5 py-4 flex items-center gap-3 text-slate-soft text-[13px]">
      <Icon size={14} />
      <span className="capitalize">{cat}</span>
      <span className="italic">— not part of this plan</span>
    </div>
  );
}

function Timeline({ items }) {
  if (!items?.length) return null;
  return (
    <div className="bg-ivory-50 border border-ivory-200 rounded-sm p-5" data-testid="plan-timeline">
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-4">
        › day-of timeline
      </div>
      <div className="relative pl-5">
        <div className="absolute left-1.5 top-1 bottom-1 w-px bg-ivory-200" />
        {items.map((it, i) => (
          <div key={i} className="relative mb-4 last:mb-0">
            <div className="absolute -left-[18px] top-1.5 w-2.5 h-2.5 rounded-full bg-emerald-800" />
            <div className="font-mono text-[12px] tracking-wider text-gold-600">{it.time}</div>
            <div className="text-[14px] text-slate-ink leading-snug">{it.activity}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BudgetSummary({ plan, budget }) {
  const total = plan?.total_cost_inr || 0;
  const over = budget && total > budget;
  const pct = budget ? Math.min(100, Math.round((total / budget) * 100)) : 0;
  return (
    <div className="bg-emerald-800 text-ivory-50 rounded-sm p-6" data-testid="budget-summary">
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-200">
        › estimated total
      </div>
      <div className="font-serif text-5xl mt-2">{inr(total)}</div>
      {budget && (
        <div className="text-[13px] text-emerald-50/80 mt-1">
          of {inr(budget)} budget · {pct}% used
        </div>
      )}

      <div className="h-1 bg-emerald-900/50 mt-4 relative overflow-hidden">
        <div
          className={cn("h-full", over ? "bg-rose-600" : "bg-gold-400")}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-5 divide-y divide-emerald-700/40 border-t border-emerald-700/40">
        {(plan?.budget_breakdown || []).map((b, i) => (
          <div key={i} className="flex items-center justify-between py-2 text-[13px]">
            <span className="capitalize text-emerald-50/90">{b.category}</span>
            <span className="font-medium">{inr(b.amount_inr)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function NextSteps({ state, planId }) {
  const isAwait = state.status === "awaiting_approval";
  const isBooked = state.status === "booked";

  const share = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: "My Gatherly plan", url });
      } catch {
        /* user cancelled share */
      }
    } else {
      try {
        await navigator.clipboard.writeText(url);
        alert("Link copied to clipboard");
      } catch {
        /* clipboard denied */
      }
    }
  };

  return (
    <div className="bg-ivory-50 border border-ivory-200 rounded-sm p-6" data-testid="next-steps">
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-3">
        › what happens next
      </div>
      <ol className="space-y-3 text-[13.5px] text-slate-mid">
        <Step done label="AI built your plan" />
        <Step done={isBooked} active={isAwait} label="Gatherly coordinator reviews" />
        <Step done={isBooked} label="Vendors confirmed & booked" />
        <Step label="You celebrate — we run the day" />
      </ol>

      <div className="mt-5 grid grid-cols-2 gap-2">
        <button
          type="button"
          data-testid="share-button"
          onClick={share}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 border border-ivory-200 text-[12.5px] hover:border-emerald-800 hover:text-emerald-800 rounded-sm transition-colors"
        >
          <Share2 size={13} /> Share plan
        </button>
        <a
          href={`mailto:${CONTACT_EMAIL}?subject=My%20event%20plan%20${planId}&body=I%27d%20like%20to%20talk%20about%20my%20plan%3A%20${encodeURIComponent(window.location.href)}`}
          data-testid="contact-button"
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-sm text-[12.5px] transition-colors"
        >
          <Mail size={13} /> Contact us
        </a>
      </div>

      <div className="mt-4 text-[11px] text-slate-soft font-mono">
        plan id: {planId}
      </div>
    </div>
  );
}

function Step({ done, active, label }) {
  return (
    <li className="flex items-start gap-3">
      <span
        className={cn(
          "mt-0.5 w-4 h-4 rounded-full grid place-items-center shrink-0 border",
          done
            ? "bg-emerald-800 border-emerald-800 text-ivory-50"
            : active
            ? "bg-gold-500 border-gold-500 text-ivory-50 animate-pulse"
            : "bg-ivory-100 border-ivory-200 text-slate-soft"
        )}
      >
        {done ? <CheckCircle2 size={10} /> : active ? <Clock size={10} /> : null}
      </span>
      <span className={cn(done && "text-slate-ink", active && "text-slate-ink font-medium")}>
        {label}
      </span>
    </li>
  );
}

function FailureBlock({ state }) {
  return (
    <div className="mt-8 bg-ivory-50 border border-ivory-200 rounded-sm p-8 text-center" data-testid="plan-failure">
      <AlertTriangle className="mx-auto text-rose-600" />
      <h2 className="mt-4 font-serif text-3xl tracking-tight">We hit a wall</h2>
      <p className="mt-2 text-slate-mid max-w-md mx-auto text-[14px]">
        {state.final_message || state.compliance?.rationale || "Please try adjusting your details."}
      </p>
      <Link
        to="/plan"
        className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[13px]"
      >
        Try again
      </Link>
    </div>
  );
}
