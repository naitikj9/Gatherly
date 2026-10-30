import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileText, Search, CalendarRange, ShieldCheck, UserCheck } from "lucide-react";
import ConsumerNav from "../components/ConsumerNav";
import ConsumerFooter from "../components/ConsumerFooter";

const AGENTS = [
  {
    icon: FileText,
    name: "Intake",
    role: "Understands the brief",
    body: "Parses your free-text request into a structured event profile, while doing a first-pass safety screen.",
  },
  {
    icon: Search,
    name: "Vendor · RAG",
    role: "Researches the catalog",
    body: "Searches our vetted vendor catalog using retrieval-augmented matching, never inventing a vendor that doesn't exist.",
  },
  {
    icon: CalendarRange,
    name: "Planner",
    role: "Builds the day-of timeline",
    body: "Writes a realistic schedule and computes the exact INR budget — the totals are math, not LLM guesses.",
  },
  {
    icon: ShieldCheck,
    name: "Compliance",
    role: "The safety gate",
    body: "Runs deterministic policy checks (capacity, budget tolerance, availability) and decides whether a human needs to approve.",
  },
];

export default function About() {
  return (
    <div className="min-h-screen bg-ivory-50 text-slate-ink flex flex-col" data-testid="about-root">
      <ConsumerNav />
      <div className="flex-1">
        <div className="max-w-5xl mx-auto px-6 lg:px-10 py-16 md:py-24">
          <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-3">
            › how it works
          </div>
          <h1 className="font-serif text-5xl md:text-6xl tracking-tight leading-tight">
            Four AI agents.
            <br />
            <span className="italic text-emerald-800">One human coordinator.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-slate-mid text-[15px] leading-relaxed">
            Most &quot;AI&quot; planners are a single chat that hallucinates prices and forgets
            constraints. Gatherly is different — we built a six-agent LangGraph system
            where each agent has one job, hands its work to the next in a typed
            schema, and pauses for a real human before any booking is committed.
          </p>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-4">
            {AGENTS.map((a, i) => (
              <div
                key={a.name}
                data-testid={`agent-${i}`}
                className="bg-ivory-50 border border-ivory-200 rounded-sm p-6"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full border border-emerald-700/20 bg-emerald-50 text-emerald-800 grid place-items-center">
                    <a.icon size={16} />
                  </div>
                  <div>
                    <div className="font-serif text-xl tracking-tight">{a.name}</div>
                    <div className="text-[11px] tracking-widest font-mono uppercase text-gold-600">
                      {a.role}
                    </div>
                  </div>
                </div>
                <p className="mt-4 text-[13.5px] text-slate-mid leading-relaxed">{a.body}</p>
              </div>
            ))}
            <div className="bg-emerald-800 text-ivory-50 rounded-sm p-6 md:col-span-2">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gold-500 grid place-items-center">
                  <UserCheck size={16} />
                </div>
                <div>
                  <div className="font-serif text-xl tracking-tight">A Gatherly coordinator</div>
                  <div className="text-[11px] tracking-widest font-mono uppercase text-gold-200">
                    the human in the loop
                  </div>
                </div>
              </div>
              <p className="mt-4 text-[13.5px] text-ivory-50/85 leading-relaxed">
                Every plan that&apos;s ready to book is paused for a real coordinator
                on our team. We check the vendors, the prices, the timing — then
                approve or come back to you with adjustments. No AI ever books a venue.
              </p>
            </div>
          </div>

          <div className="mt-16 border-t border-ivory-200 pt-10 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="font-serif text-2xl">Ready to plan yours?</div>
              <p className="text-slate-mid text-[13.5px] mt-1">Four short questions, one elegant plan.</p>
            </div>
            <Link
              to="/plan"
              data-testid="about-cta"
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[13.5px] font-medium"
            >
              Plan your event <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>
      <ConsumerFooter />
    </div>
  );
}
