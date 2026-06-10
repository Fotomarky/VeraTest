# VeraTest — 3-Minute Demo Video Script

> Google Cloud Rapid Agent Hackathon — Arize Track.
> Target length: 2:50–3:00. One continuous narrative, no section cards.
> Record at 1920×1080. Screen + voiceover; no talking head needed.

**Pre-flight checklist (do BEFORE recording):**
- [ ] Phoenix running and receiving spans (`PHOENIX_COLLECTOR_ENDPOINT` set); open the project view in a pinned tab
- [ ] Live Cloud Run frontend open in a pinned tab (not localhost — judges check the URL bar)
- [ ] One **pre-completed** run open in a third tab (insurance against 503s mid-demo)
- [ ] Two real screenshots ready on the desktop (use a recognizable-style landing page, not lorem ipsum)
- [ ] Mic permission already granted to the browser (the voice demo must not show a permission prompt)
- [ ] `validation/report_*.md` with the final table open in an editor tab

---

## 0:00–0:20 — The hook (problem)

**Screen:** A Figma-style mockup of two landing page variants side by side, then a Slack poll screenshot ("Which one do you like? 👍A / 👍B").

**VO:**
> "Every product team argues about design. And most resolve it the same way — gut feeling, a Slack poll, or shipping the founder's favorite. A real A/B test gives you the answer, but it needs live traffic and four to six weeks. VeraTest gives you a directional answer in ninety seconds — before you've built anything."

---

## 0:20–0:50 — Describe mode (the ADK Concierge, voice input)

**Screen:** Live Cloud Run app → New pretest. Drag a screenshot in. Click the mic. **Speak, don't type:**
> "We sell a project management tool to startup founders. I want more of them to start a free trial from this page."

Hit Run. The Packman agent theater starts walking.

**VO (over the interaction):**
> "No forms, no configuration. I upload my design and just *say* what I'm trying to do. A Google Agent Builder agent — built on the ADK — parses my description, infers the conversion goal and the audience, and launches the study. This is the front door to a twenty-agent panel."

**Caption overlay:** `Google Cloud Agent Builder (ADK) · Gemini on Vertex AI`

---

## 0:50–1:30 — The multi-agent panel (the core)

**Screen:** Stay on the in-flight run; status phases tick by (designing → recruiting → simulating ×20 → auditing → synthesizing). Cut briefly to the architecture diagram from the README.

**VO:**
> "Under the hood, six specialist agents mirror a real usability study. A Study Designer reads the screenshots and writes the brief. A Panel Recruiter assembles personas — a skeptical CFO, a mobile-first founder, a researcher who reads every footnote. Then twenty Cognitive Walkers each walk the page *in persona*, in parallel, scoring six resonance dimensions. A Bias Auditor checks the panel for groupthink before an Insight Analyst is allowed to synthesize a verdict."

> "Why twenty? Nielsen showed five independent evaluators find eighty percent of usability issues. Condorcet's jury theorem says independent judges converge on the right answer as the panel grows. One LLM call gives you one opinion. Twenty constrained personas give you a study."

**Caption overlay:** `6 phases · 20 parallel persona agents · no orchestration framework — coordination via shared state`

---

## 1:30–2:00 — Arize Phoenix (track requirement — make it unmissable)

**Screen:** Switch to the Phoenix tab. Show the trace waterfall filling in live — one span per Gemini call. Click into a single `sim_agent.N` span and show the persona prompt + scored JSON response. Then show the agent's Phoenix MCP toolset answering "what was my slowest span?" in the Concierge chat.

**VO:**
> "Every one of those calls — about twenty-four per run — is traced live into Arize Phoenix. Here's one persona's span: the prompt it walked in with, the scores it came back with. And the Concierge agent mounts the Arize Phoenix MCP server as a live toolset, so you can interrogate your own traces in plain English. Observability isn't bolted on; the agent can read its own telemetry."

**Caption overlay:** `Arize Phoenix · @arizeai/phoenix-mcp mounted as ADK toolset · 1 span per Gemini call`

---

## 2:00–2:30 — The result (what a PM actually gets)

**Screen:** The completed run (switch to the pre-completed tab if needed). Scroll deliberately: verdict rail with validity + persona-fidelity badges → persona circles, click one open → "What to do next" card → friction matrix → user-story cards, click **copy**. End on the one-click markdown export.

**VO:**
> "The output isn't a score — it's a decision. A verdict with a validity check, the personas that drove it, the top friction ranked by severity, and ready-made user stories you can paste straight into Linear. Total cost of this run: about one cent of Gemini free tier. Total time: under two minutes."

---

## 2:30–2:55 — Validation (the credibility close)

**Screen:** The validation report table in the editor. Highlight the `oneshot_gemini` row, then the `simab` decisive-accuracy column.

**VO:**
> "And we don't ask you to trust it. VeraTest ships a falsifiable benchmark: twenty real A/B tests with documented winners, mirrored so position bias can't help, scored against four baselines — including the one that matters: the same Gemini model with a single prompt. When the panel commits to a verdict, it beats the one-shot baseline. And when it doesn't have enough evidence, it abstains instead of guessing — a quorum gate refuses to synthesize a verdict from a degraded panel. For a decision tool, refusing to bluff *is* a feature."

---

## 2:55–3:00 — Close

**Screen:** README hero + live URL + MIT license badge.

**VO:**
> "VeraTest. Twenty AI personas, one honest verdict, ninety seconds. Open source, running live on Google Cloud — link below."

---

## Compliance shot-map (for the judges' rubric)

| Requirement | Where it's visibly on screen |
|---|---|
| Gemini at runtime | 0:50 phase ticker + 1:30 Phoenix spans of live Gemini calls |
| Agent Builder (ADK) | 0:20 describe-mode launch via the Concierge `LlmAgent` |
| Arize partner MCP at runtime | 1:30 Phoenix MCP toolset answering inside the agent chat |
| Multi-agent system | 0:50 six phases + 20 parallel walkers |
| Live demo URL | URL bar visible from 0:20 onward (Cloud Run domain) |
| Open source / MIT | 2:55 closing frame |
