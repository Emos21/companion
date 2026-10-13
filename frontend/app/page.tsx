"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { sendChat, ChatResponse, getConversationMessages } from "@/lib/api";

type Msg = { role: "user" | "bot"; text: string; meta?: ChatResponse; fromTeam?: boolean };

const SEV: Record<string, string> = {
  none: "bg-emerald-50 text-emerald-700 border-emerald-200",
  low: "bg-sky-50 text-sky-700 border-sky-200",
  high: "bg-amber-50 text-amber-800 border-amber-200",
  critical: "bg-rose-50 text-rose-700 border-rose-200",
};

const SUGGESTIONS = [
  "Reschedule a session",
  "Get my deposit back",
  "Sessions in Swahili",
  "How do groups work?",
];

function CompanionMark() {
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#173f3a] text-white shadow-sm shadow-[#173f3a]/20" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M7.5 8.5a4.5 4.5 0 0 1 9 0v1.8a4.5 4.5 0 0 1-9 0V8.5Z" />
        <path d="M7.5 10.5H5.8a2.8 2.8 0 0 0 0 5.6h1.7M16.5 10.5h1.7a2.8 2.8 0 0 1 0 5.6h-1.7M9.2 19.2c1.7.7 3.9.7 5.6 0" />
      </svg>
    </div>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="m3.5 3.5 13 6.5-13 6.5 2.2-6.5-2.2-6.5Z" strokeLinejoin="round" />
      <path d="M5.7 10h8" />
    </svg>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "bot",
      text: "Hi, I’m Companion. I can help with scheduling, deposits, and how the wellbeing groups work. If something needs a person, I’ll bring in a member of the team.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<number | null>(null);
  const [why, setWhy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [awaitingHuman, setAwaitingHuman] = useState(false);
  const lastHumanAt = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  // Close the loop: once a conversation has been escalated, watch for the
  // wellbeing team's reply and drop it straight into the member's chat.
  useEffect(() => {
    if (!awaitingHuman || convId == null) return;
    const timer = setInterval(async () => {
      try {
        const msgs = await getConversationMessages(convId);
        const fresh = msgs.filter((m) => m.role === "human" && m.at > lastHumanAt.current);
        if (fresh.length) {
          lastHumanAt.current = Math.max(...fresh.map((m) => m.at));
          setMessages((prev) => [...prev, ...fresh.map((m) => ({ role: "bot" as const, text: m.content, fromTeam: true }))]);
        }
      } catch {
        // transient, keep polling
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [awaitingHuman, convId]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    setError("");
    setMessages((m) => [...m, { role: "user", text: text.trim() }]);
    setLoading(true);
    try {
      const res = await sendChat(text.trim(), convId);
      setConvId(res.conversation_id);
      setMessages((m) => [...m, { role: "bot", text: res.reply, meta: res }]);
      if (res.escalated) setAwaitingHuman(true);
    } catch {
      setError("We couldn’t reach Companion. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f6f4] text-[#182524]">
      <header className="sticky top-0 z-10 border-b border-[#dfe7e3]/80 bg-[#f5f6f4]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5 sm:px-8">
          <Link href="/" className="flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">
            <CompanionMark />
            <div>
              <p className="text-[15px] font-semibold tracking-[-0.01em] text-[#183f3a]">Companion</p>
              <p className="text-[11px] font-medium text-[#70817c]">Wellbeing support</p>
            </div>
          </Link>
          <Link href="/staff" className="rounded-full px-3.5 py-2 text-[13px] font-semibold text-[#48706a] transition hover:bg-white hover:text-[#173f3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">
            Staff sign in
          </Link>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-8 sm:px-8 lg:grid-cols-[minmax(0,680px)_260px] lg:gap-20 lg:py-14">
        <section aria-labelledby="chat-title">
          <div className="mb-8 max-w-xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#d7e5df] bg-white/70 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5b7770]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#4c9a78]" />
              Here to help
            </div>
            <h1 id="chat-title" className="text-[32px] font-semibold leading-[1.08] tracking-[-0.045em] text-[#183f3a] sm:text-[42px]">
              A little support,<br className="sm:hidden" /> whenever you need it.
            </h1>
            <p className="mt-4 max-w-lg text-[15px] leading-7 text-[#63736f]">
              Ask a question about the programme and Companion will point you in the right direction. You can always ask for a person.
            </p>
          </div>

          <div className="overflow-hidden rounded-[24px] border border-[#dfe7e3] bg-white shadow-[0_12px_40px_rgba(30,68,60,0.07)]">
            <div className="flex items-center justify-between border-b border-[#edf1ef] px-5 py-4 sm:px-6">
              <div className="flex items-center gap-2.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#e5f2ec] text-[#39745b]">
                  <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M5.5 7.2a4.5 4.5 0 0 1 9 0v1.4a4.5 4.5 0 0 1-9 0V7.2Z" /><path d="M5.5 9H4.4a2.3 2.3 0 0 0 0 4.6h1.1M14.5 9h1.1a2.3 2.3 0 0 1 0 4.6h-1.1" /></svg>
                </span>
                <div>
                  <p className="text-[13px] font-semibold text-[#244943]">Companion</p>
                  <p className="text-[11px] text-[#82918c]">Usually replies in a moment</p>
                </div>
              </div>
              <span className="flex items-center gap-1.5 text-[11px] font-medium text-[#5b7770]"><span className="h-1.5 w-1.5 rounded-full bg-[#55a87e]" /> Available</span>
            </div>

            <div className="min-h-[380px] space-y-5 px-5 py-6 sm:px-6" aria-live="polite">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "ml-auto max-w-[88%]" : "max-w-[92%]"}>
                  {m.fromTeam && (
                    <p className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold text-[#2d756b]">
                      <span className="h-1.5 w-1.5 rounded-full bg-[#2d756b]" /> Wellbeing team
                    </p>
                  )}
                  <div
                    className={
                      m.role === "user"
                        ? "rounded-[18px] rounded-br-md bg-[#173f3a] px-4 py-3 text-[14px] leading-6 text-white"
                        : m.fromTeam
                        ? "rounded-[18px] rounded-bl-md border border-[#cfe3d9] bg-white px-4 py-3 text-[14px] leading-6 text-[#294740]"
                        : "rounded-[18px] rounded-bl-md bg-[#f0f5f2] px-4 py-3 text-[14px] leading-6 text-[#294740]"
                    }
                  >
                    {m.text}
                  </div>

                  {m.meta && (
                    <div className="mt-2">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${m.meta.escalated ? SEV[m.meta.decision.severity] : SEV.none}`}>
                          {m.meta.escalated ? "A team member will follow up" : "Answered by Companion"}
                        </span>
                        <button type="button" onClick={() => setWhy(why === i ? null : i)} aria-expanded={why === i} className="text-[11px] font-medium text-[#71827d] underline decoration-[#b4c1bd] underline-offset-2 transition hover:text-[#315e56] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">
                          {why === i ? "Hide details" : "How this was answered"}
                        </button>
                      </div>

                      {why === i && (
                        <div className="mt-2 space-y-1.5 rounded-2xl border border-[#e1ebe6] bg-[#f8faf9] p-3.5 text-[11px] leading-5 text-[#62736e]">
                          <p>{m.meta.decision.reason}</p>
                          <p>Confidence {m.meta.confidence} · Retrieval {m.meta.retrieval_score} · {m.meta.provider === "none" ? "No model used for this safety response" : "Checked against Companion’s knowledge base"}</p>
                          {m.meta.sources.length > 0 && <p>References: {m.meta.sources.map((s) => s.title).join(", ")}</p>}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex max-w-[92%] items-center gap-2 rounded-[18px] rounded-bl-md bg-[#f0f5f2] px-4 py-3 text-[13px] text-[#71827d]">
                  <span className="flex gap-1" aria-hidden="true"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#6f9b8b]" /><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#6f9b8b] [animation-delay:150ms]" /><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#6f9b8b] [animation-delay:300ms]" /></span>
                  Companion is thinking
                </div>
              )}

              {awaitingHuman && !loading && (
                <p className="text-[11px] text-[#8a9994]">A team member has been notified. Their reply will appear here.</p>
              )}

              {messages.length === 1 && !loading && (
                <div className="pt-1">
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-[#8a9994]">Popular questions</p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map((suggestion) => <button key={suggestion} type="button" onClick={() => send(suggestion)} className="rounded-full border border-[#dbe7e1] bg-white px-3.5 py-2 text-[12px] font-medium text-[#4d6d65] transition hover:border-[#8db9a7] hover:bg-[#f2f8f4] hover:text-[#173f3a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2">{suggestion}</button>)}
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {error && <p role="alert" className="mx-5 mb-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-[12px] text-rose-700 sm:mx-6">{error}</p>}

            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="border-t border-[#edf1ef] bg-[#fbfcfb] p-4 sm:p-5">
              <div className="flex items-center gap-2 rounded-2xl border border-[#d5e1dc] bg-white p-1.5 pl-4 shadow-sm transition focus-within:border-[#6da392] focus-within:ring-2 focus-within:ring-[#6da392]/10">
                <input value={input} onChange={(e) => setInput(e.target.value)} aria-label="Message Companion" placeholder="Ask anything about the programme" className="min-w-0 flex-1 bg-transparent py-2 text-[13px] text-[#243e39] outline-none placeholder:text-[#96a39f]" />
                <button type="submit" disabled={loading || !input.trim()} aria-label="Send message" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#173f3a] text-white transition hover:bg-[#245a52] disabled:cursor-not-allowed disabled:opacity-35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2d756b] focus-visible:ring-offset-2"><SendIcon /></button>
              </div>
              <p className="mt-2.5 px-1 text-[10px] leading-4 text-[#8a9994]">For urgent or medical concerns, please contact a qualified professional directly.</p>
            </form>
          </div>
        </section>

        <aside className="hidden pt-[142px] lg:block">
          <div className="border-t border-[#cbdcd5] pt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#6c867e]">A safe place to start</p>
            <h2 className="mt-3 text-[18px] font-semibold leading-6 tracking-[-0.02em] text-[#244943]">Support that knows when to involve a person.</h2>
            <p className="mt-3 text-[13px] leading-6 text-[#71827d]">Companion handles everyday questions and passes sensitive or uncertain conversations to the wellbeing team.</p>
          </div>
          <div className="mt-10 space-y-4 border-t border-[#cbdcd5] pt-4 text-[12px] leading-5 text-[#71827d]">
            <p><span className="font-semibold text-[#42675e]">Private by design</span><br />Share only what you’re comfortable sharing.</p>
            <p><span className="font-semibold text-[#42675e]">Human when needed</span><br />You never have to navigate something difficult alone.</p>
          </div>
        </aside>
      </main>
    </div>
  );
}
