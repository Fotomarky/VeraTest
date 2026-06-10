"""Validation harness — measures SimAB accuracy against known A/B test winners.

Compares SimAB's full pipeline against baselines:
  cheap   → random, always_a, always_b
  all     → cheap + heuristic + oneshot_gemini + simab

Usage:
  python validation/run.py --dataset validation/dataset.csv --baselines cheap
  python validation/run.py --dataset validation/dataset.csv --baselines all
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import json
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    url: str
    goal: str
    variant_a_path: str
    variant_b_path: str
    true_winner: str  # "A" or "B"
    result_summary: str = ""


def load_dataset(csv_path: str) -> list[TestCase]:
    root = Path(__file__).parent.parent
    cases = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            a = row["variant_a_img"].strip()
            b = row["variant_b_img"].strip()
            # Resolve relative paths from repo root
            if not Path(a).is_absolute():
                a = str(root / a)
            if not Path(b).is_absolute():
                b = str(root / b)
            cases.append(TestCase(
                url=row["url"].strip(),
                goal=row["goal"].strip(),
                variant_a_path=a,
                variant_b_path=b,
                true_winner=row["true_winner"].strip().upper(),
                result_summary=row.get("result_summary", "").strip(),
            ))
    return cases


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def baseline_random(case: TestCase) -> str:
    return random.choice(["A", "B"])


def baseline_always_a(case: TestCase) -> str:
    return "A"


def baseline_always_b(case: TestCase) -> str:
    return "B"


def baseline_heuristic(case: TestCase) -> str:
    """Simple heuristic: variant B is usually the challenger — pick B."""
    return "B"


async def baseline_oneshot_gemini(case: TestCase) -> str:
    """Single Gemini call — no multi-agent pipeline, just one prompt + images."""
    from simab.llm import MODEL_FLASH, generate
    a_bytes = Path(case.variant_a_path).read_bytes()
    b_bytes = Path(case.variant_b_path).read_bytes()
    prompt = (
        f"You are a UX expert. Compare these two landing page variants.\n"
        f"Conversion goal: {case.goal}\n"
        f"Variant A is shown first, Variant B second.\n"
        f"Which variant would convert better? Reply with ONLY 'A' or 'B'."
    )
    result = await generate(
        model=MODEL_FLASH,
        prompt=prompt,
        images=[a_bytes, b_bytes],
        temperature=0.1,
    )
    text = str(result).strip().upper()
    return "A" if text.startswith("A") else "B"


async def baseline_simab(case: TestCase) -> str:
    """Full SimAB multi-agent pipeline."""
    import uuid
    from simab import state
    from simab.pipeline import run_pipeline

    # Need a running DB
    await state.get_db()

    run_id = await state.create_run(
        goal=case.goal,
        audience_raw="",
        persona_source="auto",
        variant_a_path=case.variant_a_path,
        variant_b_path=case.variant_b_path,
    )
    await run_pipeline(run_id)

    run = await state.get_run(run_id)
    if run is None or run.synthesis is None:
        return "?"
    winner = run.synthesis.directional_winner  # "variant_a" | "variant_b" | "tie"
    if winner == "variant_a":
        return "A"
    elif winner == "variant_b":
        return "B"
    return "?"  # tie = abstain


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class Result:
    method: str
    predictions: list[str] = field(default_factory=list)
    correct: int = 0
    total: int = 0
    latency_s: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


async def run_baseline(
    name: str,
    fn,
    cases: list[TestCase],
    is_async: bool = False,
) -> Result:
    result = Result(method=name)
    t0 = time.monotonic()
    for case in cases:
        try:
            pred = await fn(case) if is_async else fn(case)
        except Exception as e:
            print(f"  [{name}] ERROR on {Path(case.variant_a_path).stem}: {e}")
            pred = "?"
        result.predictions.append(pred)
        result.total += 1
        if pred == case.true_winner:
            result.correct += 1
        status = "✓" if pred == case.true_winner else "✗"
        print(f"  [{name}] {status} predicted={pred} actual={case.true_winner}  ({Path(case.variant_a_path).stem})")
    result.latency_s = time.monotonic() - t0
    return result


async def main(dataset_path: str, baselines_mode: str) -> None:
    # Trace every Gemini call (one-shot baseline + full SimAB pipeline) into
    # Phoenix. No-op unless PHOENIX_COLLECTOR_ENDPOINT is set — source the
    # Cloud Run config first: `source validation/phoenix_env.sh`.
    from simab.config import CONFIG
    from simab.integrations.phoenix import init_phoenix
    if init_phoenix():
        print(f"Phoenix tracing ON → project '{CONFIG.phoenix_project}' "
              f"@ {CONFIG.phoenix_endpoint}\n")

    cases = load_dataset(dataset_path)
    print(f"\nLoaded {len(cases)} test cases from {dataset_path}\n")

    # Validate images exist
    missing = [c for c in cases if not Path(c.variant_a_path).exists() or not Path(c.variant_b_path).exists()]
    if missing:
        print("ERROR: Missing image files:")
        for c in missing:
            print(f"  A: {c.variant_a_path} — exists: {Path(c.variant_a_path).exists()}")
            print(f"  B: {c.variant_b_path} — exists: {Path(c.variant_b_path).exists()}")
        sys.exit(1)

    results: list[Result] = []

    # Cheap baselines (no API calls)
    print("── Random baseline ──────────────────")
    results.append(await run_baseline("random", baseline_random, cases))

    print("\n── Always-A baseline ────────────────")
    results.append(await run_baseline("always_a", baseline_always_a, cases))

    print("\n── Always-B baseline ────────────────")
    results.append(await run_baseline("always_b", baseline_always_b, cases))

    if baselines_mode == "all":
        print("\n── Heuristic baseline ───────────────")
        results.append(await run_baseline("heuristic", baseline_heuristic, cases))

        print("\n── One-shot Gemini ──────────────────")
        results.append(await run_baseline("oneshot_gemini", baseline_oneshot_gemini, cases, is_async=True))

        print("\n── SimAB full pipeline ──────────────")
        results.append(await run_baseline("simab", baseline_simab, cases, is_async=True))

    # Print summary table
    print("\n" + "=" * 60)
    print("ACCURACY SUMMARY")
    print("=" * 60)
    print(f"{'Method':<20} {'Accuracy':>10} {'Correct':>8} {'Total':>7} {'Time':>8}")
    print("-" * 60)
    for r in results:
        print(f"{r.method:<20} {r.accuracy:>9.1%} {r.correct:>8} {r.total:>7} {r.latency_s:>7.1f}s")
    print("=" * 60)

    # Write markdown report
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(__file__).parent / f"report_{ts}.md"
    with open(report_path, "w") as f:
        f.write(f"# SimAB Validation Report\n\n")
        f.write(f"**Dataset:** {dataset_path}  \n")
        f.write(f"**Cases:** {len(cases)}  \n")
        f.write(f"**Run at:** {datetime.now().isoformat()}  \n\n")
        f.write("## Accuracy\n\n")
        f.write("| Method | Accuracy | Correct | Total |\n")
        f.write("|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r.method} | {r.accuracy:.1%} | {r.correct} | {r.total} |\n")
        f.write("\n## Per-case results\n\n")
        f.write(f"| Test | True winner | " + " | ".join(r.method for r in results) + " |\n")
        f.write("|---|---|" + "|".join("---" for _ in results) + "|\n")
        for i, case in enumerate(cases):
            preds = [("✓" if r.predictions[i] == case.true_winner else "✗") + r.predictions[i]
                     for r in results]
            name = Path(case.variant_a_path).stem.replace("a", "", 1)
            f.write(f"| {name} | {case.true_winner} | " + " | ".join(preds) + " |\n")
        f.write(f"\n## Dataset note\n\n")
        f.write("All test cases sourced from [abtestcases.com](https://www.abtestcases.com) "
                "with publicly documented winners. Note: published A/B cases skew toward "
                "variant B winning (publication bias — positive results get written up more often).\n")

    print(f"\nReport written to: {report_path}\n")

    # Short-lived process: force-flush batched spans before we exit.
    from simab.integrations.phoenix import flush_phoenix
    flush_phoenix()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SimAB validation harness")
    parser.add_argument("--dataset", required=True, help="Path to dataset CSV")
    parser.add_argument(
        "--baselines",
        choices=["cheap", "all"],
        default="cheap",
        help="cheap = random/always-A/always-B only; all = includes oneshot Gemini + SimAB",
    )
    args = parser.parse_args()
    asyncio.run(main(args.dataset, args.baselines))
