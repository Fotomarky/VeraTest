#!/usr/bin/env bash
# VeraTest — local dev: backend (FastAPI) + frontend (Next.js) in one command.
#
# Usage:
#   ./scripts/dev.sh              # backend :8000, frontend :3000
#   BACKEND_PORT=8002 ./scripts/dev.sh
#
# Routes Gemini through Vertex AI so "Describe it" mode (the Concierge agent)
# uses the compliant path. Pulls the Phoenix key from Secret Manager. Ctrl-C
# stops both processes.
set -euo pipefail

cd "$(dirname "$0")/.."

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-veratest-497813}"

# Auto-skip occupied backend ports (e.g. a stray ChromaDB on 8000) so the
# frontend never ends up proxying /api to the wrong server.
port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
while port_busy "$BACKEND_PORT"; do
  echo "Port $BACKEND_PORT is in use — trying $((BACKEND_PORT + 1))…"
  BACKEND_PORT=$((BACKEND_PORT + 1))
done

# --- Vertex + Phoenix env for the agent layer (Describe mode) ---------------
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="$PROJECT"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
export PHOENIX_BASE_URL="${PHOENIX_BASE_URL:-https://app.phoenix.arize.com}"
if [[ -z "${PHOENIX_API_KEY:-}" ]]; then
  echo "Fetching PHOENIX_API_KEY from Secret Manager…"
  export PHOENIX_API_KEY="$(gcloud secrets versions access latest \
    --secret=phoenix-api-key --project="$PROJECT" 2>/dev/null || true)"
  [[ -z "$PHOENIX_API_KEY" ]] && echo "  (no key — Phoenix MCP will fall back to localhost)"
fi

# GEMINI_API_KEY is REQUIRED by the pipeline's 20 cognitive walkers (simab/llm.py)
# — the app does NOT auto-load .env, so set it here. Prefer an existing export,
# then .env, then Secret Manager.
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  if [[ -f .env ]] && grep -q '^GEMINI_API_KEY=' .env; then
    export GEMINI_API_KEY="$(grep '^GEMINI_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"'\''')"
    echo "GEMINI_API_KEY loaded from .env"
  else
    echo "Fetching GEMINI_API_KEY from Secret Manager…"
    export GEMINI_API_KEY="$(gcloud secrets versions access latest \
      --secret=gemini-api-key --project="$PROJECT" 2>/dev/null || true)"
  fi
  [[ -z "$GEMINI_API_KEY" ]] && echo "  WARNING: no GEMINI_API_KEY — the pretest pipeline will fail."
fi

# --- Backend ----------------------------------------------------------------
source .venv/bin/activate
echo "Backend  → http://localhost:${BACKEND_PORT}"
uvicorn simab.main:app --reload --port "$BACKEND_PORT" &
BACKEND_PID=$!

cleanup() { echo; echo "Stopping…"; kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# --- Frontend (proxies /api/* to the backend port above) --------------------
echo "Frontend → http://localhost:${FRONTEND_PORT}/new"
cd frontend
NEXT_PUBLIC_API_URL="http://localhost:${BACKEND_PORT}" \
  npm run dev -- --port "$FRONTEND_PORT"
