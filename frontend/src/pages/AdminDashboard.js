import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Inbox, BellRing } from "lucide-react";
import { Toaster, toast } from "sonner";
import Hero from "../components/Hero";
import PromptForm from "../components/PromptForm";
import Pipeline from "../components/Pipeline";
import Terminal from "../components/Terminal";
import Results from "../components/Results";
import HitlModal from "../components/HitlModal";
import History from "../components/History";
import Footer from "../components/Footer";
import { api } from "../lib/api";
import { cn, shortINR, STATUS_META } from "../lib/utils";

// Brief WebAudio beep (no asset needed). Returns a function that plays once.
function makeBeep() {
  let ctx;
  return () => {
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.value = 880;
      g.gain.value = 0.0001;
      o.connect(g).connect(ctx.destination);
      const now = ctx.currentTime;
      g.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, now + 0.3);
      o.start(now);
      o.stop(now + 0.32);
    } catch {
      /* audio blocked — silent */
    }
  };
}

export default function AdminDashboard() {
  const [architecture, setArchitecture] = useState(null);
  const [state, setState] = useState(null);
  const [running, setRunning] = useState(false);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [hitlOpen, setHitlOpen] = useState(false);
  const [error, setError] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);
  const [pending, setPending] = useState([]);
  const [catalog, setCatalog] = useState({}); // id → full vendor entry
  const [freshIds, setFreshIds] = useState(new Set()); // recently-arrived plan ids (highlight)
  const knownIdsRef = useRef(null); // null on first load → don't toast
  // the polling effect below reads the latest handler through a ref, so it
  // doesn't restart every render
  const pickPlanRef = useRef(null);
  const beepRef = useRef(makeBeep());
  const resultsRef = useRef(null);

  useEffect(() => {
    api.architecture().then(setArchitecture).catch(() => {});
    api
      .vendors()
      .then((d) => {
        const m = {};
        (d.vendors || []).forEach((v) => {
          m[v.id] = v;
        });
        setCatalog(m);
      })
      .catch(() => {});
  }, []);

  // poll pending queue every 5s so admin sees new consumer submissions
  useEffect(() => {
    const reload = async () => {
      try {
        const d = await api.listPlans();
        const onlyPending = (d.plans || []).filter(
          (p) => p.status === "awaiting_approval"
        );
        const ids = new Set(onlyPending.map((p) => p.plan_id));

        // detect new arrivals (skip first load so we don't toast on mount)
        if (knownIdsRef.current !== null) {
          const arrivals = onlyPending.filter(
            (p) => !knownIdsRef.current.has(p.plan_id)
          );
          if (arrivals.length > 0) {
            beepRef.current();
            setFreshIds((prev) => {
              const next = new Set(prev);
              arrivals.forEach((a) => next.add(a.plan_id));
              return next;
            });
            // clear "fresh" highlight after 8 seconds
            setTimeout(() => {
              setFreshIds((prev) => {
                const next = new Set(prev);
                arrivals.forEach((a) => next.delete(a.plan_id));
                return next;
              });
            }, 8000);

            arrivals.forEach((a) => {
              toast.custom(
                (t) => (
                  <ArrivalToast
                    plan={a}
                    onView={() => {
                      toast.dismiss(t);
                      pickPlanRef.current?.(a.plan_id);
                    }}
                    onDismiss={() => toast.dismiss(t)}
                  />
                ),
                { duration: 12000 }
              );
            });
          }
        }
        knownIdsRef.current = ids;
        setPending(onlyPending);
      } catch {
        /* ignore */
      }
    };
    reload();
    const t = setInterval(reload, 5000);
    return () => clearInterval(t);
  }, [historyKey]);

  // keep document title in sync with pending count
  useEffect(() => {
    const base = "OBSIDIAN · admin";
    document.title = pending.length > 0 ? `(${pending.length}) ${base}` : base;
    return () => {
      document.title = "Gatherly · Agent Console";
    };
  }, [pending.length]);

  const scrollToResults = () => {
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 150);
  };

  const handleSubmit = async (text) => {
    setError(null);
    setRunning(true);
    setState({
      requirements: null,
      stream_logs: [],
      log: [],
      status: "running",
      user_request: text,
    });
    scrollToResults();
    try {
      // stream the run so the pipeline and terminal light up as each agent works
      const res = await api.streamPlan(text, {
        onStart: ({ plan_id }) => setState((s) => ({ ...s, plan_id })),
        onStep: (step) =>
          setState((s) => ({ ...s, stream_logs: [...(s?.stream_logs || []), step] })),
      });
      setState(res);
      if (res.status === "awaiting_approval") setHitlOpen(true);
      setHistoryKey((k) => k + 1);
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Pipeline failed";
      setError(String(msg));
    } finally {
      setRunning(false);
    }
  };

  const handleDecide = async (decision) => {
    if (!state?.plan_id) return;
    setDecisionBusy(true);
    try {
      const res = await api.decide(state.plan_id, decision);
      setState(res);
      setHitlOpen(res.status === "awaiting_approval");
      setHistoryKey((k) => k + 1);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setDecisionBusy(false);
    }
  };

  const handlePickPlan = async (planId) => {
    setError(null);
    try {
      const doc = await api.getPlan(planId);
      const s = doc.state || {};
      setState({ plan_id: doc.plan_id, ...s, stream_logs: doc.stream_logs || s.log || [] });
      setHitlOpen(s.status === "awaiting_approval");
      scrollToResults();
    } catch (e) {
      setError(e.message);
    }
  };
  pickPlanRef.current = handlePickPlan;

  const logsForUI =
    state?.stream_logs && state.stream_logs.length > 0
      ? state.stream_logs
      : (state?.log || []).map((line) => {
          const m = /^\[(.+?)\]\s+(.*)$/.exec(line || "");
          return m ? { node: m[1], message: m[2] } : { node: "info", message: line };
        });

  return (
    <div className="min-h-screen flex flex-col bg-bg-app text-ink-primary font-sans" data-testid="admin-root">
      <TopNav running={running} pendingCount={pending.length} hasFresh={freshIds.size > 0} />

      {/* Pending queue */}
      {pending.length > 0 && (
        <PendingQueue pending={pending} onPick={handlePickPlan} freshIds={freshIds} />
      )}

      <Hero />
      <PromptForm onSubmit={handleSubmit} loading={running} />

      <div ref={resultsRef}>
        <Pipeline
          state={state}
          logs={logsForUI}
          running={running}
          architecture={architecture}
        />
        <Terminal logs={logsForUI} running={running} status={state?.status} />
        {error && (
          <div className="max-w-7xl mx-auto px-6 lg:px-10 py-4">
            <div className="hairline border-accent-red/40 bg-accent-red/10 rounded-sm p-4 font-mono text-[12.5px] text-accent-red" data-testid="error-banner">
              ERROR · {error}
            </div>
          </div>
        )}
        {state?.requirements && <Results state={state} catalog={catalog} />}
      </div>

      <History refreshKey={historyKey} onPick={handlePickPlan} />
      <Footer />

      <HitlModal
        open={hitlOpen}
        state={state}
        onDecide={handleDecide}
        busy={decisionBusy}
      />

      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{ unstyled: true, classNames: { toast: "" } }}
      />
    </div>
  );
}

