import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Music, Heart, Flame, Trash2, Plus, Loader2 } from "lucide-react";
import { api, adminToken } from "../lib/api";
import { cn } from "../lib/utils";

/**
 * Party playlist: guests request songs and upvote each other's picks.
 * Used on the public invite page (`canRequest`) and on the host's plan page,
 * where an admin can also remove a request.
 */
export default function Playlist({ planId, canRequest = true, defaultBy = "", compact = false }) {
  const [songs, setSongs] = useState(null);
  const [form, setForm] = useState({ title: "", artist: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [flash, setFlash] = useState(null);
  const isAdmin = Boolean(adminToken.get());

  const refresh = useCallback(() => {
    api.songs(planId).then((d) => setSongs(d.songs)).catch(() => {});
  }, [planId]);

  // other guests are voting from their phones
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 8000);
    return () => clearInterval(t);
  }, [refresh]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.requestSong(planId, { ...form, by: defaultBy });
      setSongs(res.songs);
      setFlash(res.created ? "Added to the playlist!" : "Already on the list, so we counted your vote.");
      setForm({ title: "", artist: "" });
      setTimeout(() => setFlash(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const vote = async (id) => {
    // optimistic: flip the heart now, the server answer re-sorts the list
    setSongs((list) =>
      list.map((s) => (s.id === id ? { ...s, mine: !s.mine, votes: s.votes + (s.mine ? -1 : 1) } : s))
    );
    try {
      setSongs((await api.voteSong(planId, id)).songs);
    } catch (err) {
      setError(err.message);
      refresh();
    }
  };

  const remove = async (id) => {
    try {
      await api.deleteSong(planId, id);
      setSongs((list) => list.filter((s) => s.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  const top = songs?.[0]?.votes || 0;

  return (
    <section
      className={cn("border border-ivory-200 bg-white rounded-sm", compact ? "p-5" : "p-6")}
      data-testid="playlist"
    >
      <div className="font-mono text-[11px] tracking-[0.25em] uppercase text-gold-600 inline-flex items-center gap-1.5">
        <Music size={12} /> party playlist
      </div>
      <h2 className="font-serif text-2xl mt-1">
        {canRequest ? "What should the DJ play?" : "Your guests' playlist"}
      </h2>
      <p className="text-[13px] text-slate-mid mt-1">
        {canRequest
          ? "Request a song or tap the heart on someone else's pick. Most loved plays first."
          : "Guests request songs from the invite link. Hand this list to your DJ."}
      </p>

      {canRequest && (
        <form onSubmit={submit} className="mt-4 flex flex-col sm:flex-row gap-2" data-testid="song-form">
          <input
            data-testid="song-title"
            value={form.title}
            maxLength={100}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Song (e.g. Kesariya)"
            className="flex-1 min-w-0 border border-ivory-200 bg-white rounded-sm px-3 py-2 text-[14px] focus:outline-none focus:border-emerald-800"
          />
          <input
            value={form.artist}
            maxLength={80}
            onChange={(e) => setForm((f) => ({ ...f, artist: e.target.value }))}
            placeholder="Artist (optional)"
            className="sm:w-40 min-w-0 border border-ivory-200 bg-white rounded-sm px-3 py-2 text-[14px] focus:outline-none focus:border-emerald-800"
          />
          <button
            type="submit"
            data-testid="song-submit"
            disabled={busy || !form.title.trim()}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-800 text-ivory-50 hover:bg-emerald-900 rounded-full text-[13px] font-medium disabled:opacity-40"
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Request
          </button>
        </form>
      )}
      {flash && <p className="mt-2 text-[12.5px] text-emerald-800">{flash}</p>}
      {error && <p className="mt-2 text-[12.5px] text-rose-600">{error}</p>}

      <div className="mt-4">
        {songs === null ? (
          <div className="py-6 grid place-items-center text-slate-soft">
            <Loader2 size={16} className="animate-spin" />
          </div>
        ) : songs.length === 0 ? (
          <p className="py-4 text-[13px] text-slate-soft italic">
            No requests yet. {canRequest ? "Be the first!" : "Share the invite link to get the party going."}
          </p>
        ) : (
          <ol className="space-y-1.5" data-testid="song-list">
            <AnimatePresence initial={false}>
              {songs.map((s, i) => (
                <motion.li
                  key={s.id}
                  layout
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-3 border border-ivory-200 rounded-sm px-3 py-2"
                >
                  <span className="font-mono text-[12px] text-slate-soft w-5 text-right">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[14px]">
                      <span className="truncate">{s.title}</span>
                      {i === 0 && top > 1 && (
                        <span className="shrink-0 text-gold-600" title="Crowd favourite">
                          <Flame size={13} aria-label="Crowd favourite" />
                        </span>
                      )}
                    </div>
                    {(s.artist || s.by) && (
                      <div className="text-[12px] text-slate-mid truncate">
                        {s.artist}
                        {s.artist && s.by ? " · " : ""}
                        {s.by && `asked by ${s.by}`}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => vote(s.id)}
                    disabled={!canRequest}
                    aria-pressed={s.mine}
                    aria-label={s.mine ? `Take back your vote for ${s.title}` : `Vote for ${s.title}`}
                    data-testid="song-vote"
                    className={cn(
                      "inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[12.5px] transition-colors",
                      s.mine
                        ? "bg-rose-600/10 border-rose-600/40 text-rose-600"
                        : "border-ivory-200 text-slate-mid",
                      canRequest && !s.mine && "hover:border-rose-600/40"
                    )}
                  >
                    <Heart size={13} className={s.mine ? "fill-current" : ""} /> {s.votes}
                  </button>
                  {isAdmin && !canRequest && (
                    <button
                      type="button"
                      onClick={() => remove(s.id)}
                      aria-label={`Remove ${s.title}`}
                      className="text-slate-soft hover:text-rose-600"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </motion.li>
              ))}
            </AnimatePresence>
          </ol>
        )}
      </div>
    </section>
  );
}
