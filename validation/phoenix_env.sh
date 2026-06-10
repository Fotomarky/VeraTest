# Source this to point the validation harness at the same Phoenix Cloud
# space as the deployed backend:  `source validation/phoenix_env.sh`
#
# Non-secret values mirror the veratest-backend Cloud Run env. The two API
# keys are pulled live from Secret Manager so nothing secret lives in git.
#
# Requires: gcloud auth + access to project veratest-497813.

PROJECT="veratest-497813"

# --- Phoenix Cloud (mirrors Cloud Run literal env) ---
export PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/caruso-mrc"
# Validation traces land in their own project so they don't mix with live
# product runs. Override to "VeraTest" if you want them together.
export PHOENIX_PROJECT="${PHOENIX_PROJECT:-VeraTest-validation}"

# --- Secrets (Secret Manager, fetched at runtime) ---
export PHOENIX_API_KEY="$(gcloud secrets versions access latest \
  --secret=phoenix-api-key --project="$PROJECT" 2>/dev/null)"
export GEMINI_API_KEY="$(gcloud secrets versions access latest \
  --secret=gemini-api-key --project="$PROJECT" 2>/dev/null)"

if [ -z "$PHOENIX_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
  echo "WARN: could not fetch secrets — check 'gcloud auth' and Secret Manager access." >&2
else
  echo "Phoenix env loaded: project=$PHOENIX_PROJECT endpoint=$PHOENIX_COLLECTOR_ENDPOINT"
fi
