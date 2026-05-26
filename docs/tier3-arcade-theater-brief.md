# Tier 3 — Arcade Theater Progress Visualization

**Status:** brief for handoff to a junior dev
**Replaces:** the simple amber progress bar currently rendered by `ProgressBlock` (Tier 1) on the run-detail page
**Surface:** `frontend/app/runs/[id]/page.tsx` — show this only while `run.status ∈ {pending, normalizing, building_scenarios, simulating, auditing, synthesizing}`. Once `complete` or `failed`, the existing results view takes over.

---

## 1. One-line pitch

While the pipeline runs, the user watches twenty pixel-art agents walk through a maze toward two glowing movie-theater screens (variants A and B), pause to evaluate, then return home with their resonance scores. The whole thing reads like a 1983 arcade cabinet.

The pipeline is invisible to the user today. This turns it into the demo moment of the product.

---

## 2. Visual aesthetic — non-negotiable

**Era:** 1983–1992 arcade. Think *Pac-Man* (1980), *Bomberman* (1985), *Sonic the Hedgehog* (1991).

**Color palette** (use these hex values, do not invent):

| Use | Color | Hex |
|---|---|---|
| Background | Deep black | `#0A0A14` |
| Maze walls / borders | Cobalt blue | `#1E40FF` |
| Variant A screen | Hot cyan | `#00E5FF` |
| Variant B screen | Magenta | `#FF1FB3` |
| Agent default | Yellow (Pac-Man) | `#FFEB00` |
| Agent persona accent | Lime / orange / purple | `#7CFF3A` / `#FF8A00` / `#B14CFF` |
| Score "good" badge | Lime | `#7CFF3A` |
| Score "neutral" badge | Amber | `#FFB800` |
| Score "bad" badge | Red | `#FF3A3A` |
| Text | Pixel white | `#F0F0F0` |

**Typography:** Google Font "Press Start 2P" (NES-style 8-bit) for all UI text inside the theater. Body text outside the theater stays in the app's existing system font.

**Mandatory CRT effects:**
- Horizontal scanlines overlay (2px alternating, ~6% alpha black)
- Subtle screen vignette (radial gradient, darker at edges)
- Tiny flicker on the variant screens (random opacity 95–100% at 12fps)

**Forbidden:** anti-aliased smooth shapes, gradients on sprites, drop shadows, modern Material Design surfaces. Everything snaps to a pixel grid.

---

## 3. The mechanic — what happens on screen

### Scene layout (top-down, ~640×400 logical pixels, scaled by `image-rendering: pixelated`)

