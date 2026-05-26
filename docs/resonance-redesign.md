# SimAB v0.3 — Resonance Redesign

**Status:** draft for review
**Author:** design conversation 2026-05-25
**Replaces:** the head-to-head comparative-judgment architecture in v0.2

---

## 1. Goal

Eliminate the structural position bias in the simulator (proven 100% on the DHL sanity run) by mirroring how real A/B tests work: each persona-agent sees **one variant**, scores its **resonance** with their motives/beliefs/situation across 6 dimensions, and the winner is derived from the gap between cohort means. Comparative reasoning is preserved through narrative agents that work on *cohort data*, never on side-by-side images.

This stops claiming "predicted conversion rate" — a claim LLMs cannot honor — and starts claiming "persona-page resonance," which is what LLMs are actually good at.

---

## 2. Architecture at a glance

| | v0.2 (current) | v0.3 (this doc) |
|---|---|---|
| What each sim agent sees | Persona + **both** images | Persona + **one** image (cohort-assigned) |
| What each sim agent outputs | `verdict: variant_a/b/neither` + supporting scores | **Resonance vector** (6 dims, 1–10) + friction + rationale |
| Counterbalancing | Swap image order per agent | Split 50/50 between `cohort_a` and `cohort_b` |
| Winner derivation | Argmax of weighted votes | Argmax of **mean cohort resonance**, with confidence from gap vs. variance |
| Position bias | Possible (proven 100%) | **Structurally impossible** — no agent ever sees two images |
| Auditor checks | Order bias, confidence collapse, coherence | Cohort balance, per-dim variance, persona coverage, low-confidence rate, inflation |
| Comparative narrative | Forced choice from each agent (biased) | Three narrative agents working on cohort data, not raw images |
| Output to PM | "Winner + vote share" | **Resonance vector per cohort + lift direction + diagnostic by dimension** |

---

## 3. Resonance dimensions (the new primitive)

Each sim agent scores the **one** variant they see across exactly these six dimensions, 1–10:

| Dim | Question the agent answers | Framework root |
|---|---|---|
| `motivation` | Does the page address what this persona *wants*? | Fogg M |
| `identity` | Does it speak in this persona's vocabulary and world? | Identity-design literature |
| `situation` | Does it acknowledge their current context (time, prior experience, constraints)? | Jobs-to-be-Done |
| `beliefs` | Does it match this persona's prior beliefs about the category, brand, price? | Cialdini / cognitive consistency |
| `ability` | Does it remove their specific obstacles to acting? | Fogg A |
| `trigger` | Is the next step obvious and right-sized for their decision style? | Fogg T |

Plus `resonance_overall = weighted_mean(dims)` with default weights `motivation 0.25, identity 0.15, situation 0.15, beliefs 0.15, ability 0.15, trigger 0.15` (per-archetype weighting deferred to v0.4 — see §14 Q2).

**Truth claim:** resonance is a *necessary condition* for conversion, not sufficient. PM-facing copy must say this — never claim predicted conversion rates.

---

## 4. Schema changes (`simab/models.py`)

### `SimResult` — replace verdict block with resonance block

Remove: `presented_order`, `verdict`, `outcome`, `visual_impact`, `messaging_alignment`, `fogg_motivation`, `fogg_ability`, `fogg_trigger_clarity`, `loss_gain_framing`, `competing_ctas_count`, `spatial_hierarchy_score`.

Add:

```python
cohort: Literal["variant_a", "variant_b"]
resonance: dict[Literal["motivation","identity","situation","beliefs","ability","trigger"], int]
resonance_overall: float  # weighted mean, 1.0–10.0
intent_signal: Literal["would_act", "would_research", "would_leave"]  # qualitative behavioral cue, not a probability
```

Keep: `scenario_id`, `scenario_segment`, `agent_idx`, `confidence`, `friction_points`, `what_worked`, `rationale`, `trust_signals_found/missing`, `first_impression`, `metacognitive_reflection`, `model`, `latency_ms`.

### `Synthesis` — replace vote block with cohort-resonance block

Remove: `winner` (as currently typed), `raw_vote`, `weighted_vote`, `visual_impact`, `fogg_avg`.

Add:

