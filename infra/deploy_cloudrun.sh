#!/usr/bin/env bash
# Deploy FSI Helix (api + web) to Cloud Run.
#   GOOGLE_CLOUD_PROJECT=raves-altostrat GCP_REGION=us-central1 ./infra/deploy_cloudrun.sh
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-raves-altostrat}"
REGION="${GCP_REGION:-us-central1}"
REPO="fsi-helix"
API_IMG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/fsi-helix-api"
WEB_IMG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/fsi-helix-web"

echo ">> Enabling services"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com --project "$PROJECT"

echo ">> Artifact Registry repo"
gcloud artifacts repositories create "$REPO" --repository-format=docker \
  --location="$REGION" --project "$PROJECT" 2>/dev/null || true

echo ">> Build + deploy API (backend)"
gcloud builds submit backend --tag "$API_IMG" --project "$PROJECT"
gcloud run deploy fsi-helix-api \
  --image "$API_IMG" --region "$REGION" --project "$PROJECT" \
  --allow-unauthenticated --port 8080 --memory 1Gi \
  --set-env-vars "USE_BQ=true,GOOGLE_CLOUD_PROJECT=${PROJECT},GCP_REGION=${REGION},BQ_LOCATION=${REGION},BQ_DATASET=FSI_POV,BQ_CONNECTION=${REGION}.vertex_conn"

API_URL=$(gcloud run services describe fsi-helix-api --region "$REGION" \
  --project "$PROJECT" --format='value(status.url)')
echo ">> API at ${API_URL}"

echo ">> Build + deploy Web (frontend), wired to API"
gcloud builds submit frontend --tag "$WEB_IMG" --project "$PROJECT" \
  --sapextitutions "_VITE_API_BASE=${API_URL}" 2>/dev/null \
  || gcloud builds submit frontend --tag "$WEB_IMG" --project "$PROJECT"
gcloud run deploy fsi-helix-web \
  --image "$WEB_IMG" --region "$REGION" --project "$PROJECT" \
  --allow-unauthenticated --port 8080

echo ">> Done."
echo "   API: ${API_URL}"
gcloud run services describe fsi-helix-web --region "$REGION" --project "$PROJECT" --format='value(status.url)'

# NOTE: ensure the Cloud Run runtime service account has roles/bigquery.jobUser,
# roles/bigquery.dataViewer and access to the us-central1.vertex_conn connection,
# plus roles/aiplatform.user for Gemini generation.
