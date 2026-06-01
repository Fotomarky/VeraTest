"""ScenarioBuilder — turn brief personas into N concrete scenarios.

Given the brief's personas + their traffic weights, allocate the N simulation
agents (default 20) proportionally to weight. If a persona is 60% of traffic,
12 of 20 agents simulate that persona. Each agent gets a slightly varied
context so we don't get identical responses.
"""
from __future__ import annotations
import logging

from .. import state
from ..config import CONFIG
from ..integrations.phoenix_client import (
    audience_signature as _audience_signature,
    get_persona_drift_history,
)
from ..llm import MODEL_FLASH, generate
from ..models import ScenarioCard

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Calibration layer — anti-drift constraint + stress-test persona
# ---------------------------------------------------------------------------

ANTI_DRIFT_CONSTRAINT = (
    "STAY IN CHARACTER. Prior runs show this persona archetype drifts toward "
    "a 'helpful UX evaluator' voice {drift_pct}% of the time. You are NOT a "
    "UX expert. You are this specific person: react in their voice, with "
    "their patience and concerns, NOT a generic professional analysis."
)


def _inject_drift_constraints(
    cards: list[ScenarioCard],
    history: dict[str, float],
    threshold: float,
) -> list[ScenarioCard]:
    """For each card whose archetype (segment) has a historical drift rate
    above `threshold`, prepend an anti-drift constraint to its constraints
    list. Returns a new list — does not mutate inputs.

    This is the cross-run learning loop: the FidelityAuditor records drift
    in Phoenix; the next run's Panel Recruiter reads it back and tightens
    the prompt for archetypes that have a track record of slipping.
    """
    out: list[ScenarioCard] = []
    for card in cards:
        drift = history.get(card.segment, 0.0)
        if drift > threshold:
            extra = ANTI_DRIFT_CONSTRAINT.format(drift_pct=int(drift * 100))
            out.append(card.model_copy(update={
                "constraints": [extra, *card.constraints],
            }))
        else:
            out.append(card)
    return out


# Visibly labelled in the carousel — the leading "stress_test_" is the marker
# the frontend uses (see PersonaCard) to badge this persona as a calibration
# anchor rather than an audience segment.
STRESS_TEST_PERSONA = ScenarioCard(
    id="sc_stress",
    segment="stress_test_conflicted_senior",
    intent="evaluate",
    decision_style="cautious",
    device="desktop",
    traffic_source="referral",
    context=(
        "A 65-year-old who is technologically cautious but is also a former "
        "software developer. Skeptical of modern marketing aesthetics but "
        "understands technical depth — internal conflict between caution "
        "and expertise."
    ),
    constraints=[
        "Patience for marketing fluff is near zero.",
        "Demand technical specifics before trusting a claim.",
    ],
    time_pressure="medium",
    price_sensitivity="medium",
    patience_threshold="low",
    communication_style="precise, mildly skeptical, occasionally dry",
    visual_style_preference="minimal, dense, technical",
)


def _inject_stress_test_persona(cards: list[ScenarioCard]) -> list[ScenarioCard]:
    """Always include one deliberately-difficult persona so the
    FidelityAuditor has a reliable signal to surface — standard
    adversarial-evaluation practice. Hiding it would be a demo-time hack;
    showing it makes the calibration story honest.

    The stress-test persona gets 1/(N+1) traffic weight; existing cards are
    rescaled to N/(N+1) total so weights still sum to 1.0.
    """
    if not cards:
        return [STRESS_TEST_PERSONA.model_copy(update={"traffic_weight": 1.0})]
    n = len(cards)
    rescale = n / (n + 1)
    weight = 1 / (n + 1)
    rescaled = [
        c.model_copy(update={"traffic_weight": c.traffic_weight * rescale})
        for c in cards
    ]
    rescaled.append(
        STRESS_TEST_PERSONA.model_copy(update={"traffic_weight": weight})
    )
    return rescaled


VARIATION_PROMPT = """\
Given this base persona, produce {count} micro-variations of it.
Each should keep the same segment, intent, decision_style, device,
traffic_source, time_pressure, and price_sensitivity, but vary the
`context` field with a different realistic scenario (different time of
day, different mood, different specific constraint surfacing).

BASE PERSONA:
{persona_json}

Respond with ONLY a JSON array of {count} objects, each with the same
fields as the base persona but a unique `context` value.
"""


