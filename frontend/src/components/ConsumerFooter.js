import React from "react";
import { Link } from "react-router-dom";

export default function ConsumerFooter() {
  return (
    <footer
      data-testid="consumer-footer"
      className="border-t border-ivory-200 bg-ivory-100"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 grid grid-cols-1 md:grid-cols-4 gap-8 text-[13px] text-slate-mid">
        <div className="md:col-span-2">
          <div className="font-serif text-xl text-slate-ink">
            Gather<span className="italic text-emerald-800">ly</span>
          </div>
          <p className="mt-2 max-w-md leading-relaxed">
            Heartful celebrations, intelligently planned. We pair a four-agent
            AI orchestrator with a real-world event team to bring your
            occasion together — beautifully and within budget.
          </p>
        </div>
        <div>
          <div className="font-mono text-[10px] tracking-[0.25em] uppercase text-gold-600 mb-2">
            services
          </div>
          <ul className="space-y-1.5">
            <li>Weddings &amp; receptions</li>
            <li>Corporate offsites</li>
            <li>Birthdays &amp; parties</li>
            <li>Anniversaries</li>
          </ul>
        </div>
        <div>
          <div className="font-mono text-[10px] tracking-[0.25em] uppercase text-gold-600 mb-2">
            company
          </div>
          <ul className="space-y-1.5">
            <li>
              <Link to="/about" className="hover:text-emerald-800">
                How it works
              </Link>
            </li>
            <li>Cities: Bangalore · Mumbai · Delhi</li>
            <li>hello@gatherly.example</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-ivory-200 py-3 text-[11px] text-slate-soft text-center">
        © Gatherly · A multi-agent AI demo · all bookings reviewed by a
        human
      </div>
    </footer>
  );
}
