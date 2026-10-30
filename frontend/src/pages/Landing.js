import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Sparkles,
  Heart,
  Briefcase,
  Cake,
  Gem,
  ArrowRight,
  ShieldCheck,
  Clock,
  Wallet,
} from "lucide-react";
import ConsumerNav from "../components/ConsumerNav";
import ConsumerFooter from "../components/ConsumerFooter";

const HERO_IMG =
  "https://images.unsplash.com/photo-1772127822531-6a279b5aa968?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwzfHxpbmRpYW4lMjB3ZWRkaW5nJTIwb3V0ZG9vciUyMHZlbnVlfGVufDB8fHx8MTc4MjQ5NDgwN3ww&ixlib=rb-4.1.0&q=85";

const SERVICES = [
  {
    icon: Heart,
    title: "Weddings",
    body: "Mandap, mehendi, sangeet, reception — full-day choreography with mid-budget to luxury vendors.",
    accent: "rose",
  },
  {
    icon: Briefcase,
    title: "Corporate offsites",
    body: "Conferences, product launches, off-site retreats with AV, breakout rooms and continental catering.",
    accent: "emerald",
  },
  {
    icon: Cake,
    title: "Birthdays & parties",
    body: "Rooftop cocktails, themed birthdays and intimate get-togethers — vendors that match your vibe.",
    accent: "gold",
  },
  {
    icon: Gem,
    title: "Anniversaries",
    body: "Milestone celebrations with the right venue, decor and entertainment for the moment.",
    accent: "emerald",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Tell us about your event",
    body: "A quick 4-step form — guests, city, occasion, a couple of preferences.",
  },
  {
    n: "02",
    title: "Our AI plans it in seconds",
    body: "A four-agent system selects vendors, builds the day-of timeline and prices it exactly.",
  },
  {
    n: "03",
    title: "We review every plan by hand",
    body: "A real Gatherly coordinator approves your plan before any vendor is booked.",
  },
  {
    n: "04",
    title: "You confirm and celebrate",
    body: "Once you approve, we book the venue, caterer and team. Show up and enjoy.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-ivory-50 text-slate-ink" data-testid="landing-root">
      <ConsumerNav transparent />

      {/* Hero */}
      <section
        className="relative overflow-hidden border-b border-ivory-200"
        data-testid="hero-section"
      >
        <div className="absolute inset-0">
          <div
            className="absolute right-0 top-0 w-1/2 h-full bg-cover bg-center opacity-90"
            style={{ backgroundImage: `url(${HERO_IMG})` }}
          />
          <div className="absolute right-0 top-0 w-1/2 h-full bg-gradient-to-l from-transparent via-ivory-50/40 to-ivory-50" />
        </div>

        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 py-20 md:py-28 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-700/20 rounded-full text-[11px] tracking-widest uppercase text-emerald-800 font-mono">
              <Sparkles size={12} /> introducing · ai event planning
            </div>
            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="mt-5 font-serif text-5xl md:text-6xl lg:text-7xl leading-[1.02] tracking-tight"
              data-testid="hero-title"
            >
              Heartful celebrations,
              <br />
              <span className="italic text-emerald-800">intelligently</span>{" "}
              planned.
            </motion.h1>
            <p className="mt-6 max-w-xl text-[16px] leading-relaxed text-slate-mid">
              From a 150-guest wedding in Bangalore to a rooftop birthday in
              Mumbai — describe your occasion once and our AI builds a complete,
              costed plan. A real Gatherly coordinator reviews every plan before
              anything is booked.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link
                to="/plan"
                data-testid="hero-plan-cta"
                className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[14px] font-medium tracking-wide transition-colors group"
              >
                <Sparkles size={16} /> Plan your event with AI
                <ArrowRight
                  size={16}
                  className="group-hover:translate-x-0.5 transition-transform"
                />
              </Link>
              <Link
                to="/about"
                className="inline-flex items-center gap-1.5 px-5 py-3 border border-slate-ink/15 hover:border-emerald-800 hover:text-emerald-800 text-[13px] rounded-full transition-colors"
              >
                How it works
              </Link>
            </div>

            <div className="mt-12 flex flex-wrap items-center gap-x-10 gap-y-3 text-[12px] text-slate-mid">
              <Trait icon={<Clock size={14} />} text="Plan in under 30 seconds" />
              <Trait icon={<ShieldCheck size={14} />} text="Reviewed by a human" />
              <Trait icon={<Wallet size={14} />} text="Exact ₹ budget, no surprises" />
            </div>
          </div>
        </div>
      </section>

      {/* Services */}
      <section
        id="services"
        className="border-b border-ivory-200"
        data-testid="services-section"
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-20">
          <div className="flex items-end justify-between gap-6 mb-12">
            <div>
              <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-3">
                › what we plan
              </div>
              <h2 className="font-serif text-4xl md:text-5xl tracking-tight">
                Every occasion, <span className="italic">considered.</span>
              </h2>
            </div>
            <p className="hidden md:block max-w-sm text-[14px] text-slate-mid">
              From intimate gatherings to grand weddings — our AI knows the
              vendors, capacities and price points so you don&apos;t have to.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {SERVICES.map((s, i) => (
              <ServiceCard key={s.title} {...s} idx={i} />
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-b border-ivory-200 bg-ivory-100" data-testid="how-section">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-4">
              <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-3">
                › how it works
              </div>
              <h2 className="font-serif text-4xl md:text-5xl tracking-tight leading-tight">
                Four steps.
                <br />
                <span className="italic text-emerald-800">No spreadsheets.</span>
              </h2>
              <p className="mt-5 text-[14px] text-slate-mid leading-relaxed">
                Behind the scenes, a four-agent LangGraph orchestrates intake,
                vendor research, scheduling and compliance — paused for a
                human at exactly the right moment.
              </p>
            </div>
            <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              {STEPS.map((s) => (
                <div
                  key={s.n}
                  data-testid={`step-${s.n}`}
                  className="bg-ivory-50 border border-ivory-200 rounded-sm p-6 hover:border-emerald-800/40 transition-colors"
                >
                  <div className="font-mono text-[11px] tracking-widest text-gold-600 mb-2">
                    STEP {s.n}
                  </div>
                  <div className="font-serif text-2xl tracking-tight text-slate-ink">
                    {s.title}
                  </div>
                  <p className="mt-2 text-[13.5px] text-slate-mid leading-relaxed">
                    {s.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-b border-ivory-200" data-testid="cta-section">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24 text-center">
          <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 mb-4">
            › ready when you are
          </div>
          <h2 className="font-serif text-5xl md:text-6xl tracking-tight max-w-3xl mx-auto leading-tight">
            Your next celebration is{" "}
            <span className="italic text-emerald-800">three minutes</span> away.
          </h2>
          <p className="mt-5 max-w-xl mx-auto text-slate-mid text-[15px] leading-relaxed">
            Answer four questions. Get a complete, costed plan with venue,
            catering, decor, entertainment and photography — reviewed by a
            human before anything is booked.
          </p>
          <div className="mt-9 flex items-center justify-center gap-3">
            <Link
              to="/plan"
              data-testid="cta-plan-button"
              className="inline-flex items-center gap-2 px-7 py-3.5 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[14px] font-medium tracking-wide transition-colors"
            >
              <Sparkles size={16} /> Plan your event with AI
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      <ConsumerFooter />
    </div>
  );
}

function Trait({ icon, text }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-emerald-800">{icon}</span>
      <span>{text}</span>
    </span>
  );
}

function ServiceCard({ icon: Icon, title, body, accent, idx }) {
  const tone =
    accent === "rose"
      ? "text-rose-600 bg-rose-600/5 border-rose-600/15"
      : accent === "gold"
      ? "text-gold-600 bg-gold-200/30 border-gold-400/30"
      : "text-emerald-800 bg-emerald-50 border-emerald-700/15";
  return (
    <div
      data-testid={`service-${idx}`}
      className="bg-ivory-50 border border-ivory-200 rounded-sm p-6 hover:border-emerald-800/40 transition-colors group"
    >
      <div
        className={`inline-flex items-center justify-center w-10 h-10 border ${tone} rounded-full mb-4`}
      >
        <Icon size={18} />
      </div>
      <div className="font-serif text-2xl tracking-tight">{title}</div>
      <p className="mt-2 text-[13.5px] text-slate-mid leading-relaxed">
        {body}
      </p>
    </div>
  );
}
