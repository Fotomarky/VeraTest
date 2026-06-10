"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  AudiencePreset,
  PRESET_GROUPS,
  PresetGroup,
  PresetKey,
  emptyPreset,
  isEmptyPreset,
  loadLastPreset,
  randomSensibleDefault,
  saveLastPreset,
} from "@/lib/audiencePresets";

const GOAL_EXAMPLES = [
  "sign up for free trial",
  "book a demo",
  "purchase the premium plan",
  "subscribe to the newsletter",
  "download the app",
];

// Passive hints — dimensions worth covering for richer personas. Static (no
// LLM): just a nudge so the free-text brief carries enough signal.
const PERSONA_HINTS = [
  "Age",
  "Interests",
  "Buying behaviour",
  "Tech-savviness",
  "Channel / source",
  "Objections",
];

export default function NewRunPage() {
  const router = useRouter();
  const [variantA, setVariantA] = useState<File | null>(null);
  const [variantB, setVariantB] = useState<File | null>(null);
  const [previewA, setPreviewA] = useState<string | null>(null);
  const [previewB, setPreviewB] = useState<string | null>(null);
  const [goal, setGoal] = useState("");
  const [preset, setPreset] = useState<AudiencePreset>(emptyPreset());
  const [hasLastPreset, setHasLastPreset] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [mode, setMode] = useState<"describe" | "manual">("describe");
  const [description, setDescription] = useState("");
  const [clarification, setClarification] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const descRef = useRef<HTMLTextAreaElement | null>(null);
  const recognitionRef = useRef<any>(null);

  // Detect "last audience" availability after mount (localStorage is client-only)
  useEffect(() => {
    setHasLastPreset(loadLastPreset() !== null);
  }, []);

  // Feature-detect the Web Speech API (Chrome/Edge/Safari; absent in Firefox).
  useEffect(() => {
    const SR =
      typeof window !== "undefined" &&
      ((window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition);
    setSpeechSupported(!!SR);
    return () => recognitionRef.current?.stop?.();
  }, []);

  // Auto-grow the describe textarea to fit its content (capped by max-height CSS).
  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [description]);

  function toggleMic() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = "en-US";
    rec.continuous = true;
    rec.interimResults = true;

    // Append dictation to whatever is already typed. `base` accumulates only
    // finalized chunks so interim updates don't duplicate text. Known
    // trade-off: `base` is captured once at mic start, so edits typed while
    // dictation is live are overwritten by the next onresult.
    let base = description;
    rec.onstart = () => setListening(true);
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    rec.onresult = (e: any) => {
      let finalChunk = "";
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalChunk += t;
        else interim += t;
      }
      if (finalChunk) base = (base ? base + " " : "") + finalChunk.trim();
      const combined = interim ? (base ? base + " " : "") + interim : base;
      setDescription(combined.replace(/\s+/g, " ").trimStart());
    };
    recognitionRef.current = rec;
    rec.start();
  }

  function toggleChip(key: PresetKey, option: string) {
    setPreset((cur) => {
      const arr = cur[key];
      const next = arr.includes(option)
        ? arr.filter((x) => x !== option)
        : [...arr, option];
      return { ...cur, [key]: next };
    });
  }

  function clearPreset() {
    setPreset(emptyPreset());
  }

  function applyRandomDefault() {
    setPreset(randomSensibleDefault());
  }

  function applyLastPreset() {
    const last = loadLastPreset();
    if (last) setPreset(last);
  }

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
    setSubmitted(true);

    if (mode === "describe") {
      if (!variantA || !description.trim()) {
        setError("Upload a screenshot and describe your challenge above.");
        return;
      }
      setSubmitting(true);
      setError(null);
      setClarification(null);
      try {
        const body = new FormData();
        body.append("variant_a", variantA);
        if (variantB) body.append("variant_b", variantB);
        body.append("description", description);
        const launchRes = await fetch("/api/agent/run", { method: "POST", body });
        if (!launchRes.ok) {
          throw new Error(`${launchRes.status}: ${(await launchRes.text()).slice(0, 200)}`);
        }
        const data = await launchRes.json();
        if (data.run_id) {
          router.push(`/runs/${data.run_id}`);
          return;
        }
        setClarification(
          data.question ||
            "Could you add a bit more detail about the goal and audience?"
        );
        setSubmitting(false);
      } catch (err: any) {
        setError(err.message || "Failed to start run");
        setSubmitting(false);
      }
      return;
    }

    if (!variantA || !goal.trim()) {
      setError("Please fill in the highlighted fields above.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const form = new FormData();
    form.append("variant_a", variantA);
    if (variantB) form.append("variant_b", variantB);
    form.append("goal", goal);
    if (!isEmptyPreset(preset)) {
      form.append("audience_preset", JSON.stringify(preset));
      saveLastPreset(preset);
    }
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

  const canSubmit =
    !submitting &&
    !!variantA &&
    (mode === "describe" ? description.trim() : goal.trim());
  const selectedCount =
    preset.age_ranges.length +
    preset.roles.length +
    preset.industries.length +
    preset.interests.length +
    preset.behaviors.length +
    preset.devices.length;

  return (
    <form onSubmit={submit} className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold mb-1">New pretest</h1>
        <p className="text-sm text-neutral-600">
          Upload your design, then describe the challenge — or set the audience
          manually. Typical run: <strong>60–120 seconds</strong>.
        </p>
      </div>

      {/* Variants */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-4">
        <h2 className="font-medium">Variants</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FileSlot
            label="Variant A"
            file={variantA}
            preview={previewA}
            onChange={(f) => handleFile("a", f)}
            hasError={submitted && !variantA}
          />
          <FileSlot
            label="Variant B"
            labelSuffix="optional — skip for single-design analysis"
            file={variantB}
            preview={previewB}
            onChange={(f) => handleFile("b", f)}
          />
        </div>
        <p className="text-xs text-neutral-500">
          PNG or JPG, 1200×800 or larger recommended.
          Upload only Variant A to analyze a single design without comparison.
        </p>
      </section>

      {/* Mode toggle — choose input method after uploading the design */}
      <div className="inline-flex rounded-lg border border-neutral-200 bg-neutral-50 p-1 text-sm">
        {(["describe", "manual"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setClarification(null);
            }}
            className={[
              "px-4 py-1.5 rounded-md transition",
              mode === m
                ? "bg-white shadow-sm font-medium text-neutral-900"
                : "text-neutral-500 hover:text-neutral-800",
            ].join(" ")}
          >
            {m === "describe" ? "Describe it" : "Build it manually"}
          </button>
        ))}
      </div>

      {/* Describe mode — natural-language brief, parsed by the Concierge agent */}
      {mode === "describe" && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-3">
          <h2 className="font-medium">Describe your challenge & audience</h2>

          {/* Static hint chips — dimensions worth mentioning for richer personas */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-neutral-500 mr-0.5">
              Helpful to mention:
            </span>
            {PERSONA_HINTS.map((h) => (
              <span
                key={h}
                className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 border border-neutral-200"
              >
                {h}
              </span>
            ))}
          </div>

          {clarification && (
            <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
              {clarification}
            </div>
          )}

          {/* Expanding pill input with optional mic dictation */}
          <div
            className={`relative rounded-2xl border transition focus-within:ring-2 ${
              submitted && !description.trim()
                ? "border-red-400 focus-within:ring-red-400 bg-red-50"
                : "border-neutral-300 focus-within:ring-neutral-900 bg-white"
            }`}
          >
            <textarea
              ref={descRef}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="e.g. We're testing our new pricing page. The goal is to get startup founders to start a free trial. They're technical, time-poor, and skeptical of long forms — most arrive from a Product Hunt launch."
              className="w-full resize-none bg-transparent rounded-2xl pl-4 pr-12 py-3 text-sm focus:outline-none max-h-72 overflow-y-auto"
            />
            {speechSupported && (
              <button
                type="button"
                onClick={toggleMic}
                aria-label={listening ? "Stop dictation" : "Dictate"}
                aria-pressed={listening}
                title={listening ? "Stop dictation" : "Dictate"}
                className={`absolute bottom-2.5 right-2.5 h-8 w-8 grid place-items-center rounded-full transition ${
                  listening
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
              >
                <MicIcon className="h-4 w-4" />
              </button>
            )}
          </div>

          <p className="text-xs text-neutral-500">
            Write what you're testing, the goal (what should visitors do?), and
            who the audience is — the more of the dimensions above you cover, the
            sharper the personas.
            {speechSupported && " Tap the mic to dictate instead of typing."}
          </p>
        </section>
      )}

      {/* Goal */}
      {mode === "manual" && (
      <>
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-3">
        <h2 className="font-medium">Conversion goal</h2>
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="What action should visitors take?"
          className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 ${
            submitted && !goal.trim()
              ? "border-red-400 ring-red-200 focus:ring-red-400 bg-red-50"
              : "border-neutral-300 focus:ring-neutral-900"
          }`}
        />
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-neutral-500 mr-1 self-center">Examples:</span>
          {GOAL_EXAMPLES.map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setGoal(g)}
              className="text-xs px-2 py-1 rounded-full border border-neutral-200 text-neutral-600 hover:border-neutral-400 hover:text-neutral-900 transition"
            >
              {g}
            </button>
          ))}
        </div>
      </section>

      {/* Audience — chip selector */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 space-y-4">
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <h2 className="font-medium">Audience</h2>
          <span className="text-xs text-neutral-500">
            {selectedCount === 0
              ? "optional — leave empty to infer from variants"
              : `${selectedCount} chip${selectedCount === 1 ? "" : "s"} selected`}
          </span>
        </div>

        {/* Quick actions */}
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={applyRandomDefault}
            className="text-xs px-2 py-1 rounded-full bg-neutral-900 text-white hover:bg-neutral-700 transition"
          >
            Random sensible default
          </button>
          {hasLastPreset && (
            <button
              type="button"
              onClick={applyLastPreset}
              className="text-xs px-2 py-1 rounded-full border border-neutral-300 text-neutral-700 hover:border-neutral-500 transition"
            >
              Use my last audience
            </button>
          )}
          {selectedCount > 0 && (
            <button
              type="button"
              onClick={clearPreset}
              className="text-xs px-2 py-1 rounded-full text-neutral-500 hover:text-neutral-900 transition"
            >
              Clear all
            </button>
          )}
        </div>

        {/* Chip groups */}
        <div className="space-y-3">
          {PRESET_GROUPS.map((group) => (
            <ChipGroup
              key={group.key}
              group={group}
              selected={preset[group.key]}
              onToggle={(opt) => toggleChip(group.key, opt)}
            />
          ))}
        </div>

        {/* Optional notes field */}
        <div>
          <label className="text-sm font-medium text-neutral-700 block mb-1">
            Notes <span className="text-xs text-neutral-500">(optional)</span>
          </label>
          <textarea
            value={preset.notes || ""}
            onChange={(e) => setPreset({ ...preset, notes: e.target.value })}
            rows={2}
            placeholder="Anything the chips don't cover — specific JTBD, constraints, prior context."
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </div>
      </section>
      </>
      )}

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={!canSubmit}
          className="px-5 py-2.5 rounded-md bg-neutral-900 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-700 transition"
        >
          {submitting
            ? mode === "describe"
              ? "Reading your description…"
              : "Starting…"
            : "Run pretest"}
        </button>
        <span className="text-xs text-neutral-500">
          {mode === "describe"
            ? "AI reads your description, then runs ~20 audience agents"
            : "~20 agents, parallel · uses Gemini Flash-Lite free tier"}
        </span>
      </div>
    </form>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Components
// ─────────────────────────────────────────────────────────────────────────────

function MicIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function ChipGroup({
  group,
  selected,
  onToggle,
}: {
  group: PresetGroup;
  selected: string[];
  onToggle: (option: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const inlineCount = group.inlineCount ?? 8;
  const visible = expanded ? group.options : group.options.slice(0, inlineCount);
  const hidden = group.options.length - visible.length;

  return (
    <div>
      <div className="text-xs font-medium text-neutral-600 mb-1">{group.label}</div>
      <div className="flex flex-wrap gap-1.5">
        {visible.map((opt) => {
          const isSel = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onToggle(opt)}
              className={[
                "text-xs px-2.5 py-1 rounded-full border transition",
                isSel
                  ? "bg-neutral-900 text-white border-neutral-900"
                  : "border-neutral-300 text-neutral-700 hover:border-neutral-500 hover:text-neutral-900",
              ].join(" ")}
            >
              {opt}
            </button>
          );
        })}
        {hidden > 0 && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="text-xs px-2 py-1 rounded-full text-neutral-500 hover:text-neutral-900 transition"
          >
            + {hidden} more
          </button>
        )}
        {expanded && group.options.length > inlineCount && (
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="text-xs px-2 py-1 rounded-full text-neutral-500 hover:text-neutral-900 transition"
          >
            show less
          </button>
        )}
      </div>
    </div>
  );
}

function FileSlot({
  label,
  labelSuffix,
  file,
  preview,
  onChange,
  hasError,
}: {
  label: string;
  labelSuffix?: string;
  file: File | null;
  preview: string | null;
  onChange: (f: File | null) => void;
  hasError?: boolean;
}) {
  return (
    <div>
      <span className={`text-sm font-medium block mb-1 ${hasError ? "text-red-600" : ""}`}>
        {label}
        {hasError && <span className="ml-1 text-xs font-normal text-red-500">— required</span>}
        {!hasError && labelSuffix && (
          <span className="ml-1 text-xs font-normal text-neutral-400">{labelSuffix}</span>
        )}
      </span>
      {preview ? (
        <div className="relative group">
          <img
            src={preview}
            alt={label}
            className="w-full h-48 object-contain bg-neutral-50 rounded border border-neutral-200"
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition rounded flex items-center justify-center">
            <label className="opacity-0 group-hover:opacity-100 transition cursor-pointer bg-white px-3 py-1.5 rounded-md text-xs font-medium shadow">
              Replace
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onChange(e.target.files?.[0] || null)}
              />
            </label>
          </div>
          <div className="text-xs text-neutral-500 mt-1 truncate">{file?.name}</div>
        </div>
      ) : (
        <label className={`block rounded border-2 border-dashed h-48 flex items-center justify-center cursor-pointer transition ${
          hasError
            ? "border-red-400 bg-red-50 hover:border-red-500"
            : "border-neutral-300 hover:border-neutral-500 hover:bg-neutral-50"
        }`}>
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => onChange(e.target.files?.[0] || null)}
          />
          <div className="text-center px-4">
            <div className={`text-sm mb-1 ${hasError ? "text-red-600" : "text-neutral-700"}`}>Click to upload</div>
            <div className="text-xs text-neutral-500">PNG or JPG, any size</div>
          </div>
        </label>
      )}
    </div>
  );
}
