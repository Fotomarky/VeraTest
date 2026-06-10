# Hackathon Compliance Audit & Implementation Plan

**Contest:** Google Cloud Rapid Agent Hackathon — Arize Track
**Deadline:** June 11, 2026, 2:00 PM PT
**Audited:** June 9, 2026
**Repo:** `Fotomarky/VeraTest`

---

## 1. Verdict against the Official Rules

The single binding requirement (Rule §7.A) is:

> Build a functional agent — **powered by Gemini AND Google Cloud Agent Builder** — that **integrates a Partner Entity's MCP server** to solve a real challenge.

All three legs must be **imported and called at runtime**, not merely named. Status:

| # | Rule | Requirement | Status | Severity |
|---|------|-------------|--------|----------|
| 1 | §7.A | **Gemini** used at runtime | ✅ Yes — `google-genai` via `simab/llm.py` | OK |
| 2 | §7.A | **Google Cloud Agent Builder** used at runtime | ❌ **Not used at all.** No ADK / Agent Engine / Agentspace / Vertex AI Agent Builder anywhere. `CLAUDE.md` explicitly says *"No agent frameworks."* Orchestration is hand-rolled in `pipeline.py`. | 🔴 **Blocker** |
| 3 | §7.A | **Partner (Arize) MCP server** integrated at runtime | ⚠️ **Not at runtime.** Arize Phoenix is used for OTLP *tracing* (`integrations/phoenix.py`) and a Python eval client (`phoenix_client.py`). The Arize **MCP server** (`@arizeai/phoenix-mcp`) appears **only** in `mcp/phoenix-mcp.example.json` as a Claude Desktop config example. The app never calls it. | 🔴 **Blocker** |
| 4 | §7.B (AI limitation) | Gemini via **Google Cloud AI** ("Gemini models on Agent Platform") | ⚠️ Uses the **AI Studio Developer API** (`genai.Client(api_key=...)`), not Vertex AI on Google Cloud. Borderline; should route through Vertex AI. | 🟡 Risk |
| 5 | §7.B | No competing cloud/AI services | ✅ Cloud Run + Google deps only; no OpenAI/AWS/Azure in code. Phoenix evals use no non-Google LLM. | OK |
| 6 | §7.B | Runs on web | ✅ Next.js frontend on Cloud Run | OK |
| 7 | §7.B | **New project**, created in Contest Period (≥ May 5, 2026) | ⚠️ First SimAB commit `2026-05-21` ✅ — but the **git history contains a pre-window project** (2025-11-14, Firebase/Hunter.io). A judge inspecting history sees the repo predates the window. | 🟡 Risk |
| 8 | §7.B (Submit) | Repo **public** with OSI license visible in About | ❌ Repo is **private** today. License IS MIT (detectable once public). | 🔴 **Blocker** (1-click fix) |
| 9 | §7.B (Submit) | Hosted URL works for judges | ⚠️ Unverifiable from CI sandbox (network allowlist). **Must test in incognito.** | 🟡 Verify |
| 10 | §7.B (Submit) | Demo video < 3 min, public on YouTube/Vimeo, English | ❓ No link in repo — Devpost field. Confirm. | 🟡 Verify |
| 11 | §7.B (Submit) | Text description (features/tech/data/learnings) | ❓ Devpost field. README has raw material. | 🟡 Verify |
| 12 | §7.B (Team) | All team members on Devpost, ≤ 4 | ❓ Devpost field. Confirm. | 🟡 Verify |
| 13 | §4 | Eligibility — **Italy is INELIGIBLE / Contest void in Italy** | ⚠️ Repo/context suggests an Italy-based author (CET commit timezones `+0100/+0200`). **If the entrant resides in Italy, the entry is void.** | 🔴 **Check personally** |

### Bottom line
**Three hard blockers (Agent Builder, Arize MCP at runtime, private repo) plus an eligibility flag.** As submitted, the project would **fail Stage One** pass/fail screening (Rule §8), which explicitly checks that the Submission "reasonably applies both the required data provided by Partner and Google Cloud products."

> ⚠️ **Eligibility first (Rule §4):** the Contest is **void in Italy** and Italian residents are ineligible. If you reside in Italy, no amount of engineering makes the entry valid — resolve this before investing effort (e.g., eligible team representative).

---

## 2. What "really working well" requires

To move from "names the tech" to "genuinely built on it and demos well":

### Gap A — Build the agent on Google Cloud Agent Builder (the big one)
Recommended path: **Vertex AI Agent Builder via the Agent Development Kit (ADK)**, deployed to **Vertex AI Agent Engine**.

- Define a root ADK `Agent` (Gemini-backed) that orchestrates the pipeline. The cleanest mapping: expose each phase (Study Designer, Panel Recruiter, Cognitive Walker, Bias Auditor, Insight Analyst, Report Narrator) as ADK sub-agents or tools, preserving the existing stigmergy/SQLite state model underneath.
- Route Gemini through **Vertex AI** (`genai.Client(vertexai=True, project=..., location=...)`) so Gap D is closed simultaneously.
- Deploy to **Agent Engine**; have `main.py` / the A2A endpoint invoke the deployed agent.
- This also lets us drop the `CLAUDE.md` "no frameworks" stance and update architecture docs accordingly.

### Gap B — Integrate the Arize Phoenix MCP server at runtime
- Run `@arizeai/phoenix-mcp` against the Phoenix instance.
- Wire it as an **MCP toolset into the ADK agent** (ADK supports MCP toolsets natively — strong synergy with Gap A). Concretely: have the **FidelityAuditor** (or Panel Recruiter) call Phoenix MCP tools at runtime to query prior-run spans/datasets/experiments, instead of (or in addition to) the direct Python client. That makes the partner MCP server a live dependency in the request path.

