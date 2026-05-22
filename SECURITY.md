# Security Policy

## Supported versions

SimAB is currently at v0.1.0. Until v1.0, only the `main` branch is supported.
Older versions will not receive security patches.

## Reporting a vulnerability

**Do not open public issues for security problems.**

Email security concerns privately to the maintainer (replace with your address
before publishing the repo). We aim to respond within 72 hours and to publish a
fix within 30 days of confirming the issue.

## What's in scope

- The Python backend (`simab/`)
- The MCP server (`mcp/`)
- The Next.js frontend (`frontend/`)
- Default configuration values

## What's out of scope

- Third-party services (Gemini API, Arize Phoenix, MongoDB, Google Analytics)
- User-provided LLM prompts or persona data (treated as untrusted by design)
- Self-hosted deployments where the operator has modified the code

## Known threat model

SimAB is intentionally **single-tenant** as open source. The trust boundary is
the operator's environment. Specifically:

- The SQLite database has no row-level access control
- API endpoints have no built-in authentication
- File uploads are stored in a single shared directory
- No rate limiting per "user" (only global rate limits on the LLM API)

These are not bugs — they're the design line between the free self-hostable
version and the hosted SaaS. Operators who need multi-tenant isolation should
either deploy SimAB per-team or use the hosted offering at app.simab.io.

## API key handling

`GEMINI_API_KEY` and `SIMAB_SLACK_WEBHOOK_URL` are read from environment
variables only. They are never logged, never returned in API responses, and
never written to the database. If you find a code path that violates this,
please report it as a security issue.

## Image upload safety

Uploaded landing-page images are stored on disk and served back via
`/api/runs/{id}/image/{a|b}`. The images themselves are not interpreted as
code, but:

- Files are not virus-scanned
- File types are validated only by MIME type (not deep content inspection)
- Operators exposing this publicly should add their own malware scanning

## Disclosure timeline

For confirmed vulnerabilities:

1. **Day 0**: Private report received, acknowledgment within 72 hours
2. **Day 1-14**: Investigation and patch development
3. **Day 14-30**: Patch tested and released
4. **Day 30+**: Public disclosure with credit to the reporter (if desired)
