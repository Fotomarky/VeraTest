#!/usr/bin/env bash
# VeraTest — Google Cloud Run deploy script
# Usage: ./gcp/deploy.sh YOUR_PROJECT_ID [REGION]
# Prerequisites: gcloud CLI authenticated, Docker running

set -euo pipefail

PROJECT_ID="${1:?Usage: ./gcp/deploy.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/veratest-backend"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/veratest-frontend"

echo "→ Deploying to project: ${PROJECT_ID} / region: ${REGION}"

# ── Backend ──────────────────────────────────────────────────────────────────
echo "→ Building backend image..."
docker build -t "${BACKEND_IMAGE}:latest" .
docker push "${BACKEND_IMAGE}:latest"

echo "→ Deploying backend..."
gcloud run deploy veratest-backend \
  --image "${BACKEND_IMAGE}:latest" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 3 \
  --timeout 600 \
  --concurrency 80 \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
  --set-env-vars "SIMAB_DB_PATH=/tmp/simab.db,SIMAB_UPLOAD_DIR=/tmp/uploads,SIMAB_SIM_CONCURRENCY=6"

BACKEND_URL=$(gcloud run services describe veratest-backend \
  --region "${REGION}" --project "${PROJECT_ID}" \
  --format "value(status.url)")
echo "✓ Backend: ${BACKEND_URL}"

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "→ Building frontend image..."
docker build \
  --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
  -t "${FRONTEND_IMAGE}:latest" \
  ./frontend

docker push "${FRONTEND_IMAGE}:latest"

echo "→ Deploying frontend..."
gcloud run deploy veratest-frontend \
  --image "${FRONTEND_IMAGE}:latest" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5

FRONTEND_URL=$(gcloud run services describe veratest-frontend \
  --region "${REGION}" --project "${PROJECT_ID}" \
  --format "value(status.url)")
echo "✓ Frontend: ${FRONTEND_URL}"

# ── Update backend CORS ───────────────────────────────────────────────────────
echo "→ Updating backend FRONTEND_URL → ${FRONTEND_URL}..."
gcloud run services update veratest-backend \
  --region "${REGION}" --project "${PROJECT_ID}" \
  --update-env-vars "FRONTEND_URL=${FRONTEND_URL}"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  VeraTest deployed successfully!                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo "  Frontend:  ${FRONTEND_URL}"
echo "  Backend:   ${BACKEND_URL}"
echo "  Health:    ${BACKEND_URL}/health"
echo ""
echo "Next: set GEMINI_API_KEY secret if not already done:"
echo "  echo -n 'YOUR_KEY' | gcloud secrets create gemini-api-key --data-file=- --project ${PROJECT_ID}"
