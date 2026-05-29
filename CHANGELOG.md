# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-05-29
### Added
- Rate-limiting middleware (`simab/ratelimit.py`) for the live demo: global daily run cap, per-IP hourly cap, pending-queue depth limit, upload-size limit, and optional access code. Configured via env vars (`SIMAB_DAILY_RUN_CAP`, `SIMAB_PER_IP_HOUR_CAP`, `SIMAB_MAX_PENDING`, `SIMAB_MAX_UPLOAD_MB`, `SIMAB_ACCESS_CODE`).
- Single-screen evaluation mode: `variant_b` is now optional. Upload one design to get resonance scoring, friction themes, and recommendations without an A/B comparison.
- Pixelated walking agent characters in the Packman loading theater (replaces Pac-Man circles). Each agent's jacket color matches its persona segment color.
- `PersonaCarousel` component — prev/next navigation through all persona diagnostics.
- `SprintPriorities` now shows agent count and segment count in the header instead of an alarming orange confound block.
- `UserStoryScaffold` — generates "As a … I need … so that I can …" cards from high/medium friction themes, with copy-to-clipboard.
- `TestNextHypothesis` — blue card surfacing the synthesis recommendation with an ability score target.
- Resonance reframe: 6-dimension scoring (motivation, identity, situation, beliefs, ability, trigger) replaces the 2-dimension Fogg model.
- CSS hover tooltips on all resonance dimension labels (replaces broken `title` attributes on Safari).
- Form validation: Variant A and goal fields show red highlight when submitting with empty fields.

### Changed
- `BlockersMatrix` now unified into a single table showing both blockers and wins, with Fogg badges (Motiv↑↓, Ability↑↓) and recommended-fix hints.
- Results page restructured as "PM Command Center" with `CommandRail` sticky header.
- Animation restart bug fixed: agents no longer reset position on each SSE update.
- User story grammar fixed: "so that I can {goal}".

## [0.2.0] — (earlier)
### Added
- Bias auditor agent — checks cohort balance, score inflation, rationale coherence.
- Structured audience preset chip selector on the /new form.
- Arize Phoenix OTLP observability integration.
- A2A (Google agent-to-agent) protocol endpoint.
- Markdown and HTML share page exports.

## [0.1.0] — initial
### Added
- 5-agent pipeline: BriefNormalizer → ScenarioBuilder → 20×Simulator → BiasAuditor → Synthesizer.
- SQLite stigmergy state layer (pheromone trail pattern).
- Next.js 14 frontend with SSE live progress.
- MCP server with 4 tools.