```python
cohort_resonance: dict[Literal["variant_a","variant_b"],
                       dict[str, float]]   # per dim, mean across cohort
cohort_resonance_overall: dict[str, float] # per variant, weighted mean
resonance_gap: float                       # cohort_b_overall - cohort_a_overall
directional_winner: Literal["variant_a","variant_b","tie"]
gap_significance: Literal["strong","moderate","weak","tie"]  # gap vs. pooled variance
per_persona_resonance: dict[str, dict[str, dict[str, float]]]
   # {persona_segment: {variant_a/b: {dim: score}}} — diagnostic
```

Keep: `coverage_score`, `top_friction`, `what_worked_themes`, `segment_splits`, `recommendation`, `one_line_summary`, `confound_warning`, `trust_signal_gaps`.

### `AuditReport` — drop position-bias check, add cohort checks

Remove: `order_bias_detected`, `first_position_win_rate`.

Add:

```python
cohort_balance: dict[str, int]                     # {variant_a: 10, variant_b: 10}
cohort_persona_balance: dict[str, dict[str, int]]  # by segment too
per_dim_variance: dict[str, float]                 # variance of resonance scores per dim
inflation_warning: bool                            # flag if mean resonance > 8.5 across both cohorts
```

Keep: `trust_level`, `confidence_collapse`, `low_confidence_rate`, `avg_rationale_coherence`, `segment_divergence`, `warnings`, `recommended_action`.

---

## 5. Simulator prompt (skeleton, single-variant)

```
You are evaluating ONE landing page from the perspective of a specific persona.
You will NOT see any other version. Your job is not to predict whether you will
convert — that is unknowable. Your job is to honestly evaluate how well this
page RESONATES with who you are.

PERSONA:
{persona_block}

CONVERSION GOAL THE BRAND WANTS YOU TO TAKE:
{goal}

THE PAGE (image attached): evaluate it on six dimensions.

For each dimension, score 1–10 and give a one-sentence reason.
Be honest, including when the page fits POORLY. Inflation is the enemy.

1. MOTIVATION — does this page speak to what I actually want? ...
2. IDENTITY    — does it speak in my world / vocabulary / register? ...
3. SITUATION   — does it acknowledge my context (time, prior experience, ...)? ...
4. BELIEFS     — does it fit my priors about this category/brand/price? ...
5. ABILITY     — does it remove the specific friction I would feel? ...
6. TRIGGER     — is the next step obvious and right-sized for me? ...

Also list:
- friction_points: specific UI/copy elements that block ME
- what_worked: specific elements that fit ME
- trust_signals_found / missing
- intent_signal: would_act | would_research | would_leave
- confidence: high | medium | low
- rationale: 2-3 sentences from first person

Respond as JSON only.
```

Length target: < 80 lines (vs. 247 today). Shorter prompts reduce default-behavior fallback.

---

## 6. Comparative narrative agents (three, none pick winners)

| Agent | Inputs | Output | Why no position bias |
|---|---|---|---|
| `structural_diff` | Both images | Factual list of differences (layout, copy, form, imagery, CTA, trust signals) — no evaluation | No winner asked → nothing to anchor |
| `symmetric_hypothesis` | Both images | For each variant: 3 reasons it may work for some users, 3 reasons it may fail. Symmetric constraint enforced | Forced balance prevents one-sided rationalization |
| `cohort_narrative` | **Cohort scores + friction themes + persona splits** — *not images* | The PM-facing story: "B resonated +1.8 overall, driven by stronger trigger clarity for analytical personas. A's weakness was situational fit for new users…" | Operates on numbers, not visuals — bias impossible |

Run `cohort_narrative` last, after sim + audit + theme clustering complete.

---

## 7. Updated auditor & synthesizer

**Auditor checks** (`simab/agents/auditor.py`):
- Cohort balance: are both cohorts roughly 50/50 in count and persona mix?
- Per-dimension variance: low variance across all 20 agents on a dim = collapse signal (LLM giving the same answer regardless of persona)
- Mean-resonance inflation: if both cohorts > 8.5 overall, flag agreeableness inflation
- Low-confidence rate: unchanged
- Coherence (LLM-as-judge on rationale ↔ resonance): unchanged but adapted

**Synthesizer** (`simab/agents/synthesizer.py`):
- Compute `cohort_resonance[dim]` = mean of agent scores in that cohort
- `resonance_gap = cohort_b.overall - cohort_a.overall`
- `directional_winner`: sign of gap; `tie` if `|gap| < 0.3` or `|gap| < pooled_std` (see §14 Q3 — tunable)
- `gap_significance`: `strong` if `|gap| > 1.5 * pooled_std` and `|gap| > 0.8`; `moderate` if `> pooled_std`; `weak` otherwise
- Friction clustering: unchanged but partition by cohort first
- Per-persona view: matrix of `{segment, variant, dim} → score` for the dashboard heatmap