function TopNav({ running, pendingCount, hasFresh }) {
  return (
    <header className="sticky top-0 z-40 backdrop-blur bg-black/70 border-b hairline" data-testid="admin-nav">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="inline-flex items-center gap-1.5 text-[11px] text-ink-muted hover:text-accent-orange font-mono uppercase tracking-widest mr-3" data-testid="back-to-consumer">
            <ArrowLeft size={12} /> consumer
          </Link>
          <div className="w-6 h-6 grid place-items-center hairline-strong rounded-sm bg-bg-surface">
            <span className="block w-2 h-2 rounded-full bg-accent-orange animate-pulse" />
          </div>
          <span className="font-black tracking-tight text-[15px]">
            OBSIDIAN
            <span className="text-ink-muted font-normal ml-2 hidden md:inline">
              / admin · agent console
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-widest text-ink-secondary">
          {pendingCount > 0 && (
            <span
              data-testid="nav-pending-badge"
              className={cn(
                "inline-flex items-center gap-1.5 px-2 py-1 rounded-sm hairline-strong",
                hasFresh
                  ? "text-accent-orange border-accent-orange/60 animate-pulse"
                  : "text-accent-orange"
              )}
            >
              {hasFresh ? <BellRing size={12} /> : <Inbox size={12} />}
              {pendingCount} pending
            </span>
          )}
          <span className="hidden md:inline text-ink-muted">·</span>
          <span className="hidden md:inline">
            {running ? (
              <span className="text-accent-cyan flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-accent-cyan rounded-full animate-pulse" />
                graph running
              </span>
            ) : (
              <span className="text-ink-muted">graph idle</span>
            )}
          </span>
        </div>
      </div>
    </header>
  );
}

