"use client";
import { useState, useEffect } from "react";
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

  // Detect "last audience" availability after mount (localStorage is client-only)
  useEffect(() => {
    setHasLastPreset(loadLastPreset() !== null);
  }, []);

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

  const canSubmit = variantA && variantB && goal.trim() && !submitting;
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
          Upload two variants, describe the goal, pick the audience.
          Typical run: <strong>60–120 seconds</strong>.
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
          />
          <FileSlot
            label="Variant B"
            file={variantB}
            preview={previewB}
            onChange={(f) => handleFile("b", f)}
          />
        </div>
        <p className="text-xs text-neutral-500">
          PNG or JPG. Aim for 1200×800 or larger so the agents can read fine detail.
        </p>
      </section>

      {/* Goal */}
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
          {submitting ? "Starting…" : "Run pretest"}
        </button>
        <span className="text-xs text-neutral-500">
          ~20 agents, parallel · uses Gemini Flash-Lite free tier
        </span>
      </div>
    </form>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Components
// ─────────────────────────────────────────────────────────────────────────────

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
  file,
  preview,
  onChange,
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
        <label className="block rounded border-2 border-dashed border-neutral-300 h-48 flex items-center justify-center cursor-pointer hover:border-neutral-500 hover:bg-neutral-50 transition">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => onChange(e.target.files?.[0] || null)}
          />
          <div className="text-center px-4">
            <div className="text-sm text-neutral-700 mb-1">Click to upload</div>
            <div className="text-xs text-neutral-500">PNG or JPG, any size</div>
          </div>
        </label>
      )}
    </div>
  );
}
