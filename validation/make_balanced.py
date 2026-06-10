"""Build a position-counterbalanced dataset from the base real cases.

The base dataset (dataset.csv) is sourced from abtestcases.com, where every
documented winner happens to be variant B (publication bias — sites only write
up tests where the challenger won). That makes the trivial "always_b" baseline
score 100% and renders the benchmark uninformative.

Fix: present each real pair in BOTH orderings. Swapping the variant column order
flips the documented winner label (B->A), so 10 all-B pairs become 20 trials with
exactly 10 A-winners and 10 B-winners. No winners are fabricated — every label is
the same documented outcome, just with the columns counterbalanced. This also
turns the benchmark into a position-invariance test: a model that truly reads the
design (rather than favouring slot A or slot B) should score identically on a pair
and its mirror.

Usage:
  python validation/make_balanced.py
  # writes validation/dataset_balanced.csv (20 rows)
"""
from __future__ import annotations
import csv
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "dataset.csv"
OUT = HERE / "dataset_balanced.csv"

FLIP = {"A": "B", "B": "A"}


def main() -> None:
    rows = list(csv.DictReader(SRC.open(newline="")))
    out_rows = []
    for r in rows:
        # Original ordering (documented winner as-is).
        out_rows.append({
            "url": r["url"],
            "goal": r["goal"],
            "variant_a_img": r["variant_a_img"],
            "variant_b_img": r["variant_b_img"],
            "true_winner": r["true_winner"].strip().upper(),
            "result_summary": r["result_summary"],
        })
        # Mirror ordering (variants swapped -> winner label flips).
        out_rows.append({
            "url": r["url"],
            "goal": r["goal"],
            "variant_a_img": r["variant_b_img"],
            "variant_b_img": r["variant_a_img"],
            "true_winner": FLIP[r["true_winner"].strip().upper()],
            "result_summary": r["result_summary"] + " [variant order mirrored]",
        })

    fields = ["url", "goal", "variant_a_img", "variant_b_img", "true_winner", "result_summary"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    a = sum(1 for r in out_rows if r["true_winner"] == "A")
    b = sum(1 for r in out_rows if r["true_winner"] == "B")
    print(f"Wrote {OUT} — {len(out_rows)} trials ({a} A-winners, {b} B-winners)")


if __name__ == "__main__":
    main()
