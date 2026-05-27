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
};

function themeToAction(theme: string): string {
  const lower = theme.toLowerCase();
  if (lower.includes("missing") || lower.includes("lack of")) {
    return "Add " + theme.replace(/^missing\s*/i, "").replace(/^lack of\s*/i, "");
  }
  if (lower.includes("vague") || lower.includes("unclear")) {
    return "Clarify " + theme.replace(/^vague\s*/i, "").replace(/^unclear\s*/i, "");
  }
  return theme;
}

const SEV_ICON: Record<string, string> = { high: "🔴", medium: "🟡", low: "🟢" };

export default function SprintPriorities({
  topFriction,
  recommendation,
  confoundWarning,
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
  } else if (topFriction[2]) {
    const t = topFriction[2];
    items.push({
      icon: SEV_ICON[t.severity] ?? "🟡",
      text: themeToAction(t.theme),
      agents: t.count,
    });
  }

  if (!items.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <h2 className="font-semibold text-sm mb-3">Sprint Priorities</h2>
      {confoundWarning && (
        <p className="text-xs text-orange-600 bg-orange-50 rounded px-3 py-2 mb-3">
          ⚠ Test was confounded — treat these priorities as directional, not conclusive.
        </p>
      )}
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
