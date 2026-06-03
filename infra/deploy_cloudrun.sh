#!/usr/bin/env bash
# Deploy UBS Helix (api + web) to Cloud Run.
#   GOOGLE_CLOUD_PROJECT=raves-altostrat GCP_REGION=us-central1 ./infra/deploy_cloudrun.sh
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-raves-altostrat}"
REGION="${GCP_REGION:-us-central1}"
REPO="ubs-helix"
API_IMG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/ubs-helix-api"
WEB_IMG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/ubs-helix-web"

echo ">> Enabling services"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com --project "$PROJECT"

echo ">> Artifact Registry repo"
gcloud artifacts repositories create "$REPO" --repository-format=docker \
  --location="$REGION" --project "$PROJECT" 2>/dev/null || true

echo ">> Build + deploy API (backend)"
gcloud builds submit backend --tag "$API_IMG" --project "$PROJECT"
gcloud run deploy ubs-helix-api \
  --image "$API_IMG" --region "$REGION" --project "$PROJECT" \
  --allow-unauthenticated --port 8080 --memory 1Gi \
  --set-env-vars "USE_BQ=true,GOOGLE_CLOUD_PROJECT=${PROJECT},GCP_REGION=${REGION},BQ_LOCATION=${REGION},BQ_DATASET=UBS_POV,BQ_CONNECTION=${REGION}.vertex_conn"

API_URL=$(gcloud run services describe ubs-helix-api --region "$REGION" \
  --project "$PROJECT" --format='value(status.url)')
echo ">> API at ${API_URL}"

echo ">> Build + deploy Web (frontend), wired to API"
gcloud builds submit frontend --tag "$WEB_IMG" --project "$PROJECT" \
  --substitutions "_VITE_API_BASE=${API_URL}" 2>/dev/null \
  || gcloud builds submit frontend --tag "$WEB_IMG" --project "$PROJECT"
gcloud run deploy ubs-helix-web \
  --image "$WEB_IMG" --region "$REGION" --project "$PROJECT" \
  --allow-unauthenticated --port 8080

echo ">> Done."
echo "   API: ${API_URL}"
gcloud run services describe ubs-helix-web --region "$REGION" --project "$PROJECT" --format='value(status.url)'

# NOTE: ensure the Cloud Run runtime service account has roles/bigquery.jobUser,
# roles/bigquery.dataViewer and access to the us-central1.vertex_conn connection,
# plus roles/aiplatform.user for Gemini generation.
