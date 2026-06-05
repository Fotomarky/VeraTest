"use client";
import { useState } from "react";

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: Array<{ quote: string; agent_idx?: number | null; segment?: string | null }>;
};

type Props = {
  themes: FrictionTheme[];
  title?: string;
  emptyMessage?: string;
};

const SEV_STYLES: Record<string, { bar: string; bg: string; label: string; dot: string }> = {
  high:   { bar: "border-l-red-400",    bg: "bg-red-50",   label: "HIGH", dot: "bg-red-400"   },
  medium: { bar: "border-l-amber-400",  bg: "bg-amber-50", label: "MED",  dot: "bg-amber-400" },
  low:    { bar: "border-l-green-400",  bg: "bg-green-50", label: "LOW",  dot: "bg-green-400" },
};

export default function FrictionList({
  themes,
  title = "Top friction in losing variant",
  emptyMessage = "No significant friction detected.",
}: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!themes.length) {
    return (
      <section className="rounded-lg border border-neutral-200 bg-white p-5">
        <h2 className="font-semibold mb-2 text-sm">{title}</h2>
        <p className="text-sm text-neutral-400">{emptyMessage}</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold text-sm">{title}</h2>
        <span className="text-xs text-neutral-400">{themes.length} theme{themes.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="space-y-2">
        {themes.map((t, i) => {
          const sev = SEV_STYLES[t.severity] || SEV_STYLES.medium;
          const isOpen = expanded === i;
          const hasQuotes = t.example_quotes && t.example_quotes.length > 0;
          return (
            <div key={i} className={`border-l-2 ${sev.bar} ${sev.bg} pl-3 pr-3 py-2 rounded-r`}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium">{t.theme}</span>
                    <span className="flex items-center gap-1 text-[10px] text-neutral-500">
                      <span className={`w-1.5 h-1.5 rounded-full ${sev.dot}`} />
                      {sev.label} · {t.count} agent{t.count !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
                {hasQuotes && (
                  <button
                    onClick={() => setExpanded(isOpen ? null : i)}
                    className="text-[10px] text-neutral-500 hover:text-neutral-800 shrink-0 whitespace-nowrap mt-0.5"
                  >
                    {isOpen ? "▲ hide" : "▼ quotes"}
                  </button>
                )}
              </div>
              {isOpen && hasQuotes && (
                <div className="mt-2 space-y-1">
                  {t.example_quotes.map((q, j) => (
                    <p key={j} className="text-xs text-neutral-600 italic">&ldquo;{q.quote}&rdquo;</p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}