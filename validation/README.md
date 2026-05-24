# SimAB Validation Harness

Measures pipeline accuracy against real A/B tests with documented outcomes.

## Quick start

```bash
# No API needed — just verifies the harness runs
python validation/run.py --dataset validation/dataset.csv --baselines cheap

# Full run including SimAB (requires GEMINI_API_KEY and backend running)
export GEMINI_API_KEY="..."
python validation/run.py --dataset validation/dataset.csv --baselines all
```

## Dataset

10 cases from [abtestcases.com](https://www.abtestcases.com) with publicly documented winners.
Images are stored locally in `validation/images/`.

## Known limitation: publication bias

Published A/B test case databases are heavily skewed toward B-winning results — websites
only write up tests where the challenger variant improved conversion. Our 10-case dataset
reflects this: all 10 have B as the winner, so the trivial "always_b" baseline scores 100%.

**This is a dataset limitation, not a SimAB limitation.**

The meaningful comparison is SimAB vs one-shot Gemini — both face the same dataset,
and SimAB's multi-agent pipeline should produce higher accuracy AND richer qualitative
insight (friction themes, Fogg scores, trust signals) that a single-call baseline cannot.

For a truly balanced benchmark, you would need access to a private A/B testing platform
with a mix of winning and losing challengers. ablibrary.de is one public option worth
monitoring, but it was inaccessible at time of writing.
