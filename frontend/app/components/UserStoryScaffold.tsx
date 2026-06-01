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

// Map negative friction adjectives to their positive "need" equivalents.
// Keys are the bad phrase; values are what to prepend (or "" to just strip).
// Order matters — longer phrases first so "lack of" beats "lack".
const NEGATIVE_TO_NEED: Array<[RegExp, string]> = [
  [/\black of\b/gi,        ""],
  [/\babsence of\b/gi,     ""],
  [/\bmissing\b/gi,        ""],
  [/\babsent\b/gi,         ""],
  [/\bno\b/gi,             ""],
  [/\binadequate\b/gi,     "stronger"],
  [/\binsufficient\b/gi,   "more complete"],
  [/\bpoor\b/gi,           "stronger"],
  [/\bweak\b/gi,           "stronger"],
  [/\blimited\b/gi,        "more comprehensive"],
  [/\bincomplete\b/gi,     "complete"],
  [/\bpartial\b/gi,        "complete"],
  [/\bsparse\b/gi,         "comprehensive"],
  [/\bunclear\b/gi,        "clearer"],
  [/\bambiguous\b/gi,      "clearer"],
  [/\bvague\b/gi,          "clearer"],
  [/\bconfusing\b/gi,      "clearer"],
  [/\bcomplicated\b/gi,    "simpler"],
  [/\boverwhelming\b/gi,   "simpler"],
  [/\bexcessive\b/gi,      "less"],
  [/\btoo many\b/gi,       "fewer"],
  [/\btoo much\b/gi,       "less"],
  [/\bredundant\b/gi,      "streamlined"],
  [/\bintrusive\b/gi,      "less intrusive"],
  [/\boutdated\b/gi,       "modernized"],
  [/\bsuboptimal\b/gi,     "improved"],
  [/\bdisjointed\b/gi,     "cohesive"],
  [/\bbroken\b/gi,         "working"],
  [/\bhidden\b/gi,         "more visible"],
  [/\bburied\b/gi,         "more visible"],
  [/\bobscured\b/gi,       "more visible"],
  [/\birrelevant\b/gi,     "more targeted"],
  [/\bgeneric\b/gi,        "more specific"],
];

// Convert a friction theme (a PROBLEM) into a need-phrase (a SOLUTION) so
// the user story "I need X" reads naturally. A friction theme like
// "Inadequate Feature Comparison & Detail" should yield "stronger feature
// comparison & detail", not the literal friction phrase.
export function themeToNeed(theme: string): string {
  let cleaned = theme;
  let prepend: string | null = null;
  for (const [pattern, replacement] of NEGATIVE_TO_NEED) {
    if (pattern.test(cleaned)) {
      // Capture the first positive replacement found (don't double-prepend).
      if (replacement && !prepend) prepend = replacement;
      // Reset lastIndex for the global regex before replacing.
      cleaned = cleaned.replace(pattern, "").trim();
    }
  }
  // Remove leading conjunctions / punctuation left behind by stripping
  // ("& Irrelevant Foo" → "& Foo" → "Foo").
  cleaned = cleaned.replace(/^[\s&,]+|(\s*\band\b\s*)+/gi, " ").trim();
  // Collapse double spaces from successive strips.
  cleaned = cleaned.replace(/\s{2,}/g, " ").trim();
  if (!cleaned) return theme;
  const lower = cleaned.charAt(0) === cleaned.charAt(0).toLowerCase()
    ? cleaned
    : cleaned.charAt(0).toLowerCase() + cleaned.slice(1);
  return prepend ? `${prepend} ${lower}` : lower;
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

// Personas often start with "The " (e.g. "The Strategic Growth Seeker") —
// since the template prepends "As a ", that produces "As a The ...".
// Strip a leading article so the sentence reads naturally.
function cleanPersona(name: string): string {
  return name.replace(/^\s*(?:the|a|an)\s+/i, "").trim() || name;
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
          const persona = cleanPersona(findPrimaryPersona(t, resultsBySegment));
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
          const persona = cleanPersona(findPrimaryPersona(t, resultsBySegment));
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