def _allocate(weights: list[float], total: int) -> list[int]:
    """Largest-remainder method for proportional allocation."""
    if not weights or sum(weights) == 0:
        # Equal split
        base = total // len(weights)
        rem = total - base * len(weights)
        result = [base] * len(weights)
        for i in range(rem):
            result[i] += 1
        return result

    s = sum(weights)
    quotas = [w / s * total for w in weights]
    floors = [int(q) for q in quotas]
    remainder = total - sum(floors)
    # Distribute remainder by largest fractional parts
    fracs = sorted(
        range(len(weights)), key=lambda i: quotas[i] - floors[i], reverse=True
    )
    for i in fracs[:remainder]:
        floors[i] += 1
    # Each persona gets at least 1 agent if we have room
    for i in range(len(floors)):
        if floors[i] == 0 and any(f > 1 for f in floors):
            j = max(range(len(floors)), key=lambda k: floors[k])
            floors[j] -= 1
            floors[i] = 1
    return floors


async def run(run_id: str, num_agents: int | None = None) -> list[ScenarioCard]:
    """Build the final scenario list with one entry per simulation agent."""
    num_agents = num_agents or CONFIG.num_agents
    run = await state.get_run(run_id)
    if run is None or run.brief is None:
        raise ValueError(f"Run {run_id} has no brief")

    await state.set_status(run_id, "building_scenarios")

    personas = run.brief.inferred_personas
    if not personas:
        raise ValueError("Brief has no personas")

    weights = [p.traffic_weight if p.traffic_weight > 0 else 1.0 / len(personas)
               for p in personas]
    allocation_counts = _allocate(weights, num_agents)

    final_scenarios: list[ScenarioCard] = []
    allocations: list[dict] = []
    agent_idx = 0

    for persona, count in zip(personas, allocation_counts):
        allocations.append({
            "persona_id": persona.id,
            "segment": persona.segment,
            "agent_count": count,
            "traffic_weight": round(persona.traffic_weight, 3),
        })
        if count == 0:
            continue

        if count == 1:
            # Just clone the base persona once
            sc = persona.model_copy()
            sc.id = f"{persona.id}_a{agent_idx:02d}"
            final_scenarios.append(sc)
            agent_idx += 1
            continue

        # Ask LLM to vary the context for the rest
        raw = await generate(
            model=MODEL_FLASH,
            prompt=VARIATION_PROMPT.format(
                count=count, persona_json=persona.model_dump_json(indent=2)
            ),
            response_schema={},
            temperature=0.7,  # higher temp for diversity
        )

        # Be lenient: raw may be a list or a dict with a list inside
        variations = raw if isinstance(raw, list) else (
            raw.get("variations") or raw.get("personas") or raw.get("items") or []
        )
        if not isinstance(variations, list) or len(variations) == 0:
            # Fallback: replicate base persona
            variations = [persona.model_dump() for _ in range(count)]

        for j, var in enumerate(variations[:count]):
            try:
                merged = {**persona.model_dump(), **var}
                merged["id"] = f"{persona.id}_a{agent_idx:02d}"
                final_scenarios.append(ScenarioCard.model_validate(merged))
            except Exception as e:
                log.warning(f"Variation parse failed: {e}; using base persona")
                sc = persona.model_copy()
                sc.id = f"{persona.id}_a{agent_idx:02d}"
                final_scenarios.append(sc)
            agent_idx += 1

    # Pad if we didn't hit num_agents (e.g. LLM under-delivered)
    while len(final_scenarios) < num_agents:
        sc = personas[0].model_copy()
        sc.id = f"{personas[0].id}_a{len(final_scenarios):02d}"
        final_scenarios.append(sc)

    final_scenarios = final_scenarios[:num_agents]

    # ── Calibration layer (Arize track) ──────────────────────────────────
    # Read cross-run drift history and tighten constraints on archetypes
    # that have a track record of slipping out of character.
    sig = _audience_signature(run.audience_raw or run.goal)
    history = get_persona_drift_history(audience_signature=sig)
    if history:
        log.info(
            f"[{run_id}] drift history: "
            + ", ".join(f"{a}={r:.0%}" for a, r in history.items())
        )
    final_scenarios = _inject_drift_constraints(
        final_scenarios, history, threshold=CONFIG.fidelity_drift_threshold,
    )
    # Always include one visibly-labelled stress-test persona so the
    # FidelityAuditor has a reliable failure signal to operate on.
    final_scenarios = _inject_stress_test_persona(final_scenarios)

    await state.write_scenarios(run_id, final_scenarios, allocations)
    log.info(f"[{run_id}] scenario_builder: {len(final_scenarios)} agents across "
             f"{len([a for a in allocations if a['agent_count']>0])} personas")
    return final_scenarios
