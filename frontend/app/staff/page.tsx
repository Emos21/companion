"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { listEscalations, resolveEscalation, Escalation } from "@/lib/api";

const SEV: Record<string, string> = {
  low: "bg-sky-50 text-sky-700 border-sky-200",
  high: "bg-amber-50 text-amber-800 border-amber-200",
  critical: "bg-rose-50 text-rose-700 border-rose-200",
};

function formatTime(timestamp: number) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(timestamp * 1000));
}

function RefreshIcon() {
  return <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M16 8a6.2 6.2 0 0 0-11.4-2L3 8M4 12a6.2 6.2 0 0 0 11.4 2l1.6-2" /><path d="M3 4v4h4M17 16v-4h-4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export default function Staff() {
  const [items, setItems] = useState<Escalation[]>([]);
  const [replies, setReplies] = useState<Record<number, string>>({});
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [resolving, setResolving] = useState<number | null>(null);
  const [notice, setNotice] = useState("");

  const load = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      setItems(await listEscalations());
      setErr("");
    } catch {
      setErr("Could not reach the service. Try refreshing in a moment.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => load(), 5000);
    return () => clearInterval(t);
  }, [load]);

  async function resolve(id: number) {
    const reply = (replies[id] || "").trim();
    if (!reply || resolving) return;
    setResolving(id);
    setNotice("");
    try {
      await resolveEscalation(id, reply);
      setReplies((r) => ({ ...r, [id]: "" }));
      setNotice("Reply sent and escalation resolved.");
      await load();
    } catch {
      setErr("The reply could not be sent. Please try again.");
    } finally {
      setResolving(null);
    }
  }

  const counts = useMemo(() => ({
    critical: items.filter((item) => item.severity === "critical").length,
    high: items.filter((item) => item.severity === "high").length,
  }), [items]);

  return (
    <div className="min-h-screen bg-[#f5f6f4] text-[#182524]">
      <header className="border-b border-[#dfe7e3]/80 bg-[#f5f6f4]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5 sm:px-8">
          <Link href="/" className="flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#173f3a] text-[15px] font-semibold text-white">C</div>
            <div><p className="text-[15px] font-semibold tracking-[-0.01em] text-[#183f3a]">Companion</p><p className="text-[11px] font-medium text-[#70817c]">Team workspace</p></div>
          </Link>
          <Link href="/" className="rounded-full px-3.5 py-2 text-[13px] font-semibold text-[#48706a] transition hover:bg-white hover:text-[#173f3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">Member chat</Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#6c867e]"><span className="h-1.5 w-1.5 rounded-full bg-[#d28b3d]" />Needs attention</div>
            <h1 className="text-[32px] font-semibold leading-tight tracking-[-0.04em] text-[#183f3a]">Human support inbox</h1>
            <p className="mt-2 text-[14px] text-[#71827d]">Conversations Companion has passed to your team.</p>
          </div>
          <button type="button" onClick={() => load(true)} disabled={refreshing} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-[#d2e0da] bg-white px-3.5 text-[12px] font-semibold text-[#42675e] shadow-sm transition hover:border-[#a7c5b8] hover:text-[#173f3a] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2"><RefreshIcon />{refreshing ? "Refreshing" : "Refresh"}</button>
        </div>

        <div className="mt-8 grid grid-cols-3 gap-3 sm:max-w-[560px]">
          <div className="rounded-2xl border border-[#dfe7e3] bg-white p-4 shadow-sm"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#82918c]">Open</p><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#244943]">{items.length}</p></div>
          <div className="rounded-2xl border border-[#f0dfc4] bg-[#fffaf2] p-4"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#a17b4d]">High</p><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#765629]">{counts.high}</p></div>
          <div className="rounded-2xl border border-[#f0d8d8] bg-[#fff8f8] p-4"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#ad6868]">Critical</p><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#853f3f]">{counts.critical}</p></div>
        </div>

        {err && <div role="alert" className="mt-6 flex items-center justify-between gap-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-700"><span>{err}</span><button type="button" onClick={() => load(true)} className="shrink-0 font-semibold underline underline-offset-2">Retry</button></div>}
        {notice && <p role="status" className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-[13px] text-emerald-700">{notice}</p>}

        {loading ? (
          <div className="mt-8 rounded-[22px] border border-[#dfe7e3] bg-white p-8 text-center text-[13px] text-[#71827d]">Loading support requests…</div>
        ) : !err && items.length === 0 ? (
          <div className="mt-8 rounded-[22px] border border-dashed border-[#cbdcd5] bg-white/60 px-6 py-16 text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#e5f2ec] text-[#39745b]"><svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="m7 12 3.2 3.2L17 8.5" /><path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5A8.5 8.5 0 0 0 12 3.5Z" /></svg></div><h2 className="mt-4 text-[16px] font-semibold text-[#244943]">You’re all caught up</h2><p className="mx-auto mt-2 max-w-sm text-[13px] leading-6 text-[#71827d]">New conversations that need a human will appear here automatically.</p></div>
        ) : (
          <div className="mt-8 space-y-4">
            {items.map((e) => (
              <article key={e.id} className="rounded-[22px] border border-[#dfe7e3] bg-white p-5 shadow-[0_8px_28px_rgba(30,68,60,0.05)] sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#edf1ef] pb-4">
                  <div className="flex items-center gap-2.5"><span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] ${SEV[e.severity] || SEV.low}`}>{e.severity}</span><span className="text-[11px] font-medium text-[#8a9994]">Request #{e.id}</span></div>
                  <time className="text-[11px] text-[#8a9994]" dateTime={new Date(e.created_at * 1000).toISOString()}>{formatTime(e.created_at)}</time>
                </div>
                <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_280px]">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8a9994]">Member message</p>
                    <p className="mt-2 text-[15px] leading-7 text-[#294740]">{e.user_message}</p>
                    <p className="mt-5 text-[13px] leading-6 text-[#71827d]"><span className="font-semibold text-[#4d6d65]">Why this was escalated · </span>{e.reason}</p>
                    {e.sources.length > 0 && <p className="mt-3 text-[11px] leading-5 text-[#8a9994]">Related guidance: {e.sources.map((s) => s.title).join(", ")}</p>}
                  </div>
                  <div className="rounded-2xl bg-[#f5f8f6] p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#78918a]">Reply to member</p>
                    {e.draft_answer && <p className="mt-2 border-b border-[#dfe9e3] pb-3 text-[12px] leading-5 text-[#6f817a]">Suggested context: {e.draft_answer}</p>}
                    <textarea value={replies[e.id] || ""} onChange={(ev) => setReplies((r) => ({ ...r, [e.id]: ev.target.value }))} placeholder="Write a thoughtful reply…" aria-label={`Reply to request ${e.id}`} rows={4} className="mt-3 w-full resize-none rounded-xl border border-[#d5e1dc] bg-white px-3 py-2.5 text-[13px] leading-5 text-[#294740] outline-none placeholder:text-[#a0ada8] focus:border-[#6da392] focus:ring-2 focus:ring-[#6da392]/10" />
                    <button type="button" onClick={() => resolve(e.id)} disabled={!(replies[e.id] || "").trim() || resolving === e.id} className="mt-2.5 flex h-10 w-full items-center justify-center rounded-xl bg-[#173f3a] text-[12px] font-semibold text-white transition hover:bg-[#245a52] disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">{resolving === e.id ? "Sending…" : "Send reply & resolve"}</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
