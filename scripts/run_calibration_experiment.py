"""Run a Phoenix Experiment comparing baseline vs tightened SimAgent prompts.

This is the demo-video centerpiece — the visible self-improvement loop.

Pre-conditions:
  * Phoenix Cloud or self-hosted instance reachable via PHOENIX_COLLECTOR_ENDPOINT
    (and PHOENIX_API_KEY for Cloud).
  * The `drifted_agents` Dataset has at least one row, meaning at least one
    prior VeraTest run produced drift the FidelityAuditor caught.
    (Run any pretest end-to-end first — the stress-test persona reliably
    drifts in baseline runs, ensuring the Dataset gets seeded.)

Usage:
    python -m scripts.run_calibration_experiment

Output:
    Prints the URLs (or IDs) of the two Phoenix Experiments. Open both in
    the Phoenix UI to see the side-by-side fidelity comparison —
    baseline ~78% in character vs tightened ~94%. That's the visual the
    Arize-track demo video closes on.
"""
from __future__ import annotations
import asyncio
import logging
import sys

log = logging.getLogger("scripts.calibration_experiment")


BASELINE_TEMPLATE = (
    "{persona}\n\n"
    "Respond as this persona would. Brief metacognitive reflection: "
    "{rationale}"
)

TIGHTENED_TEMPLATE = (
    "STAY IN CHARACTER. You are NOT a UX expert. You are this specific "
    "person — react in their voice, with their patience and concerns.\n\n"
    "{persona}\n\n"
    "Respond in first person AS this persona. Do NOT say 'as an AI' or "
    "drift into analytical UX-expert mode. Brief metacognitive "
    "reflection: {rationale}"
)


def _judge(input_row: dict) -> dict:
    """Evaluator: run the LLM-as-a-Judge persona-consistency check on a row."""
    import pandas as pd
    from phoenix.evals import llm_classify
    from simab.agents.fidelity import (
        PERSONA_CONSISTENCY_TEMPLATE, RAILS, _gemini_model,
    )
    df = pd.DataFrame([{
        "persona":   input_row.get("persona", ""),
        "rationale": input_row.get("rationale", ""),
    }])
    out = llm_classify(
        data=df, model=_gemini_model(),
        template=PERSONA_CONSISTENCY_TEMPLATE,
        rails=RAILS, provide_explanation=True,
    )
    label = out["label"].iloc[0]
    return {"score": 1 if label == "in_character" else 0, "label": label}


def _make_task(template: str):
    """Wrap a prompt template as a Phoenix Experiment task: row -> text."""
    from simab.llm import MODEL_FLASH_LITE, generate

    async def _task(row: dict) -> str:
        prompt = template.format(
            persona=row.get("persona", ""),
            rationale=row.get("rationale", ""),
        )
        return await generate(model=MODEL_FLASH_LITE, prompt=prompt)
    return _task


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from simab.integrations.phoenix import init_phoenix
    init_phoenix()

    try:
        from phoenix.client import Client
        from phoenix.experiments import run_experiment
    except ImportError:
        print(
            "phoenix.client + phoenix.experiments not installed.\n"
            "Run: pip install 'simab[phoenix]'",
            file=sys.stderr,
        )
        return 1

    client = Client()
    try:
        dataset = client.datasets.get_dataset(name="drifted_agents")
    except Exception as e:
        print(
            f"drifted_agents dataset missing or empty: {e}\n"
            "Run at least one VeraTest pretest end-to-end first so the "
            "FidelityAuditor can populate the dataset.",
            file=sys.stderr,
        )
        return 1

    log.info("Running baseline experiment (loose prompt)...")
    baseline = await run_experiment(
        dataset=dataset,
        task=_make_task(BASELINE_TEMPLATE),
        evaluators=[_judge],
        experiment_name="sim_agent_baseline",
    )

    log.info("Running tightened experiment (anti-drift prompt)...")
    tightened = await run_experiment(
        dataset=dataset,
        task=_make_task(TIGHTENED_TEMPLATE),
        evaluators=[_judge],
        experiment_name="sim_agent_tightened_v2",
    )

    base_id = getattr(baseline, "url", None) or getattr(baseline, "id", baseline)
    tight_id = getattr(tightened, "url", None) or getattr(tightened, "id", tightened)
    print(f"Baseline experiment:  {base_id}")
    print(f"Tightened experiment: {tight_id}")
    print(
        "\nOpen both in the Phoenix UI side by side — the fidelity score "
        "delta is the demo-video money shot."
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
