# Testing & Local Deployment Runbook

Step-by-step verification before pushing to GitHub. **Total time: ~20 minutes.**

```
  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
  │ 1. Smoke   │ → │ 2. API     │ → │ 3. Dash-   │ → │ 4. MCP     │
  │    test    │   │    e2e     │   │    board   │   │    server  │
  │ (2 min)    │   │ (5 min)    │   │ (8 min)    │   │ (5 min)    │
  └────────────┘   └────────────┘   └────────────┘   └────────────┘
```

Optional add-ons (Phoenix, Slack, GA4, cloud deploy) come after the core path.

---

## Prerequisites

1. **Python 3.11+**: `python --version`
2. **Node.js 18+** (only for the dashboard): `node --version`
3. **A free Gemini API key** — get one at https://aistudio.google.com/app/apikey. No credit card required.

```bash
export GEMINI_API_KEY="paste-your-key-here"
```

---

## 1. Smoke test (2 min)

Verify all code imports and unit tests pass before doing anything else.

```bash
cd simab
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

pytest tests/ -v
```

**Expected:** `17 passed in ~3 seconds`. If anything fails, stop and investigate before continuing.

```bash
# Generate sample landing-page images you'll use for the next steps
python tests/fixtures/make_samples.py
```

**Expected:** Two PNG files written to `tests/fixtures/`. Open them to confirm they look like (intentionally bad and good) landing pages.

---

## 2. End-to-end API test (5 min)

Start the backend and run a real pretest via the REST API. No frontend needed.

### 2.1 Start the backend

```bash
uvicorn simab.main:app --reload --port 8000
```

In a **second terminal**, hit the health endpoint:

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"ok","version":"0.1.0"}`

### 2.2 Submit a real run

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@tests/fixtures/variant_a.png" \
  -F "variant_b=@tests/fixtures/variant_b.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools, mostly on desktop"
```

**Expected:** `{"run_id":"run_xxxxx","status":"pending","stream_url":"...","dashboard_url":"..."}`. Note the `run_id`.

### 2.3 Watch the pipeline progress

```bash
RUN_ID="run_xxxxx"   # paste your run_id

# Either poll:
watch -n 2 "curl -s http://localhost:8000/api/runs/$RUN_ID | python -c 'import sys,json; d=json.load(sys.stdin); print(\"status:\",d[\"status\"],\"·\",\"completed:\",len(d[\"simulation_results\"]),\"/20\")'"

# Or stream (cleaner):
curl -N http://localhost:8000/api/runs/$RUN_ID/stream
```

**Expected progression** (~60–120 seconds total):
1. `status: pending` → `normalizing` → `building_scenarios`
2. `simulating` — completed count climbs from 0 to ~20
3. `auditing` → `synthesizing` → `complete`

If it gets stuck on `normalizing` or `simulating` for more than 90 seconds, check the backend terminal for errors. Most likely cause: bad `GEMINI_API_KEY` or rate-limit hit.

### 2.4 Verify outputs

```bash
# Full JSON
curl -s http://localhost:8000/api/runs/$RUN_ID | python -m json.tool

# PM-friendly summary
curl -s http://localhost:8000/api/runs/$RUN_ID/summary | python -m json.tool

# Markdown export (paste this into Notion / Linear / PRD)
curl -s http://localhost:8000/api/runs/$RUN_ID/export.md

# Standalone share page (open in browser)
open http://localhost:8000/share/$RUN_ID   # or visit manually
```

**What to check:**
- The synthesis has a `winner`, `coverage_score`, and `top_friction` array
- The audit has a `trust_level` (high/medium/low)
- The markdown is well-formed and readable
- The share page renders correctly without any JS errors in the console

---

## 3. Dashboard walkthrough (8 min)

Start the frontend and click through both pages.

### 3.1 Start the dashboard

In a **third terminal**:

```bash
cd frontend
npm install   # only first time, ~30 seconds
npm run dev
```

Open http://localhost:3000

**Expected:** Home page loads showing the runs list (your API test run from step 2 should be there).

### 3.2 Walk through the "New run" page

1. Click "New run"
2. **Polish checkpoints — verify these work:**
   - [ ] Click on the Variant A upload area → file picker opens
   - [ ] Pick `tests/fixtures/variant_a.png` → preview appears with filename
   - [ ] Hover over the preview → "Replace" button appears, click works
   - [ ] Upload Variant B the same way
   - [ ] Click a goal example chip (e.g. "sign up for free trial") → text fills in
   - [ ] Click an audience template chip (e.g. "B2B SaaS evaluators") → textarea fills with realistic content
   - [ ] "Run pretest" button is disabled until both files + goal are present