### Gap C — Repo public + license visible
- Flip repo to **Public** (Settings → Danger Zone). MIT `LICENSE` already exists; confirm it renders in the About sidebar. **~5 minutes.**

### Gap D — Gemini on Vertex AI
- Folded into Gap A (switch client to `vertexai=True`). Keep the AI Studio key path as a local-dev fallback.

### Gap E — New-project history hygiene
- Either squash to a clean initial commit dated in-window, or add a `NOTICE`/README note explaining the SimAB project began 2026-05-21 and prior commits belonged to an unrelated project. Document the "new project" answer truthfully on Devpost.

### Supporting work
- Redeploy backend+frontend to Cloud Run wired to Agent Engine + Phoenix MCP.
- Update `README.md`, `CLAUDE.md`, `docs/architecture.md` (the "no frameworks" claim is now false).
- Re-shoot the < 3 min demo video showing: Agent Builder/Agent Engine running the agent, Gemini-on-Vertex spans in Phoenix, and the Phoenix MCP tool calls.
- Keep `pytest tests/` green (45 tests) + add tests for the ADK agent and MCP toolset.

---

## 3. Effort estimate (one experienced engineer)

| Gap | Work | Realistic | Min-viable |
|-----|------|-----------|------------|
| A | ADK agent + sub-agents/tools over existing pipeline; Vertex project/IAM; Agent Engine deploy + wiring | 4–7 d | 3 d |
| B | Phoenix MCP server + ADK MCP toolset in request path + tests | 2–3 d | 1.5 d |
| C | Repo public + license in About | ~0.1 d | 0.1 d |
| D | Gemini → Vertex AI client (folded into A) | 0.5–1 d | 0.5 d |
| E | History hygiene / new-project note | 0.25 d | 0.25 d |
| — | Cloud Run redeploy, docs rewrite, QA, demo video | 1.5–2 d | 1 d |
| **Total** | | **≈ 10–14 engineer-days** | **≈ 6 days** |

### ⏱️ Timeline reality check
Today is **June 9**; deadline **June 11, 2:00 PM PT** — roughly **2 days** left. Even the compressed ~6-day path **does not fit** for a single engineer. Honest options:

1. **Triage to "Stage-One survivable" only** (highest ROI in 2 days): flip repo public (C), Gemini→Vertex (D), and a **genuine but minimal** ADK agent (A-min) that wraps the pipeline as one tool on Agent Engine, plus a **single live Phoenix MCP tool call** (B-min). Skippable polish dropped. Tight but conceivably ~2 long days; quality will read as minimal.
2. **Parallelize across the (≤4-person) team** — split A / B / deploy+video across people.
3. **Accept the deadline can't be met well** and decide whether a rushed minimal entry is worth it, especially given the **Italy eligibility blocker** (§13 above) which may moot the whole effort.

**Recommendation:** resolve eligibility (Rule §4) first. If eligible, pursue Option 1 immediately and in parallel; treat Agent Builder (Gap A) as the critical path since it is the rule most likely to fail Stage One.

---

## 4. Immediate action checklist
- [ ] **Confirm eligibility** — entrant not resident in Italy (Contest void in Italy).
- [ ] Flip repo to **Public**; verify MIT license shows in About.
- [ ] Decide scope (Option 1 / 2 / 3 above).
- [ ] Implement ADK agent on Agent Engine (Gap A) + Gemini→Vertex (Gap D).
- [ ] Wire Phoenix MCP toolset into the agent at runtime (Gap B).
- [ ] Redeploy; verify hosted URL in a fresh incognito browser.
- [ ] Record < 3 min public demo video showing all three required techs live.
- [ ] Confirm Devpost: text description, video link, all team members, "new project" = correct.

---

## 5. Token estimate (AI coding agent)

These are **aggregate model tokens (input + output, summed across all turns)** — the figure that drives cost/context. In agentic coding, input dominates (~10–20× output) because files get re-read, test output streams back, and long sessions trigger context compaction.

**Important:** token spend is **not** proportional to lines of code. Reading the entire 4.5K-line backend once is only ~55K tokens; all new/edited code + doc rewrites is ~250–350K tokens of output. The bulk of any large figure comes from **iteration loops** — and specifically from cloud deploy/auth logs streaming back through context, which is a *risk tail*, not the baseline.

| Workstream | Realistic |
|---|---|
| A — ADK agent on Agent Engine | 350–700K |
| B — Phoenix MCP toolset at runtime | 150–300K |
| D — Gemini → Vertex client (overlaps A) | 50–120K |
| Tests (keep 45 green + new) | 100–250K |
| Deploy + QA (Cloud Run, incognito verify) | 100–300K |
| Docs rewrite (README/CLAUDE/architecture) | 100–200K |
| C — repo public, E — history hygiene | ~30K |

- **Min-viable (Stage-One-survivable): ~0.5–0.8M tokens**
- **Realistic (polished, fully compliant): ~1–2M tokens**
- **Pessimistic tail: ~3–4M tokens** — only if Vertex/Agent Engine/Cloud Run deploys fail repeatedly and stream large logs (first-time IAM/quota debugging is the usual culprit). Assumes GCP project, Vertex quota, and Agent Engine access are already provisioned.

**Cost lever:** ~90% of the spend is exploration + iteration + streamed logs, not code generation. Routing the high-iteration deploy/test grunt work to a cheaper model (Sonnet/Haiku) and reserving the top model for the agent design cuts cost substantially.
