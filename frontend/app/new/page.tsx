"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const GOAL_EXAMPLES = [
  "sign up for free trial",
  "book a demo",
  "purchase the premium plan",
  "subscribe to the newsletter",
  "download the app",
];

const AUDIENCE_TEMPLATES: Record<string, string> = {
  "B2B SaaS evaluators":
    "Startup founders and engineering leads evaluating CI/dev tools. " +
    "Mostly on desktop, mix of free-trial-seekers and paid evaluators. " +
    "Care about pricing transparency, integrations, and time-to-value.",
  "E-commerce shoppers":
    "Mobile shoppers in the 25-44 age range, mostly returning visitors " +
    "from email and paid social. High price sensitivity, short attention span, " +
    "drop off quickly if shipping isn't clear.",
  "Consumer SaaS / freemium":
    "Mix of new visitors from organic and paid search. " +
    "Most are mobile, 18-34 age range, comparing 2-3 alternatives. " +
    "Will sign up for free but bounce on hidden costs.",
  "Empty / let SimAB infer":
    "",
};

export default function NewRunPage() {
  const router = useRouter();
  const [variantA, setVariantA] = useState<File | null>(null);
  const [variantB, setVariantB] = useState<File | null>(null);
  const [previewA, setPreviewA] = useState<string | null>(null);
  const [previewB, setPreviewB] = useState<string | null>(null);
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFile(which: "a" | "b", file: File | null) {
    if (which === "a") {
      setVariantA(file);
      setPreviewA(file ? URL.createObjectURL(file) : null);
    } else {
      setVariantB(file);
      setPreviewB(file ? URL.createObjectURL(file) : null);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!variantA || !variantB) {
      setError("Both variant images are required");
      return;
    }
    if (!goal.trim()) {
      setError("A conversion goal is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    const form = new FormData();
    form.append("variant_a", variantA);
    form.append("variant_b", variantB);
    form.append("goal", goal);
    form.append("audience", audience);
    try {
      const res = await fetch("/api/runs", { method: "POST", body: form });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text.slice(0, 200)}`);
      }
      const data = await res.json();
      router.push(`/runs/${data.run_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to start run");
      setSubmitting(false);
    }
  }

  const canSubmit = variantA && variantB && goal.trim() && !submitting;

  return (
    <form onSubmit={submit} className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold mb-1">New pretest</h1>
        <p className="text-sm text-neutral-600">
          Upload two variants, describe the goal, and optionally describe your
          audience. Typical run: <strong>60–120 seconds</strong>.
        </p>
      </div>

      {/* Variants section */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-4">
        <h2 className="font-medium">Variants</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FileSlot label="Variant A" file={variantA} preview={previewA}
                    onChange={(f) => handleFile("a", f)} />
          <FileSlot label="Variant B" file={variantB} preview={previewB}
                    onChange={(f) => handleFile("b", f)} />
        </div>
        <p className="text-xs text-neutral-500">
          PNG or JPG. Aim for 1200×800 or larger so the agents can read fine detail.
        </p>
      </section>

      {/* Goal section */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-3">
        <h2 className="font-medium">Conversion goal</h2>
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="What action should visitors take?"
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-neutral-500 mr-1 self-center">Examples:</span>
          {GOAL_EXAMPLES.map((g) => (
            <button
              key={g} type="button" onClick={() => setGoal(g)}
              className="text-xs px-2 py-1 rounded-full border border-neutral-200 text-neutral-600 hover:border-neutral-400 hover:text-neutral-900 transition"
            >
              {g}
            </button>
          ))}
        </div>
      </section>

      {/* Audience section */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-3">
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <h2 className="font-medium">Audience</h2>
          <span className="text-xs text-neutral-500">
            optional — leave empty to infer from variants
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5 mb-2">
          <span className="text-xs text-neutral-500 mr-1 self-center">Quick start:</span>
          {Object.keys(AUDIENCE_TEMPLATES).map((label) => (
            <button
              key={label} type="button"
              onClick={() => setAudience(AUDIENCE_TEMPLATES[label])}
              className="text-xs px-2 py-1 rounded-full border border-neutral-200 text-neutral-600 hover:border-neutral-400 hover:text-neutral-900 transition"
            >
              {label}
            </button>
          ))}
        </div>
        <textarea
          value={audience}
          onChange={(e) => setAudience(e.target.value)}
          rows={5}
          placeholder="Paste a campaign brief, JSON personas, CSV cohort data, or describe in plain text. SimAB will detect the format and extract personas automatically."
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
        <div className="text-xs text-neutral-500 leading-relaxed">
          v0.2 will add a GA4 connector — see <code className="text-neutral-700">integrations/ga4.py</code> for the backend.
        </div>
      </section>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center gap-4">
        <button
          type="submit" disabled={!canSubmit}
          className="px-5 py-2.5 rounded-md bg-neutral-900 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-700 transition"
        >
          {submitting ? "Starting…" : "Run pretest"}
        </button>
        <span className="text-xs text-neutral-500">
          ~20 agents, parallel · uses Gemini Flash-Lite free tier
        </span>
      </div>
    </form>
  );
}

function FileSlot({
  label, file, preview, onChange,
}: {
  label: string;
  file: File | null;
  preview: string | null;
  onChange: (f: File | null) => void;
}) {
  return (
    <div>
      <span className="text-sm font-medium block mb-1">{label}</span>
      {preview ? (
        <div className="relative group">
          <img src={preview} alt={label}
               className="w-full h-48 object-contain bg-neutral-50 rounded border border-neutral-200" />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition rounded flex items-center justify-center">
            <label className="opacity-0 group-hover:opacity-100 transition cursor-pointer bg-white px-3 py-1.5 rounded-md text-xs font-medium shadow">
              Replace
              <input type="file" accept="image/*" className="hidden"
                     onChange={(e) => onChange(e.target.files?.[0] || null)} />
            </label>
          </div>
          <div className="text-xs text-neutral-500 mt-1 truncate">{file?.name}</div>
        </div>
      ) : (
        <label className="block rounded border-2 border-dashed border-neutral-300 h-48 flex items-center justify-center cursor-pointer hover:border-neutral-500 hover:bg-neutral-50 transition">
          <input type="file" accept="image/*" className="hidden"
                 onChange={(e) => onChange(e.target.files?.[0] || null)} />
          <div className="text-center px-4">
            <div className="text-sm text-neutral-700 mb-1">Click to upload</div>
            <div className="text-xs text-neutral-500">PNG or JPG, any size</div>
          </div>
        </label>
      )}
    </div>
  );
}