```
┌─────────────────────────────────────────────────────────────┐
│   [VARIANT A SCREEN]              [VARIANT B SCREEN]        │
│        (cyan glow)                    (magenta glow)        │
│   ┌──────────────┐                ┌──────────────┐          │
│   │              │                │              │          │
│   │  pulsing     │                │  pulsing     │          │
│   │   pattern    │                │   pattern    │          │
│   │              │                │              │          │
│   └──┬───────────┘                └────────────┬─┘          │
│      │                                         │            │
│      │     ──── maze walls ────                │            │
│      │  ┌───┐  ┌───┐  ┌───┐  ┌───┐             │            │
│      │  │   │  │   │  │   │  │   │             │            │
│      │  └───┘  └───┘  └───┘  └───┘             │            │
│      │                                         │            │
│      ├─────────  agents walk here  ────────────┤            │
│      │                                         │            │
│   ┌──┴─────────────────────────────────────────┴───┐        │
│   │            SPAWN LOBBY                          │       │
│   │      (20 agents queue here)                     │       │
│   └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

The maze is *navigable* — agents move through corridors, not through walls. Pathfinding is trivially A* or a precomputed route per agent.

### Phase-by-phase animation

| Pipeline phase | What happens visually |
|---|---|
| `pending` | All 20 agents huddle in the lobby. Subtle idle bob animation. Screens are dark with a slow blink. |
| `normalizing` | A scrolling marquee at top reads "READING BRIEF…". The two screens flicker on, showing animated pixel "static" patterns. |
| `building_scenarios` | Agents sort themselves into colored cohorts (one color per persona segment). They line up in formation in the lobby. |
| `simulating` | The race. Half the agents walk toward Screen A (cohort A), half toward Screen B. Each follows a corridor through the maze. On arrival, the agent stops at the screen base, a pixel "thought bubble" pops up with the persona segment label, the screen pulses brighter, and after a short pause the agent turns and walks back to the lobby carrying a colored score badge over its head (lime/amber/red depending on `resonance_overall`). The amber progress bar at the top fills as agents return home. |
| `auditing` | A "scanner" sprite — horizontal pixel laser — sweeps across the lobby top to bottom, "checking" each agent in turn. Marquee reads "AUDITING TRUST…". |
| `synthesizing` | The screens swap their static for the per-cohort mean resonance score in giant 8-bit digits. A drum-roll dot animation runs. When `complete` lands, a trophy sprite drops over the winning screen with a brief flash. |

If `status === failed`, the entire scene briefly inverts colors and a "GAME OVER" pixel banner drops in.

---

## 4. Data integration

All animation state derives from the existing `/api/runs/{id}/stream` SSE payload. **Do not add new backend endpoints.** The fields you read:

```typescript
type Run = {
  status: "pending" | "normalizing" | "building_scenarios"
        | "simulating" | "auditing" | "synthesizing" | "complete" | "failed";
  scenarios: ScenarioCard[];               // 20 entries when phase ≥ building_scenarios
  simulation_results: SimResult[];         // grows from 0 to 20 during simulating
  audit?: AuditReport;
  synthesis?: Synthesis;
};