3. Click "Run pretest"
4. You should redirect to `/runs/<id>`

### 3.3 Walk through the "Run results" page

While the run is in progress (~60–120 seconds), watch for:

**Polish checkpoints — verify these work:**
- [ ] Initial skeleton loading state shows before SSE connects
- [ ] Status banner updates with the current phase label (not just status codes)
- [ ] During the `simulating` phase, the progress bar moves as agents complete
- [ ] During other phases, the bar pulses to indicate activity
- [ ] When complete, the variant cards show side-by-side
- [ ] Click on a variant image → opens full-size in new tab
- [ ] Winner card shows with weighted percentage (not just raw count)
- [ ] If trust is medium/low, the trust banner appears **before** the winner
- [ ] Friction themes have color-coded severity borders (red/amber/green)
- [ ] Segment splits render as a stacked horizontal bar chart
- [ ] "Scenario voices" accordion expands and shows all ~20 responses
- [ ] "Copy as markdown" button copies to clipboard, shows "✓ Copied" briefly
- [ ] "Open share page" opens the standalone HTML in a new tab

**Common issues to spot:**
- Run a second time with the **same image for both A and B** — the system should detect ~50/50 split or "neither" winner. If it confidently picks one, your auditor isn't working.
- Resize the browser to mobile width (375px) — verify nothing overflows or breaks.

### 3.4 Inspect a few PM-facing flows

- Open http://localhost:8000/share/$RUN_ID directly (the standalone HTML).
- Copy the markdown and paste it into a Notion test page — verify the table renders.
- Right-click the share page → "Print" → check the print layout is clean.

---

## 4. MCP server test (5 min)

Verify the MCP server starts and the tools are discoverable.

### 4.1 Install the MCP package

```bash
cd mcp/
pip install -e .
```

### 4.2 Smoke-test it via stdio

```bash
# Backend must still be running on :8000
python -m simab_mcp <<EOF
{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.0.1"}}}
{"jsonrpc":"2.0","method":"tools/list","id":2}
EOF
```

**Expected:** Two JSON responses. The second should list four tools: `run_pretest`, `get_pretest_result`, `list_runs`, `list_personas`.

### 4.3 Wire into Claude Desktop (optional)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "simab": {
      "command": "python",
      "args": ["-m", "simab_mcp"],
      "env": {
        "SIMAB_API_URL": "http://localhost:8000",
        "PYTHONPATH": "/absolute/path/to/simab/mcp"
      }
    }
  }
}
```

Restart Claude Desktop, then in a chat:

> *"Use SimAB to run a UX pretest comparing `/full/path/to/variant_a.png` and `/full/path/to/variant_b.png` for the goal 'sign up for free trial'."*

You should see Claude call the `run_pretest` tool, then return a formatted result.

---

## 5. Optional: Phoenix observability (5 min)

See every Gemini call as a span with full inputs/outputs.

```bash
# In a new terminal
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
```

```bash
# In the backend terminal, before starting uvicorn:
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
pip install -e .[phoenix]
uvicorn simab.main:app --reload --port 8000
```

Open http://localhost:6006. Run another pretest. You should see spans appear in real time, one per Gemini call. Click a span to see the prompt, the image inputs, and the response.

**Why this matters for the hackathon demo:** showing the Arize judges your agent activity in Phoenix during the 3-minute video is the most direct demonstration of "real multi-agent orchestration."

---

## 6. Optional: Slack notifications (3 min)

Get a webhook URL from https://api.slack.com/messaging/webhooks (takes 2 minutes).

```bash
export SIMAB_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
uvicorn simab.main:app --reload --port 8000   # restart
```

Run any pretest. When it completes, your Slack channel gets a formatted message with the verdict, top friction, and a "View full report" button linking to the share page.

---

## 7. Cloud deployment (varies by platform)

Once local testing is solid, deploy somewhere a teammate or judge can reach.

### Option A — Render (easiest, free tier sleeps after 15 min idle)

1. Push the repo to GitHub
2. https://dashboard.render.com → New Web Service → connect the repo
3. Settings:
   - Environment: `Docker`
   - Dockerfile path: `./Dockerfile`
   - Region: closest to you
4. Environment variables: `GEMINI_API_KEY`
5. Click "Create Web Service". Initial build ~3 minutes.
6. You get a permanent HTTPS URL like `https://simab-xyz.onrender.com`. Test:
   ```bash
   curl https://simab-xyz.onrender.com/health
   ```

