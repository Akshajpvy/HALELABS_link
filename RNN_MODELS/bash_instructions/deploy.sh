#!/bin/bash
# deploy.sh

# Build and push Docker image
gcloud auth configure-docker
docker build -t gcr.io/$PROJECT_ID/water-quality-predictor .
docker push gcr.io/$PROJECT_ID/water-quality-predictor

# Create Vertex AI model
gcloud ai models upload \
  --region=us-central1 \
  --display-name=water-quality-model \
  --container-image-uri=gcr.io/$PROJECT_ID/water-quality-predictor \
  --container-health-route=/health \
  --container-predict-route=/predict

# Create endpoint
gcloud ai endpoints create \
  --region=us-central1 \
  --display-name=water-quality-endpoint

# Get model ID and endpoint ID
MODEL_ID=$(gcloud ai models list --region=us-central1 --format='value(MODEL_ID)' --filter="displayName=water-quality-model")
ENDPOINT_ID=$(gcloud ai endpoints list --region=us-central1 --format='value(ENDPOINT_ID)' --filter="displayName=water-quality-endpoint")

# Deploy model to endpoint
gcloud ai endpoints deploy-model $ENDPOINT_ID \
  --region=us-central1 \
  --model=$MODEL_ID \
  --display-name=water-quality-deployment \
  --machine-type=n1-standard-4 \
  --min-replica-count=1 \
  --max-replica-count=3 \
  --traffic-split=0=100

# Create Pub/Sub topics
gcloud pubsub topics create device_events
gcloud pubsub topics create water_quality_predictions

# Deploy Cloud Functions
gcloud functions deploy register_device \
  --runtime python310 \
  --trigger-http \
  --entry-point register_device \
  --source ./functions \
  --set-env-vars PROJECT_ID=$PROJECT_ID

gcloud functions deploy process_prediction \
  --runtime python310 \
  --trigger-topic water_quality_predictions \
  --entry-point process_prediction \
  --source ./functions \
  --set-env-vars PROJECT_ID=$PROJECT_ID