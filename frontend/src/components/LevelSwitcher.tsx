import type { Level } from "../lib/api";

const LEVELS: { value: Level; label: string }[] = [
  { value: "eli5", label: "ELI5" },
  { value: "student", label: "Student" },
  { value: "expert", label: "Expert" },
];

interface Props {
  level: Level;
  onChange: (l: Level) => void;
  disabled?: boolean;
}

export function LevelSwitcher({ level, onChange, disabled }: Props) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
      {LEVELS.map((l) => (
        <button
          key={l.value}
          type="button"
          disabled={disabled}
          onClick={() => onChange(l.value)}
          className={`rounded-md px-3 py-1 text-sm font-medium transition ${
            level === l.value
              ? "bg-brand text-white"
              : "text-slate-600 hover:bg-slate-100"
          } disabled:opacity-50`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
