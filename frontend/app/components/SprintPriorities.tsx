type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type Props = {
  topFriction: FrictionTheme[];
  recommendation?: string;
  confoundWarning?: string;
  totalAgents?: number;
  personaCount?: number;
};

function themeToAction(theme: string): string {
  const lower = theme.toLowerCase();
  if (/\bmissing\b/.test(lower) || /\black of\b/.test(lower)) {
    const stripped = theme.replace(/^(missing|lack of)\s*/i, "").trim();
    return stripped ? "Add " + stripped : theme;
  }
  if (/\bvague\b/.test(lower) || /\bunclear\b/.test(lower)) {
    const stripped = theme.replace(/^(vague|unclear)\s*/i, "").trim();
    return stripped ? "Clarify " + stripped : theme;
  }
  return theme;
}

const SEV_ICON: Record<string, string> = { high: "🔴", medium: "🟡", low: "🟢" };

export default function SprintPriorities({
  topFriction,
  recommendation,
  confoundWarning,
  totalAgents,
  personaCount,
}: Props) {
  const highMed = topFriction
    .filter((t) => t.severity === "high" || t.severity === "medium")
    .slice(0, 2);

  const items: Array<{ icon: string; text: string; agents?: number }> = highMed.map((t) => ({
    icon: SEV_ICON[t.severity] ?? "🟡",
    text: themeToAction(t.theme),
    agents: t.count,
  }));

  if (recommendation) {
    items.push({ icon: "💡", text: `Next hypothesis: ${recommendation}` });
  } else {
    const third = topFriction.find(
      (t, i) => i >= 2 && (t.severity === "high" || t.severity === "medium")
    );
    if (third) {
      items.push({
        icon: SEV_ICON[third.severity] ?? "🟡",
        text: themeToAction(third.theme),
        agents: third.count,
      });
    }
  }

  if (!items.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="font-semibold text-sm">Sprint Priorities</h2>
        <div className="flex items-center gap-1.5">
          {totalAgents != null && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600 font-mono">
              {totalAgents} agents
            </span>
          )}
          {personaCount != null && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600 font-mono">
              {personaCount} segment{personaCount !== 1 ? "s" : ""}
            </span>
          )}
          {confoundWarning && (
            <span className="text-[11px] text-orange-500" title={confoundWarning}>
              ⚠ directional
            </span>
          )}
        </div>
      </div>
      <ol className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-sm">
            <span className="font-mono text-neutral-400 text-xs mt-0.5 w-4 flex-shrink-0">
              {i + 1}.
            </span>
            <span className="flex-shrink-0">{item.icon}</span>
            <span className="flex-1 text-neutral-800">{item.text}</span>
            {item.agents != null && (
              <span className="text-xs text-neutral-400 flex-shrink-0">
                → {item.agents} agent{item.agents !== 1 ? "s" : ""}
              </span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
