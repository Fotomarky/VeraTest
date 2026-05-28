"use client";
import { useState } from "react";

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type SimResult = {
  scenario_segment: string;
  rationale: string;
  friction_points: string[];
  what_worked: string[];
};

type Props = {
  topFriction: FrictionTheme[];
  whatWorkedThemes: FrictionTheme[];
  goal: string;
  resultsBySegment: Map<string, SimResult[]>;
};

function themeToNeed(theme: string): string {
  const lower = theme.toLowerCase();
  if (/\bmissing\b/.test(lower) || /\black of\b/.test(lower)) {
    const stripped = theme.replace(/^(missing|lack of)\s*/i, "").trim();
    return stripped || theme;
  }
  if (/\bvague\b/.test(lower) || /\bunclear\b/.test(lower)) {
    const stripped = theme.replace(/^(vague|unclear)\s*/i, "").trim();
    return stripped ? "a clearer " + stripped : theme;
  }
  return theme;
}

function findPrimaryPersona(
  theme: FrictionTheme,
  resultsBySegment: Map<string, SimResult[]>
): string {
  const words = theme.theme
    .split(/\s+/)
    .filter((w) => w.length >= 5)
    .map((w) => w.toLowerCase());

  const segmentCounts: Record<string, number> = {};

  for (const [segment, results] of resultsBySegment) {
    for (const r of results) {
      const inFriction = r.friction_points.some((fp) =>
        words.some((w) => fp.toLowerCase().includes(w))
      );
      const inRationale =
        words.length > 0 && words.some((w) => r.rationale.toLowerCase().includes(w));
      if (inFriction || inRationale) {
        segmentCounts[segment] = (segmentCounts[segment] ?? 0) + 1;
      }
    }
  }

  const top = Object.entries(segmentCounts).sort(([, a], [, b]) => b - a)[0];
  return top ? top[0] : "a user";
}

const SEV_BORDER: Record<string, string> = {
  high: "border-l-red-400",
  medium: "border-l-amber-400",
  low: "border-l-green-400",
};

export default function UserStoryScaffold({
  topFriction,
  whatWorkedThemes,
  goal,
  resultsBySegment,
}: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const highMed = topFriction.filter(
    (t) => t.severity === "high" || t.severity === "medium"
  );
  const topWorked = whatWorkedThemes
    .filter((t) => t.severity === "high" || t.severity === "medium")
    .slice(0, 2);

  if (!highMed.length && !topWorked.length) return null;

  async function copyText(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    } catch {}
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="mb-3">
        <h2 className="font-semibold text-sm">User Stories to Write</h2>
        <p className="text-xs text-neutral-400 mt-0.5">
          Generated from simulation findings — copy directly to your backlog.
        </p>
      </div>
      <div className="space-y-3">
        {highMed.map((t, i) => {
          const persona = findPrimaryPersona(t, resultsBySegment);
          const need = themeToNeed(t.theme);
          const text = `As a ${persona},\nI need ${need},\nso that I can ${goal}.`;
          const key = `friction-${i}`;
          return (
            <div
              key={key}
              className={`border-l-2 ${
                SEV_BORDER[t.severity] ?? "border-l-neutral-300"
              } pl-3 pr-3 py-2 rounded-r bg-neutral-50`}
            >
              <pre className="text-xs text-neutral-700 font-sans whitespace-pre-wrap leading-relaxed">
                {text}
              </pre>
              <div className="flex items-center justify-between mt-2">
                <span className="text-[10px] text-neutral-400">
                  Affects {t.count} agent{t.count !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => copyText(text, key)}
                  className="text-[10px] px-2 py-0.5 rounded border border-neutral-300 hover:bg-white text-neutral-600"
                >
                  {copied === key ? "✓ Copied" : "Copy"}
                </button>
              </div>
            </div>
          );
        })}

        {topWorked.map((t, i) => {
          const persona = findPrimaryPersona(t, resultsBySegment);
          const text = `✅ As a ${persona}, ${t.theme} supports ${goal} —\n   preserve this in the next iteration.`;
          const key = `worked-${i}`;
          return (
            <div
              key={key}
              className="border-l-2 border-l-green-400 pl-3 pr-3 py-2 rounded-r bg-green-50"
            >
              <pre className="text-xs text-neutral-700 font-sans whitespace-pre-wrap leading-relaxed">
                {text}
              </pre>
              <div className="flex items-center justify-between mt-2">
                <span className="text-[10px] text-neutral-400">
                  Affects {t.count} agent{t.count !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => copyText(text, key)}
                  className="text-[10px] px-2 py-0.5 rounded border border-neutral-300 hover:bg-white text-neutral-600"
                >
                  {copied === key ? "✓ Copied" : "Copy"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
