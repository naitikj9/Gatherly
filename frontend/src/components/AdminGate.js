import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, LockKeyhole, ArrowLeft } from "lucide-react";
import { api, adminToken } from "../lib/api";

/**
 * Guards the agent console. Checks access with a cheap admin-only call; if the
 * API answers 401 it asks for the admin token and keeps it for this tab only.
 * When the server runs without ADMIN_TOKEN (local dev) it lets you straight in.
 */
export default function AdminGate({ children }) {
  const [status, setStatus] = useState("checking"); // checking | locked | open
  const [token, setToken] = useState("");
  const [error, setError] = useState(null);

  const check = useCallback(async () => {
    setStatus("checking");
    try {
      await api.listPlans({ limit: 1 });
      setStatus("open");
    } catch (e) {
      if (e?.response?.status === 401) {
        adminToken.clear();
        setStatus("locked");
      } else {
        // API down or erroring: let the console load and show its own errors
        setStatus("open");
      }
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  const submit = async (e) => {
    e.preventDefault();
    if (!token.trim()) return;
    adminToken.set(token.trim());
    setError(null);
    await check();
    if (!adminToken.get()) setError("That token didn't work.");
  };

  if (status === "open") return children;

  return (
    <div className="min-h-screen bg-bg-app text-ink-primary grid place-items-center px-4" data-testid="admin-gate">
      {status === "checking" ? (
        <Loader2 className="animate-spin text-accent-cyan" />
      ) : (
        <form onSubmit={submit} className="w-full max-w-sm hairline bg-bg-surface rounded-sm p-6">
          <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.25em] text-accent-cyan">
            <LockKeyhole size={12} /> agent console
          </div>
          <h1 className="mt-2 font-bold text-xl tracking-tight">Coordinator sign-in</h1>
          <p className="mt-1 text-[13px] text-ink-secondary">
            Enter the admin token to review and approve plans.
          </p>
          <label htmlFor="admin-token" className="sr-only">Admin token</label>
          <input
            id="admin-token"
            type="password"
            autoComplete="current-password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            data-testid="admin-token-input"
            className="mt-4 w-full bg-black hairline rounded-sm px-3 py-2 font-mono text-[13px] focus:outline-none focus:border-accent-cyan/60"
            placeholder="admin token"
          />
          {error && <p className="mt-2 text-[12px] text-accent-red">{error}</p>}
          <button
            type="submit"
            data-testid="admin-token-submit"
            className="mt-4 w-full bg-accent-orange hover:bg-accent-orangeHover text-black font-bold text-[13px] py-2 rounded-sm transition-colors"
          >
            Unlock console
          </button>
          <Link to="/" className="mt-4 inline-flex items-center gap-1.5 text-[11px] text-ink-muted hover:text-accent-orange font-mono uppercase tracking-widest">
            <ArrowLeft size={11} /> back to site
          </Link>
        </form>
      )}
    </div>
  );
}
