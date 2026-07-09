import { useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { DueReviewBadge } from "../components/DueReviewBadge";
import { LevelSwitcher } from "../components/LevelSwitcher";
import { MasteryDashboard } from "../components/MasteryDashboard";
import { PathSidebar } from "../components/PathSidebar";
import { useSession } from "../hooks/useSession";

const TOPICS = [
  { value: "neural-networks", label: "Neural Networks" },
  { value: "sql", label: "SQL" },
];

export function Learn() {
  const { state, start, submitAnswer, switchLevel } = useSession();
  const [topic, setTopic] = useState("neural-networks");

  return (
    <div className="mx-auto max-w-6xl p-4 lg:p-6">
      <header className="mb-5 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-ink">
          Mentor <span className="text-brand">·</span>{" "}
          <span className="text-base font-normal text-slate-500">adaptive learning agent</span>
        </h1>
        <div className="ml-auto flex items-center gap-3">
          <DueReviewBadge due={state.due} />
          <LevelSwitcher
            level={state.level}
            disabled={state.loading || !state.sessionId}
            onChange={switchLevel}
          />
        </div>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {TOPICS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => start(state.userId, topic, state.level)}
          disabled={state.loading}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
        >
          {state.sessionId ? "Restart" : "Start learning"}
        </button>
        {state.error && <span className="text-sm text-rose-600">{state.error}</span>}
      </div>

      <div className="flex flex-col gap-5 lg:flex-row">
        <PathSidebar path={state.path} currentConceptId={state.view?.current_concept?.id} />

        <main className="flex min-h-[28rem] flex-1 flex-col gap-5">
          <div className="h-[28rem]">
            <ChatPanel
              messages={state.messages}
              streaming={state.streaming}
              disabled={state.loading || !state.sessionId || state.view?.done === true}
              onSubmit={submitAnswer}
            />
          </div>
          {state.view?.citations && state.view.citations.length > 0 && (
            <div className="text-xs text-slate-500">
              Sources:{" "}
              {state.view.citations.map((c, i) => (
                <a
                  key={i}
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mr-2 underline hover:text-brand"
                >
                  [{i + 1}] {c.title}
                </a>
              ))}
            </div>
          )}
          <MasteryDashboard progress={state.progress} />
        </main>
      </div>
    </div>
  );
}