### Option B — Hugging Face Spaces (always free, no card, no sleep)

1. Push the repo to GitHub (or HF directly)
2. https://huggingface.co/new-space → Docker template → link your repo
3. Settings → Repository secrets → add `GEMINI_API_KEY`
4. Wait for build (~5 minutes)
5. URL: `https://<your-username>-simab.hf.space`

### Option C — Cloud Run (Google's free tier — 2M requests/month)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud run deploy simab \
  --source . \
  --region europe-west1 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --memory 1Gi \
  --concurrency 80 \
  --allow-unauthenticated

# You get a URL like https://simab-xxxx-ew.a.run.app
```

### Frontend → Vercel (always free, custom domain support)

```bash
cd frontend
npm i -g vercel
vercel
# Set NEXT_PUBLIC_API_URL to your deployed backend URL during prompts
vercel --prod
```

---

## 8. Pre-flight checklist before pushing to GitHub

Run through this before you `git push`:

### Code
- [ ] `pytest tests/ -v` passes all 17 tests
- [ ] `python -c "import simab; import simab.main; import simab.pipeline"` succeeds without import errors
- [ ] Sample fixture images render correctly (`python tests/fixtures/make_samples.py`)
- [ ] No accidentally committed secrets: `git grep -i "AIza\|sk-\|secret_\|password"` returns nothing

### Documentation
- [ ] `README.md` has correct repo URL once the GitHub repo exists
- [ ] `LICENSE` file exists and is MIT
- [ ] `CONTRIBUTING.md` and `SECURITY.md` are present
- [ ] `BUSINESS.md` reflects the actual business model you intend to pursue

### Repo hygiene
- [ ] `.gitignore` excludes `simab.db`, `uploads/`, `.env`, `__pycache__/`, `node_modules/`, `.next/`
- [ ] No leftover test files (`.pytest_cache/`, `*.egg-info/`)
- [ ] All committed image files are intentional (only the sample fixtures, not real screenshots of customer pages)

### End-to-end sanity
- [ ] Fresh clone in a temp directory → `pip install -e .` → `pytest` → all pass
- [ ] Backend boots cleanly on a fresh checkout
- [ ] Frontend builds without errors: `cd frontend && npm install && npm run build`

### For the hackathon submission specifically
- [ ] License is detectable in the GitHub repo About section (this needs the LICENSE file at repo root)
- [ ] README has a live demo URL (deploy to one of the cloud options above)
- [ ] Demo video is ~3 minutes (per hackathon rules)
- [ ] Devpost submission selects the **Arize** track
- [ ] At least one screenshot in the README showing the dashboard

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: GEMINI_API_KEY is not set` | Forgot to export the env var | `export GEMINI_API_KEY=...` and restart uvicorn |
| Runs stuck on `simulating` forever | Hit Gemini free-tier RPM limit | Lower `SIMAB_SIM_CONCURRENCY=3` and retry |
| `sqlite3.OperationalError: database is locked` | Another process is writing | Stop other uvicorn processes; SQLite WAL handles concurrent reads but only one writer |
| Frontend can't reach backend | CORS or wrong URL | Check `NEXT_PUBLIC_API_URL` matches the backend URL |
| MCP tool not appearing in Claude | Wrong path in `args` | Use absolute paths in `claude_desktop_config.json`, then restart Claude Desktop |
| Phoenix shows no spans | OTLP endpoint wrong | Confirm `PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317` (gRPC port, not 6006) |
| Sample images don't generate | PIL can't find font | Code falls back to default font automatically; check that PIL is installed: `pip show pillow` |

---

## What "good" looks like

A passing local test session should show all of the following:

1. ✅ `pytest tests/` → 17/17 passed
2. ✅ Health endpoint returns OK
3. ✅ End-to-end run completes in 60–120s with a non-empty synthesis
4. ✅ Markdown export is readable
5. ✅ Share page loads as standalone HTML
6. ✅ Dashboard new-run form has previews, examples, and disabled-state validation
7. ✅ Run-results page shows trust banner before winner when audit confidence < high
8. ✅ MCP server responds to `tools/list` with 4 tools
9. ✅ (Optional) Phoenix shows ~24 spans per run
10. ✅ (Optional) Slack receives a formatted message on completion

If all 10 are green, you're ready to push.
