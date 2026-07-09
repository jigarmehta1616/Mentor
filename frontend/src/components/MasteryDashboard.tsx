import type { ProgressResponse } from "../lib/api";

export function MasteryDashboard({ progress }: { progress: ProgressResponse | null }) {
  if (!progress) return null;
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Mastery
      </h2>
      <div className="space-y-2">
        {progress.mastery.map((m) => (
          <div key={m.id} className="flex items-center gap-3">
            <span className="w-40 truncate text-sm text-slate-700">{m.name}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand transition-all"
                style={{ width: `${Math.round(m.mastery_level * 100)}%` }}
              />
            </div>
            <span className="w-10 text-right text-xs tabular-nums text-slate-500">
              {Math.round(m.mastery_level * 100)}%
            </span>
          </div>
        ))}
      </div>

      {progress.history.length > 0 && (
        <>
          <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Recent quiz history
          </h3>
          <ul className="space-y-1 text-sm">
            {progress.history.slice(0, 6).map((a, i) => (
              <li key={i} className="flex items-center gap-2">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    a.quality_score >= 3 ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                />
                <span className="truncate text-slate-600">{a.concept_id}</span>
                <span className="ml-auto text-xs tabular-nums text-slate-400">
                  {a.quality_score}/5
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
