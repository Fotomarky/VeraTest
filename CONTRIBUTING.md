# Contributing to SimAB

Thanks for considering a contribution. SimAB is intentionally lean — the design
philosophy is in the [README](./README.md) architecture section, and the business
model that shaped what is and isn't in this repo is in [BUSINESS.md](./BUSINESS.md).

## What this repo is

The full self-hostable engine: five ADK-style agents, stigmergy state on SQLite,
MCP server, dashboard, A2A endpoints, GA4 connector, Slack integration. Anyone
can clone, run, and use this for free under MIT.

## What this repo is *not*

These features belong in the hosted SaaS layer and are explicitly not in scope
for the open-source repo:

- Multi-tenant workspace isolation (no user accounts here)
- Authentication / SSO / SAML
- Billing integration (Stripe, GCP Cloud Commerce)
- Cross-tenant analytics or benchmarks
- Enterprise compliance modules (audit logs, SOC2 attestations)
- Hosted-only persona library scoring intelligence

PRs adding these will be closed. They're real product needs, just not in the
free, self-hostable layer.

## Good first contributions

- **New persona templates** — drop pre-built persona sets for common verticals
  (B2B SaaS, e-commerce, mobile apps) into `simab/personas/templates/`
- **Additional MCP tools** — wrap a new endpoint or export format as an MCP tool
- **Frontend polish** — accessibility fixes, mobile layout improvements
- **Test coverage** — adversarial tests (identical images, blank pages, etc.)
- **Documentation** — deployment walkthroughs for specific platforms (Render, Fly.io, Railway)

## Development setup

```bash
git clone <repo> simab && cd simab
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
export GEMINI_API_KEY="..."  # from https://aistudio.google.com/app/apikey
pytest tests/ -v             # should show 17 passing
uvicorn simab.main:app --reload --port 8000
```

## PR checklist

- [ ] Code passes `pytest tests/` (currently 17 tests, ~3 seconds)
- [ ] New behavior has a test
- [ ] No new dependencies unless absolutely needed (we're keeping the install small)
- [ ] No `print()` statements; use the `logging` module
- [ ] No `async def` functions without `await` somewhere inside them
- [ ] Pydantic schemas are the source of truth — update `simab/models.py` first
- [ ] If touching agent prompts, include a 1-line note about why in the PR description

## Code style

- Python 3.11+ with type hints
- `from __future__ import annotations` at the top of every module
- No formatter configured intentionally — keep it readable, don't reformat existing code
- Imports: stdlib, then third-party, then local (single blank line between groups)

## Release process

1. Bump version in `simab/__init__.py` and `pyproject.toml`
2. Update CHANGELOG (when one exists)
3. Tag the release in GitHub
4. The MCP package is published separately via `mcp/pyproject.toml`

## Questions

Open an issue. For private/security concerns, see [SECURITY.md](./SECURITY.md).