type SimResult = {
  scenario_id: string;
  scenario_segment: string;                 // → persona color
  agent_idx: number;                        // → which Pac-Man (0-19)
  cohort: "variant_a" | "variant_b";        // → which screen
  resonance_overall: number;                // → score badge color
};
```

**Mapping rules:**
- Agent identity = `agent_idx` (0–19). Stable across the whole run.
- Persona color = derived from `scenarios[agent_idx].segment` — assign one of 4 accent colors per unique segment in display order.
- Cohort destination = `cohort` field on the SimResult (or `agent_idx % 2` as a fallback before the result lands).
- Score badge color: `resonance_overall ≥ 7` → lime; `4–7` → amber; `< 4` → red.
- An agent's "walked back home" event = its SimResult appears in `simulation_results`. Until then, it's still at or walking to the screen.

---

## 5. Tech stack

**Recommendation: Phaser 3** (game engine, ~280KB gzipped). Justified because:
- Sprite animation + path tweening + scene management are all built-in
- React integration is well-trodden (a thin `<PhaserGame>` wrapper passing props as scene state)
- Two-week learning curve for a junior who has not touched game dev

**Alternative for the budget-minded:** vanilla `<canvas>` + `requestAnimationFrame` + a sprite sheet. Doable in ~1.5x the time. Use this if Phaser feels too heavy.

**Forbidden:** Three.js (3D is wrong), Lottie (vector, not pixel), CSS-only animation (won't scale to 20 agents + pathfinding).

**Asset format:** PNG sprite sheets at 1× pixel scale (e.g. 16×16 per frame), upscaled in CSS with `image-rendering: pixelated`. Do not commit Photoshop files; commit only the final PNGs and a JSON atlas.

---

## 6. Implementation roadmap (ship in stages — each is mergeable on its own)

| Stage | Scope | Acceptance |
|---|---|---|
| **S1 — Static scene** | Draw the maze, lobby, two screens, 20 agent dots (no animation). Wire up the Phaser scene into a React component that receives `run` as a prop. | The scene renders correctly at every phase value; no movement yet. |
| **S2 — Walking agents** | Add A* (or hardcoded) corridor paths from lobby → screen A and lobby → screen B. Animate agents along the path when phase enters `simulating`, return when their SimResult lands. | All 20 agents reach their screen and return, 10 to each. |
| **S3 — Persona color + score badge** | Pull `scenario_segment` per agent, color the sprite. When the agent returns home, draw a score badge over its head with color based on `resonance_overall`. | Color-coding is consistent with the segment legend below the scene. |
| **S4 — Phase choreography** | Add the marquee, the scanner sweep for `auditing`, the drum-roll + trophy for `synthesizing`, and the GAME OVER for `failed`. | Every phase has a distinct visual; no phase ever shows a blank screen. |
| **S5 — Polish** | CRT scanlines, screen flicker, "Press Start 2P" font, 8-bit beep on agent arrival (use Howler.js, ONE sound for now). Add a "reduce motion" toggle that falls back to the Tier 1 progress bar. | Demo-ready. Profiled at 60fps on M1 MacBook. |

Estimated total: **5–8 working days** for someone unfamiliar with Phaser, **2–3 days** for someone who has shipped a Phaser/Pixi prototype before.

---

## 7. Acceptance criteria (definition of done)

- [ ] Visible on `/runs/{id}` whenever `inProgress` is true
- [ ] All 6 active phases produce a distinct visualization
- [ ] 20 agent sprites match agent_idx; cohort split (10/10) visually obvious
- [ ] Phase transitions feel deliberate (no jump cuts; brief crossfade or pixel wipe)
- [ ] Updates within 500ms of receiving an SSE event
- [ ] Maintains 60fps on M1 MacBook Air at the default browser zoom
- [ ] Falls back to Tier 1 `ProgressBlock` when:
  - `prefers-reduced-motion: reduce` is set
  - The user clicks a "Skip animation" toggle (top-right of the scene)
- [ ] Gracefully degrades if `scenarios` is empty (don't crash; show the lobby with grayed-out agents)
- [ ] No new backend endpoints; all data from the existing SSE stream
- [ ] Tested manually on the Highrise and DHL validation cases end to end

---

## 8. Out of scope (deliberately)

- 3D effects, parallax, depth
- Real Pac-Man IP / trademarked sprites — design original characters that *evoke* the era without copying
- Configurable maze layouts — one fixed maze for v1
- Per-agent thought-text from the actual rationale string (the persona segment label is enough)
- Sound effects beyond one 8-bit "blip" on score arrival
- Mobile portrait layout — desktop-first; mobile gets the Tier 1 fallback

---

## 9. Open questions for the design review

1. **Agent shape** — straight homage to Pac-Man (yellow circle, open mouth) or original "blob with eyes" character? IP-safety leans toward original. Pick before any sprite work begins.
2. **Maze layout** — single corridor each side (simple) or branching maze with junctions (more characterful, more pathing work)?
3. **Should agents pass each other?** Pure Pac-Man maze has narrow corridors. Either widen the corridors so agents can overtake, or let them queue politely. Queueing is more honest to the data — only `SIMAB_SIM_CONCURRENCY=6` are active at once anyway.
4. **Score badge persistence** — once an agent is home with their score, does the badge stay visible (cumulative lobby view of all returned agents) or fade? Cumulative is more readable.
5. **What appears on the two screens during `synthesizing`?** Per-cohort overall score in giant 8-bit digits is the proposal. Alternative: a tiny per-dimension bar chart in pixel art. Decide in design review.

---

## 10. References to study before coding

- **Pac-Man (1980)** — corridor pathing, sprite walk cycles, "ghost" AI patterns
- **Bomberman (1985)** — grid-aligned movement, multiple agents on screen at once
- **Sonic the Hedgehog (1991)** — 16-bit color palette, "ring score" UI overlay
- **shadertoy.com CRT shader examples** — for the scanline overlay
- The `frontend/app/runs/[id]/page.tsx` Tier 1 `ProgressBlock` component — the data shape and phase enumeration to mirror

Hand this brief, the existing Tier 1 code, and access to the running backend on `localhost:8001`. The dev should be able to ship S1 within their first day.
