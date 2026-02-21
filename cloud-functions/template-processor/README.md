# Cloud Function for Template Processing

Processes compliance templates uploaded to GCS via Pub/Sub trigger.

## Deployment

```bash
gcloud functions deploy compliance-template-processor \
  --gen2 \
  --region=us-central1 \
  --runtime=python311 \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=compliance-template-ingestion \
  --vpc-connector=compliance-vpc-connector \
  --set-env-vars PROJECT_ID=btoproject-486405,REGION=us-central1 \
  --service-account=template-processor-sa@btoproject-486405.iam.gserviceaccount.com \
  --memory=1Gi \
  --timeout=540s
```

## Testing

Publish a test message:
```bash
gcloud pubsub topics publish compliance-template-ingestion \
  --message='{"template_id":"test-1","bucket":"btoproject-486405-compliance-templates","blob_name":"templates/ISO27001/test.pdf","template_type":"ISO27001","version":"1.0"}'
```
