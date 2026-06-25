gcloud ai custom-jobs create \
  --region=$REGION \
  --display-name="water-quality-training" \
  --python-package-uris=$MODEL_BUCKET/water_quality_package.tar.gz \
  --worker-pool-spec=machine-type=n1-standard-4,accelerator-type=NVIDIA_TESLA_T4,accelerator-count=1,replica-count=1,executor-image-uri=us-docker.pkg.dev/vertex-ai/training/tf-gpu.2-12:latest,python-module=train.task \
  --args="--data-bucket=$(basename $DATA_BUCKET),--data-file=water_potability.csv,--output-bucket=$(basename $MODEL_BUCKET)"