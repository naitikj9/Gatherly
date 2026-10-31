import React, { useCallback, useEffect, useState } from "react";
import { Link2, Check, Users, Leaf, Drumstick } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

export const inviteUrl = (planId) => `${window.location.origin}/invite/${planId}`;

/** Owner's view: the shareable invite link and a live headcount from RSVPs. */
export default function GuestRsvp({ planId }) {
  const [summary, setSummary] = useState(null);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(() => {
    api.rsvps(planId).then((d) => setSummary(d.summary)).catch(() => {});
  }, [planId]);

  // guests answer from their own phones, so keep the count fresh
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 10000);
    return () => clearInterval(t);
  }, [refresh]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl(planId));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this invite link:", inviteUrl(planId));
    }
  };

  const pct = Math.min(100, summary?.fill_pct || 0);

  return (
    <section className="border border-ivory-200 bg-white rounded-sm p-6" data-testid="guest-rsvp">
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 inline-flex items-center gap-1.5">
        <Users size={12} /> guest list
      </div>
      <h2 className="font-serif text-2xl mt-1">Invite your guests</h2>
      <p className="text-[13px] text-slate-mid mt-1">
        Share one link. Guests RSVP from their phone and the headcount updates here.
      </p>

      <button
        type="button"
        onClick={copy}
        data-testid="copy-invite"
        className="mt-4 w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[13px] font-medium transition-colors"
      >
        {copied ? <Check size={14} /> : <Link2 size={14} />}
        {copied ? "Link copied" : "Copy invite link"}
      </button>

      {summary && (
        <div className="mt-5" data-testid="rsvp-summary">
          <div className="flex items-baseline justify-between">
            <span className="font-serif text-3xl">{summary.headcount}</span>
            <span className="text-[12px] text-slate-mid">
              of {summary.planned_guests} planned
            </span>
          </div>
          <div className="h-1 bg-ivory-200 mt-2 overflow-hidden">
            <div
              className={cn("h-full transition-all", summary.over_capacity ? "bg-rose-600" : "bg-emerald-800")}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[12.5px] text-slate-mid">
            <span>{summary.attending} coming</span>
            <span>{summary.not_attending} can't make it</span>
            <span className="inline-flex items-center gap-1"><Leaf size={12} /> {summary.diet.veg} veg</span>
            <span className="inline-flex items-center gap-1"><Drumstick size={12} /> {summary.diet["non-veg"]} non-veg</span>
          </div>
          {summary.over_capacity && (
            <p className="mt-3 text-[12.5px] text-rose-600">
              More guests are coming than planned. Use the what-if simulator to re-price.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
