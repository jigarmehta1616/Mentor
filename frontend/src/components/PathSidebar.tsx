import type { PathItem } from "../lib/api";

const STATUS_STYLE: Record<PathItem["status"], string> = {
  learned: "bg-emerald-500",
  "in-progress": "bg-amber-400",
  "not-started": "bg-slate-300",
};

interface Props {
  path: PathItem[];
  currentConceptId?: string | null;
}

export function PathSidebar({ path, currentConceptId }: Props) {
  return (
    <aside className="w-full shrink-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:w-72">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Learning path
      </h2>
      <ol className="space-y-1">
        {path.map((c, i) => (
          <li
            key={c.id}
            className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
              c.id === currentConceptId ? "bg-indigo-50 ring-1 ring-brand/30" : ""
            }`}
          >
            <span className={`h-2.5 w-2.5 rounded-full ${STATUS_STYLE[c.status]}`} />
            <span className="w-5 text-xs text-slate-400">{i + 1}</span>
            <span className="flex-1 truncate text-slate-700">{c.name}</span>
            <span className="text-xs tabular-nums text-slate-400">
              {Math.round(c.mastery_level * 100)}%
            </span>
          </li>
        ))}
        {path.length === 0 && (
          <li className="px-2 py-4 text-sm text-slate-400">Start a session to build a path.</li>
        )}
      </ol>
    </aside>
  );
}
