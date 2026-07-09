import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../hooks/useSession";

interface Props {
  messages: ChatMessage[];
  streaming: string;
  disabled: boolean;
  onSubmit: (answer: string) => void;
}

const BUBBLE: Record<ChatMessage["kind"], string> = {
  teach: "bg-white border border-slate-200",
  quiz: "bg-indigo-50 border border-brand/20 font-medium",
  answer: "bg-brand text-white ml-auto",
  grade: "bg-slate-100 text-slate-700 text-sm",
};

export function ChatPanel({ messages, streaming, disabled, onSubmit }: Props) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const submit = () => {
    const text = draft.trim();
    if (!text || disabled) return;
    onSubmit(text);
    setDraft("");
  };

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-slate-50 shadow-sm">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 ${BUBBLE[m.kind]}`}
          >
            {m.text}
          </div>
        ))}
        {streaming && (
          <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl border border-slate-200 bg-white px-4 py-2.5">
            {streaming}
            <span className="ml-0.5 animate-pulse">▍</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex gap-2 border-t border-slate-200 p-3">
        <input
          value={draft}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          placeholder="Answer the question…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand disabled:bg-slate-100"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
