import type { DueItem } from "../lib/api";

export function DueReviewBadge({ due }: { due: DueItem[] }) {
  const count = due.length;
  return (
    <span
      title={count ? due.map((d) => d.name).join(", ") : "No reviews due"}
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${
        count ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500"
      }`}
    >
      🔁 {count} due for review
    </span>
  );
}