---

## 8. Model configurability (per-phase override)

Every phase model-configurable through `config.py` and the API. User-facing dropdown surfaces the two models confirmed for this account:

- **Gemini 3 Flash Preview** — cheaper, faster, default for the 20 parallel simulator calls
- **Gemini 3.5 Flash** — more capable, default for strategic phases (normalizer, scenarios, auditor, synthesizer, narrative)

```python
# simab/config.py — additions
class ModelConfig(BaseModel):
    normalizer:  str = "gemini-3.5-flash"
    scenarios:   str = "gemini-3.5-flash"
    simulator:   str = "gemini-3-flash-preview"   # user-overridable per run
    auditor:     str = "gemini-3.5-flash"
    synthesizer: str = "gemini-3.5-flash"
    narrative:   str = "gemini-3.5-flash"
```

Frontend `/new` page exposes one dropdown labeled **"Evaluator model"** that maps to the `simulator` slot — the one that matters most for cost/quality. Two options shown to the user with cost/speed labels:

- **Fast & cheap** → `gemini-3-flash-preview` (default)
- **Most accurate** → `gemini-3.5-flash`

API: accept `model_simulator` (and optionally other slots) as form fields on `POST /api/runs`. Update `simab/llm.py` rate-limiter buckets to register both model IDs. **Exact model ID strings must be verified against the user's Google AI Studio account** during P4 implementation — if the SDK rejects either ID, fall back to closest-name match and surface a warning.

---

## 9. Persona grounding UX (frontend `/new` page)

Replace the current free-text `audience` field with a fast preset chip selector. No typing required; user can ship a configured audience in < 15 seconds.

### Form schema

```typescript
interface AudiencePreset {
  age_ranges:   string[]   // multi-select, optional — e.g. ["25-34", "35-44"]
  roles:        string[]   // Student, Founder, IC, Manager, Director, C-level, Parent, Retiree, …
  industries:   string[]   // SaaS, FinTech, Healthcare, E-commerce, Education, Retail, …
  interests:    string[]   // Tech, Design, Marketing, Ops, Finance, Health, Lifestyle, …
  behaviors:    string[]   // Impulse buyer, Comparison shopper, Brand loyal, Deal hunter, Early adopter, Skeptic, …
  devices:      string[]   // Desktop, Mobile, Tablet
  notes?:       string     // optional free text for anything not covered
}
```

### UX rules
- All fields multi-select chips, no required fields (smart defaults if everything left empty)
- Each chip group shows max 8 options inline, "+ more" to expand to full list
- A live preview pane on the right shows: "Inferred personas: [3 chips of segment names]" — updates as the user toggles chips
- One **"Use my last audience"** quick action restoring the previous preset from localStorage
- One **"Random sensible default"** for users who just want to demo

### Backend
- `AudiencePreset` flows to the normalizer as structured JSON instead of a paragraph
- Normalizer prompt updated: "Given the following audience presets, infer 3–5 distinct personas…" — far less hallucination because the input is structured
- `Brief.inferred_personas` shape unchanged downstream

### Preset library
Store the option lists in `frontend/lib/audiencePresets.ts` so PMs can extend without backend changes. Seed it with ~50 options across all groups based on common B2B/B2C SaaS audiences.

---

## 10. Validation metric

Drop "predicted vs actual conversion rate" — that comparison is dishonest given the truth claim change.

Adopt **binary directional accuracy**: does the variant with higher overall resonance match the documented winner in `validation/dataset.csv`?

- Baselines: random (50%), always_b (currently 100% due to publication bias — acknowledge in the report)
- SimAB target on the existing 10-case set: > 70%, ideally with breakdown by `gap_significance` (strong-signal cases should be ≥ 85%)
- Add a `gap_significance ≠ tie` filter: when SimAB declines to call a winner, don't count it as a miss — report it as `abstain_rate`
- Dataset expansion to a balanced ~100-case set is **out of scope for this redesign** (separate workstream)

---

## 11. File touchpoints

