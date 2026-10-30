import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { cn } from "../lib/utils";

export default function ConsumerNav({ transparent = false }) {
  const loc = useLocation();
  const link = (to, label) => {
    const active = loc.pathname === to;
    return (
      <Link
        key={to}
        to={to}
        data-testid={`nav-${label.toLowerCase()}`}
        className={cn(
          "text-[13px] tracking-wide transition-colors",
          active
            ? "text-emerald-800"
            : "text-slate-mid hover:text-emerald-800"
        )}
      >
        {label}
      </Link>
    );
  };

  return (
    <header
      data-testid="consumer-nav"
      className={cn(
        "sticky top-0 z-40 border-b border-ivory-200",
        transparent ? "bg-ivory-50/80 backdrop-blur" : "bg-ivory-50"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link
          to="/"
          data-testid="logo-link"
          className="flex items-center gap-2 group"
        >
          <div className="w-8 h-8 grid place-items-center bg-emerald-800 text-ivory-50 rounded-full">
            <span className="font-serif italic text-base leading-none translate-y-[1px]">
              G
            </span>
          </div>
          <div className="leading-tight">
            <div className="font-serif text-[18px] text-slate-ink tracking-tight">
              Gather<span className="italic text-emerald-800">ly</span>
            </div>
            <div className="text-[9px] font-mono tracking-[0.3em] uppercase text-gold-600 -mt-0.5">
              ai · planning · grace
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {link("/", "Home")}
          {link("/about", "How it works")}
          <a
            href="#services"
            className="text-[13px] tracking-wide text-slate-mid hover:text-emerald-800"
          >
            Services
          </a>
        </nav>

        <Link
          to="/plan"
          data-testid="nav-plan-cta"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 text-[13px] font-medium tracking-wide rounded-full transition-colors"
        >
          <Sparkles size={14} /> Plan with AI
        </Link>
      </div>
    </header>
  );
}