function PendingQueue({ pending, onPick, freshIds }) {
  const hasFresh = freshIds.size > 0;
  return (
    <section
      data-testid="pending-queue"
      className={cn(
        "border-b hairline transition-colors",
        hasFresh ? "bg-accent-orange/10" : "bg-accent-orange/5"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-6">
        <div className="flex items-baseline justify-between mb-4">
          <div className="flex items-center gap-3">
            <Inbox
              className={cn("text-accent-orange", hasFresh && "animate-pulse")}
              size={18}
            />
            <div>
              <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-accent-orange">
                › approval_queue
              </div>
              <div className="font-bold text-lg tracking-tight flex items-center gap-2">
                {pending.length} consumer plan
                {pending.length === 1 ? "" : "s"} waiting for your review
                {hasFresh && (
                  <span
                    data-testid="fresh-arrival-badge"
                    className="text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 bg-accent-orange text-black rounded-sm animate-pulse"
                  >
                    new
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="text-[11px] font-mono text-ink-muted uppercase tracking-widest">
            polls every 5s
          </div>
        </div>
        <div className="hairline bg-bg-surface rounded-sm overflow-hidden">
          {pending.map((p, idx) => {
            const meta =
              STATUS_META[p.status] || {
                label: (p.status || "—").toUpperCase(),
                tone: "amber",
              };
            const fresh = freshIds.has(p.plan_id);
            return (
              <button
                key={p.plan_id}
                type="button"
                data-testid={`pending-row-${idx}`}
                data-fresh={fresh ? "true" : "false"}
                onClick={() => onPick(p.plan_id)}
                className={cn(
                  "w-full grid grid-cols-12 gap-3 px-4 py-3 border-b hairline last:border-b-0 transition-all text-left items-center",
                  fresh
                    ? "bg-accent-orange/10 border-l-2 border-l-accent-orange shadow-glowOrange"
                    : "hover:bg-bg-surfaceHover"
                )}
              >
                <div className="col-span-1 font-mono text-[11px] text-accent-orange flex items-center gap-1.5">
                  {fresh && (
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-orange animate-pulse" />
                  )}
                  #{String(idx + 1).padStart(2, "0")}
                </div>
                <div className="col-span-6 min-w-0">
                  <div className="text-[13px] text-ink-primary truncate flex items-center gap-2">
                    {p.request}
                    {fresh && (
                      <span className="text-[9px] font-mono uppercase tracking-widest px-1.5 py-0.5 bg-accent-orange text-black rounded-sm shrink-0">
                        just arrived
                      </span>
                    )}
                  </div>
                  <div className="font-mono text-[10px] text-ink-muted uppercase tracking-widest mt-0.5">
                    {p.event_type || "event"} · {p.city || "—"} ·{" "}
                    {p.guest_count || 0} guests
                  </div>
                </div>
                <div className="col-span-3 font-mono text-[12px] text-ink-secondary">
                  {shortINR(p.total_cost_inr)} / {shortINR(p.budget_inr)}
                </div>
                <div className="col-span-2 text-right">
                  <span className="px-3 py-1 hairline rounded-sm font-mono text-[10px] uppercase tracking-widest text-accent-orange border-accent-orange/40">
                    ● {meta.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}


function ArrivalToast({ plan, onView, onDismiss }) {
  const summary = `${plan.event_type || "event"} · ${plan.city || "—"} · ${plan.guest_count || 0} guests`;
  return (
    <div
      data-testid="arrival-toast"
      className="w-[360px] bg-black border border-accent-orange shadow-glowOrange rounded-sm p-4 font-sans"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-7 h-7 bg-accent-orange/20 border border-accent-orange/50 rounded-full">
            <BellRing size={14} className="text-accent-orange" />
          </span>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-accent-orange">
              new approval request
            </div>
            <div className="text-[13px] text-ink-primary font-bold mt-0.5">
              {shortINR(plan.total_cost_inr)} · {summary}
            </div>
          </div>
        </div>
        <button
          type="button"
          data-testid="arrival-toast-close"
          onClick={onDismiss}
          className="text-ink-muted hover:text-ink-primary text-lg leading-none"
          aria-label="dismiss"
        >
          ×
        </button>
      </div>
      <div className="mt-2 text-[12px] text-ink-secondary line-clamp-2">
        {plan.request}
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          data-testid="arrival-toast-dismiss"
          onClick={onDismiss}
          className="text-[11px] font-mono uppercase tracking-widest text-ink-muted hover:text-ink-primary px-3 py-1.5"
        >
          later
        </button>
        <button
          type="button"
          data-testid="arrival-toast-view"
          onClick={onView}
          className="text-[11px] font-mono uppercase tracking-widest bg-accent-orange hover:bg-accent-orangeHover text-black px-3 py-1.5 rounded-sm"
        >
          review now
        </button>
      </div>
    </div>
  );
}