| File | Change |
|---|---|
| `simab/models.py` | Replace SimResult, Synthesis, AuditReport per §4 |
| `simab/agents/simulator.py` | New single-variant prompt; remove counterbalancing logic; assign cohort by `agent_idx % 2`; map response → resonance schema |
| `simab/agents/scenarios.py` | Accept structured `AudiencePreset`; minor prompt updates |
| `simab/agents/normalizer.py` | Consume `AudiencePreset` JSON, output the same `Brief` shape |
| `simab/agents/auditor.py` | Drop order-bias checks; add cohort balance / variance / inflation checks |
| `simab/agents/synthesizer.py` | Cohort-aggregation logic, gap & significance computation, per-persona matrix |
| `simab/agents/narrative.py` | **New file** — `cohort_narrative` agent |
| `simab/config.py` | Add `ModelConfig` per-phase override; update model defaults to Gemini 3.x |
| `simab/llm.py` | Register `gemini-3-flash-preview` and `gemini-3.5-flash` in the rate-limiter bucket map |
| `simab/main.py` | Accept `model_simulator` form field on POST /api/runs; consume `AudiencePreset` JSON |
| `simab/exports.py` | Rewrite markdown / PM summary / Slack message for resonance output |
| `frontend/app/new/page.tsx` | Replace free-text audience with chip selector; add model dropdown |
| `frontend/lib/audiencePresets.ts` | **New file** — preset option library |
| `frontend/app/runs/[id]/page.tsx` | Replace winner-vote viz with resonance heatmap + dimension breakdown |
| `tests/test_smoke.py` | Update schema assertions |
| `tests/test_exports.py` | Update fixture to new SimResult shape |
| `validation/run.py` | Switch baseline_simab return to directional winner; add abstain_rate metric |

---

## 12. Rollout phases (so we can ship incrementally)

| Phase | Scope | Acceptance |
|---|---|---|
| **P0 — Wipe** | Delete `simab.db`, `uploads/`, and `/tmp/simab_live.db`; document the breaking change in `README.md` | Fresh DB; current dashboard shows zero runs |
| **P1 — Schema + simulator** | New `SimResult`, new simulator prompt, hardcoded `cohort = agent_idx % 2`. Auditor/synthesizer stubbed to compute cohort means. | DHL sanity run produces non-tie result; per-agent rationales clearly vary; bias signature gone |
| **P2 — Auditor + synthesizer + narrative agent** | Cohort balance/variance checks, gap+significance computation, `cohort_narrative` agent. | Synthesis includes `cohort_resonance`, `resonance_gap`, `gap_significance`; narrative reads as an A/B analysis, not a side-by-side |
| **P3 — Audience preset UX** | Chip selector frontend, `AudiencePreset` API contract, normalizer prompt update. | New run can be configured in < 15s without typing; inferred personas reflect chip selection meaningfully |
| **P4 — Model selector + validation rerun** | Per-phase model config exposed, frontend dropdown for simulator model (Gemini 3 Flash Preview / Gemini 3.5 Flash), validation harness rerun on `dataset.csv` with directional metric. | Validation report shows directional accuracy + abstain_rate by model choice |

Estimated effort: P0 ~15min, P1 ~3h, P2 ~3h, P3 ~3h, P4 ~2h. Total ~11h focused work.

---

## 13. Explicitly out of scope

- Expanding `validation/dataset.csv` to a balanced ~100-case set — separate workstream
- Live-URL rendering / Playwright integration — future enhancement
- Real-A/B-result feedback loop for calibration — future enhancement, the killer long-term feature
- Reproducibility / deterministic seeds — future enhancement
- A2A and MCP server contract changes — both surfaces already return the `Run` document; new fields land automatically. No breaking change there.
- DB migration of v0.2 runs — **wipe instead** (current DB is test pollution, no real runs to preserve)

---

## 14. Open questions

1. **Model IDs** — **resolved.** User dropdown surfaces `gemini-3-flash-preview` (default for simulator) and `gemini-3.5-flash` (default for strategic phases + selectable for simulator). Exact ID strings verified during P4 against the AI Studio account.
2. **Per-persona resonance weights** — **decision: fixed defaults for v0.3.** Default weights `motivation 0.25, others 0.15`. Per-archetype weighting deferred to v0.4 pending feedback.
3. **Abstain threshold** — **decision: `|gap| < 0.3` OR `|gap| < pooled_std` ⇒ tie** for v0.3 (conservative). Tuned empirically after first validation rerun.
4. **Backward compatibility** — **resolved: wipe.** Tag the release `v0.3.0` with a breaking schema notice; no migration path.
