import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Calendar, MapPin, Loader2, PartyPopper, Clock } from "lucide-react";
import ConsumerNav from "../components/ConsumerNav";
import ConsumerFooter from "../components/ConsumerFooter";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

const DIETS = [
  { id: "veg", label: "Veg" },
  { id: "non-veg", label: "Non-veg" },
  { id: "any", label: "No preference" },
];

/** Public page a guest opens from the invite link. */
export default function Invite() {
  const { planId } = useParams();
  const [card, setCard] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ name: "", attending: null, plus_ones: 0, diet: "any", note: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(null);

  useEffect(() => {
    api.invite(planId).then(setCard).catch((e) => setError(e.message));
  }, [planId]);

  const update = (patch) => setForm((f) => ({ ...f, ...patch }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || form.attending === null) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.rsvp(planId, form);
      setSent({ attending: form.attending, updated: res.updated });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-ivory-50 text-slate-ink flex flex-col" data-testid="invite-root">
      <ConsumerNav />
      <div className="flex-1">
        <div className="max-w-xl mx-auto px-6 py-12 md:py-16">
          {!card && !error && (
            <div className="py-24 grid place-items-center text-slate-mid">
              <Loader2 className="animate-spin" />
            </div>
          )}
          {error && !card && (
            <div className="border border-rose-600/30 bg-rose-600/5 text-rose-600 px-4 py-3 rounded-sm text-[13px]">
              {error}
            </div>
          )}

          {card && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600">
                you&apos;re invited
              </div>
              <h1 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight mt-2">
                A <span className="capitalize">{card.event_type || "celebration"}</span> in{" "}
                <span className="italic text-emerald-800">{card.city}</span>
              </h1>
              <div className="mt-4 space-y-1.5 text-[14px] text-slate-mid">
                {card.event_date && (
                  <div className="inline-flex items-center gap-2">
                    <Calendar size={14} /> {card.weekday ? `${card.weekday}, ` : ""}
                    {card.event_date}
                    {card.days_until > 0 && (
                      <span className="text-gold-600">· in {card.days_until} days</span>
                    )}
                  </div>
                )}
                {card.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin size={14} /> {card.venue}
                  </div>
                )}
              </div>

              {card.timeline?.length > 0 && (
                <ol className="mt-6 border-l border-ivory-200 pl-4 space-y-1.5">
                  {card.timeline.map((t, i) => (
                    <li key={i} className="text-[13px]">
                      <span className="inline-flex items-center gap-1 font-mono text-slate-soft w-20">
                        <Clock size={11} /> {t.time}
                      </span>{" "}
                      {t.activity}
                    </li>
                  ))}
                </ol>
              )}

              {sent ? (
                <div
                  data-testid="rsvp-thanks"
                  className="mt-10 border border-emerald-700/30 bg-emerald-50 rounded-sm p-6 text-center"
                >
                  <PartyPopper className="mx-auto text-emerald-800" />
                  <p className="font-serif text-2xl mt-2">
                    {sent.attending ? "See you there!" : "Thanks for letting us know."}
                  </p>
                  <p className="text-[13px] text-slate-mid mt-1">
                    {sent.updated ? "We updated your earlier RSVP." : "Your RSVP is in."} Open this link
                    again any time to change it.
                  </p>
                </div>
              ) : !card.open ? (
                <p className="mt-10 text-[14px] text-slate-mid">This event isn&apos;t taking RSVPs.</p>
              ) : (
                <form onSubmit={submit} className="mt-10 space-y-5" data-testid="rsvp-form">
                  <label className="block">
                    <span className="text-[13px] text-slate-mid">Your name</span>
                    <input
                      data-testid="rsvp-name"
                      value={form.name}
                      maxLength={80}
                      onChange={(e) => update({ name: e.target.value })}
                      className="mt-1 w-full border border-ivory-200 bg-white rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:border-emerald-800"
                      placeholder="Asha Rao"
                      required
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { v: true, label: "Joyfully accept" },
                      { v: false, label: "Regretfully decline" },
                    ].map((o) => (
                      <button
                        key={String(o.v)}
                        type="button"
                        data-testid={`rsvp-${o.v ? "yes" : "no"}`}
                        onClick={() => update({ attending: o.v })}
                        className={cn(
                          "px-4 py-3 rounded-sm border text-[13.5px] transition-colors",
                          form.attending === o.v
                            ? "bg-emerald-800 border-emerald-800 text-ivory-50"
                            : "border-ivory-200 bg-white hover:border-emerald-800"
                        )}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>

                  {form.attending && (
                    <>
                      <label className="block">
                        <span className="text-[13px] text-slate-mid">Bringing anyone? (up to 5)</span>
                        <input
                          type="number"
                          min={0}
                          max={5}
                          value={form.plus_ones}
                          onChange={(e) =>
                            update({ plus_ones: Math.max(0, Math.min(5, Number(e.target.value) || 0)) })
                          }
                          className="mt-1 w-28 border border-ivory-200 bg-white rounded-sm px-3 py-2 text-[14px]"
                        />
                      </label>
                      <div>
                        <span className="text-[13px] text-slate-mid">Food preference</span>
                        <div className="mt-1 flex gap-2">
                          {DIETS.map((d) => (
                            <button
                              key={d.id}
                              type="button"
                              onClick={() => update({ diet: d.id })}
                              className={cn(
                                "px-3.5 py-1.5 rounded-full text-[12.5px] border",
                                form.diet === d.id
                                  ? "bg-emerald-800 border-emerald-800 text-ivory-50"
                                  : "border-ivory-200 bg-white"
                              )}
                            >
                              {d.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  <label className="block">
                    <span className="text-[13px] text-slate-mid">A note for the hosts (optional)</span>
                    <textarea
                      value={form.note}
                      maxLength={200}
                      rows={2}
                      onChange={(e) => update({ note: e.target.value })}
                      className="mt-1 w-full border border-ivory-200 bg-white rounded-sm px-3 py-2 text-[14px]"
                    />
                  </label>

                  {error && <p className="text-[13px] text-rose-600">{error}</p>}

                  <button
                    type="submit"
                    data-testid="rsvp-submit"
                    disabled={busy || !form.name.trim() || form.attending === null}
                    className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[14px] font-medium disabled:opacity-40"
                  >
                    {busy && <Loader2 size={14} className="animate-spin" />} Send RSVP
                  </button>
                </form>
              )}
            </motion.div>
          )}
        </div>
      </div>
      <ConsumerFooter />
    </div>
  );
}
