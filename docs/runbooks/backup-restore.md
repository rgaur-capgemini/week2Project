# Backup and Disaster Recovery Runbook

## 📋 Purpose

Comprehensive procedures for backing up critical data and recovering from disasters in the RAG Chatbot production system.

## 🎯 Backup Strategy

### Backup Schedule
- **Firestore**: Automated daily backups + on-demand
- **Redis**: Automated snapshots every 6 hours
- **GCS Documents**: Versioning enabled (automatic)
- **Kubernetes Configs**: Weekly manual backups
- **Secrets**: No backups (recreate from Secret Manager)

### Retention Policy
- **Daily backups**: 30 days
- **Weekly backups**: 90 days
- **Monthly backups**: 1 year
- **Incident backups**: 2 years

### Recovery Objectives
- **RPO (Recovery Point Objective)**: < 1 hour
- **RTO (Recovery Time Objective)**: < 4 hours for full system
- **RTO (Single Component)**: < 1 hour

---

## 🔑 Prerequisites

### Required Access
- **GCP Roles**:
  - `roles/datastore.importExportAdmin` (Firestore)
  - `roles/storage.admin` (GCS)
  - `roles/redis.admin` (Memorystore)
  - `roles/container.admin` (GKE)
  
### Required Tools
```bash
gcloud version    # Latest
kubectl version   # >= 1.28
gsutil version    # Latest
```

### Backup Bucket
```bash
export PROJECT_ID="btoproject-486405-486604"
export BACKUP_BUCKET="gs://${PROJECT_ID}-backups"
export REGION="us-central1"
```

---

## 💾 Backup Procedures

### 1. Firestore Backup

#### 1.1 Manual On-Demand Backup

```bash
# Set variables
export PROJECT_ID="btoproject-486405-486604"
export BACKUP_BUCKET="gs://${PROJECT_ID}-backups/firestore"
export TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Export all collections
gcloud firestore export ${BACKUP_BUCKET}/${TIMESTAMP} \
  --project=${PROJECT_ID} \
  --async

# Export specific collection (rag_chunks)
gcloud firestore export ${BACKUP_BUCKET}/${TIMESTAMP}-rag_chunks \
  --collection-ids=rag_chunks \
  --project=${PROJECT_ID}

# Check export status
gcloud firestore operations list --project=${PROJECT_ID}

# Describe specific operation
gcloud firestore operations describe <OPERATION_ID> --project=${PROJECT_ID}
```

**Duration**: 5-30 minutes depending on data size.

#### 1.2 Automated Daily Backup

Already configured via Cloud Scheduler:
```bash
# Verify scheduled backup exists
gcloud scheduler jobs list --location=${REGION}

# Check last backup
gsutil ls -lh ${BACKUP_BUCKET}/firestore/ | tail -10

# Trigger manual run
gcloud scheduler jobs run firestore-daily-backup \
  --location=${REGION}
```

---

### 2. Redis (Memorystore) Backup

#### 2.1 Manual Snapshot

```bash
# Get Redis instance name
export REDIS_INSTANCE="rag-redis-instance"

# Create snapshot
gcloud redis instances export \
  gs://${PROJECT_ID}-backups/redis/redis-snapshot-${TIMESTAMP}.rdb \
  --source=${REDIS_INSTANCE} \
  --region=${REGION}

# Monitor export
gcloud redis operations list --region=${REGION}
```

#### 2.2 Verify Automated Snapshots

```bash
# List recent snapshots
gsutil ls -lh gs://${PROJECT_ID}-backups/redis/

# Should see snapshots every 6 hours
```

**Note**: Redis Memorystore HA automatically performs snapshots.

---

### 3. GCS Documents Backup

#### 3.1 Verify Versioning Enabled

```bash
# Check if versioning is enabled
gsutil versioning get gs://${PROJECT_ID}-rag-documents

# Expected output: Enabled

# If not enabled, enable it
gsutil versioning set on gs://${PROJECT_ID}-rag-documents
```

#### 3.2 Manual Full Backup

```bash
# Copy all documents to backup bucket
gsutil -m cp -r \
  gs://${PROJECT_ID}-rag-documents/* \
  gs://${PROJECT_ID}-backups/gcs/documents-${TIMESTAMP}/

# Verify backup
gsutil du -sh gs://${PROJECT_ID}-backups/gcs/documents-${TIMESTAMP}/
```

#### 3.3 List Object Versions

```bash
# List all versions of a specific object
gsutil ls -a gs://${PROJECT_ID}-rag-documents/document.pdf

# Shows all versions with generation numbers
```

---

### 4. Kubernetes Configuration Backup

#### 4.1 Backup All Deployments and Services

```bash
export TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export BACKUP_DIR="k8s-backup-${TIMESTAMP}"

mkdir -p ${BACKUP_DIR}

# Backup deployments
kubectl get deployments -o yaml > ${BACKUP_DIR}/deployments.yaml

# Backup services
kubectl get services -o yaml > ${BACKUP_DIR}/services.yaml

# Backup configmaps
kubectl get configmaps -o yaml > ${BACKUP_DIR}/configmaps.yaml

# Backup secrets (encrypted only!)
kubectl get secrets -o yaml > ${BACKUP_DIR}/secrets.yaml.enc

# Backup HPA
kubectl get hpa -o yaml > ${BACKUP_DIR}/hpa.yaml

# Backup ingress
kubectl get ingress -o yaml > ${BACKUP_DIR}/ingress.yaml

# Backup network policies
kubectl get networkpolicies -o yaml > ${BACKUP_DIR}/networkpolicies.yaml

# Backup service accounts
kubectl get serviceaccounts -o yaml > ${BACKUP_DIR}/serviceaccounts.yaml

# Create tarball
tar -czf ${BACKUP_DIR}.tar.gz ${BACKUP_DIR}

# Upload to GCS
gsutil cp ${BACKUP_DIR}.tar.gz gs://${PROJECT_ID}-backups/k8s/

# Cleanup
rm -rf ${BACKUP_DIR} ${BACKUP_DIR}.tar.gz

# Verify upload
gsutil ls -lh gs://${PROJECT_ID}-backups/k8s/${BACKUP_DIR}.tar.gz
```

---

### 5. Vertex AI Vector Index Backup

```bash
# Note: Vertex AI Vector Search does not support direct backups
# Backup strategy: Re-index from Firestore chunks if needed

# Backup index metadata and configuration
cat > vertex-ai-index-config-${TIMESTAMP}.yaml <<EOF
index_id: ${VERTEX_INDEX_ID}
index_endpoint: ${VERTEX_INDEX_ENDPOINT}
deployed_index_id: ${DEPLOYED_INDEX_ID}
embedding_dimension: 768
model: text-embedding-004
shard_size: 1000000
backup_date: ${TIMESTAMP}
EOF

# Upload config
gsutil cp vertex-ai-index-config-${TIMESTAMP}.yaml \
  gs://${PROJECT_ID}-backups/vertex-ai/
```

---

## 🔄 Restore Procedures

### 1. Restore Firestore

#### 1.1 Full Restore

```bash
# List available backups
gsutil ls gs://${PROJECT_ID}-backups/firestore/

# Import from backup
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/20260210_143000 \
  --project=${PROJECT_ID}

# Monitor import
gcloud firestore operations list --project=${PROJECT_ID}
```

**⚠️ WARNING**: This will overwrite existing data!

#### 1.2 Restore Specific Collection

```bash
# Import only rag_chunks collection
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/20260210_143000 \
  --collection-ids=rag_chunks \
  --project=${PROJECT_ID}
```

#### 1.3 Point-in-Time Recovery

```bash
# For point-in-time recovery, use exports from specific timestamp
# Firestore doesn't have native PITR, use closest export

gsutil ls gs://${PROJECT_ID}-backups/firestore/ | sort

# Select the backup closest to desired recovery point
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/<TIMESTAMP>
```

---

### 2. Restore Redis

#### 2.1 Import from Snapshot

```bash
# Import snapshot to existing Redis instance
gcloud redis instances import \
  gs://${PROJECT_ID}-backups/redis/redis-snapshot-20260210_143000.rdb \
  --source=${REDIS_INSTANCE} \
  --region=${REGION}

# Monitor import
gcloud redis operations list --region=${REGION}
```

**Duration**: 5-15 minutes

#### 2.2 Verify Restored Data

```bash
# Connect to Redis
kubectl run redis-client --rm -it --image=redis -- /bin/bash

# Inside container:
redis-cli -h <REDIS_HOST>
KEYS *
GET <KEY>
exit
```

---

### 3. Restore GCS Documents

#### 3.1 Restore Specific Version

```bash
# List versions of a document
gsutil ls -a gs://${PROJECT_ID}-rag-documents/document.pdf

# Restore specific version (copy with generation number)
gsutil cp gs://${PROJECT_ID}-rag-documents/document.pdf#<GENERATION> \
  gs://${PROJECT_ID}-rag-documents/document.pdf
```

#### 3.2 Restore Deleted Object

```bash
# List deleted objects (within retention period)
gsutil ls -a gs://${PROJECT_ID}-rag-documents/ | grep "#"

# Restore by copying specific generation
gsutil cp gs://${PROJECT_ID}-rag-documents/deleted-file.pdf#<GENERATION> \
  gs://${PROJECT_ID}-rag-documents/deleted-file.pdf
```

#### 3.3 Bulk Restore from Backup

```bash
# Restore entire backup folder
gsutil -m cp -r \
  gs://${PROJECT_ID}-backups/gcs/documents-20260210_143000/* \
  gs://${PROJECT_ID}-rag-documents/
```

---

### 4. Restore Kubernetes Configuration

#### 4.1 Download Backup

```bash
# List available backups
gsutil ls gs://${PROJECT_ID}-backups/k8s/

# Download specific backup
gsutil cp gs://${PROJECT_ID}-backups/k8s/k8s-backup-20260210_143000.tar.gz .

# Extract
tar -xzf k8s-backup-20260210_143000.tar.gz
cd k8s-backup-20260210_143000
```

#### 4.2 Restore Deployments

```bash
# Review what will be restored
kubectl diff -f deployments.yaml

# Apply restore
kubectl apply -f deployments.yaml

# Verify
kubectl get deployments
kubectl get pods
```

#### 4.3 Restore Services and ConfigMaps

```bash
# Restore services
kubectl apply -f services.yaml

# Restore configmaps
kubectl apply -f configmaps.yaml

# Restore HPA
kubectl apply -f hpa.yaml

# Verify
kubectl get services
kubectl get configmaps
kubectl get hpa
```

---

### 5. Restore Vertex AI Vector Index

**Note**: Vector indices cannot be directly restored. Re-index from Firestore.

```bash
# Re-index from Firestore chunks
# This will be done via the application API

# Get service URL
SERVICE_URL=$(kubectl get service rag-backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Trigger re-indexing (if API endpoint exists)
curl -X POST http://${SERVICE_URL}/admin/reindex \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"

# Monitor re-indexing progress
kubectl logs -l app=rag-backend -f | grep reindex
```

**Duration**: 1-4 hours depending on data volume

---

## 🚨 Disaster Recovery Scenarios

### Scenario 1: Complete Data Center Failure

**RPO**: 1 hour | **RTO**: 4 hours

#### Recovery Steps:

1. **Create new GKE cluster in alternate region**
```bash
gcloud container clusters create rag-chatbot-cluster-dr \
  --region=us-east1 \
  --num-nodes=3 \
  --machine-type=n1-standard-2
```

2. **Restore Firestore** (from last backup)
```bash
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/latest
```

3. **Restore Redis** (create new instance and import)
```bash
gcloud redis instances create rag-redis-dr \
  --size=5 \
  --region=us-east1

gcloud redis instances import \
  gs://${PROJECT_ID}-backups/redis/latest.rdb \
  --source=rag-redis-dr \
  --region=us-east1
```

4. **Deploy application**
```bash
kubectl apply -f k8s-backup-latest/
```

5. **Update DNS** (point to new load balancer)

---

### Scenario 2: Accidental Data Deletion

**RPO**: 15 minutes | **RTO**: 1 hour

#### Recovery Steps:

1. **Identify scope of deletion**
```bash
# Check Firestore audit logs
gcloud logging read "protoPayload.methodName='google.firestore.v1.Firestore.Delete*'" \
  --limit 100 \
  --format json
```

2. **Restore from most recent backup**
```bash
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/latest \
  --collection-ids=<AFFECTED_COLLECTION>
```

3. **Verify restored data**
```bash
# Query restored data via API
curl http://${SERVICE_URL}/admin/verify-data
```

---

### Scenario 3: Database Corruption

**RPO**: 1 hour | **RTO**: 2 hours

#### Recovery Steps:

1. **Stop write operations** (scale backend to 0)
```bash
kubectl scale deployment rag-backend --replicas=0
```

2. **Export current data** (for forensics)
```bash
gcloud firestore export gs://${PROJECT_ID}-backups/firestore/corruption-${TIMESTAMP}
```

3. **Restore from last known good backup**
```bash
gcloud firestore import gs://${PROJECT_ID}-backups/firestore/20260210_140000
```

4. **Verify data integrity**
```bash
# Custom verification script
python scripts/verify_data_integrity.py
```

5. **Resume operations**
```bash
kubectl scale deployment rag-backend --replicas=3
```

---

## ✅ Verification Procedures

### 1. Verify Firestore Restore

```bash
# Check collection count
gcloud firestore collections list --project=${PROJECT_ID}

# Sample query
gcloud firestore documents list --collection=rag_chunks --limit=5
```

### 2. Verify Redis Restore

```bash
# Connect and check keys
kubectl run redis-client --rm -it --image=redis -- redis-cli -h <REDIS_HOST>

# Check key count
DBSIZE

# Sample keys
KEYS * | head -10
```

### 3. Verify GCS Restore

```bash
# Check object count
gsutil ls -r gs://${PROJECT_ID}-rag-documents/ | wc -l

# Check total size
gsutil du -sh gs://${PROJECT_ID}-rag-documents/
```

### 4. End-to-End Functional Test

```bash
# Health check
curl http://${SERVICE_URL}/health

# Query test
curl -X POST http://${SERVICE_URL}/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Test query","top_k":3}'

# Ingest test
curl -X POST http://${SERVICE_URL}/ingest \
  -F "files=@test.pdf"
```

---

## 📋 Backup Verification Schedule

### Daily
- [ ] Verify Firestore backup completed
- [ ] Check backup size (should be consistent)

### Weekly
- [ ] Test restore of one Firestore collection to staging
- [ ] Verify Redis snapshot integrity
- [ ] Review backup retention policy compliance

### Monthly
- [ ] Full disaster recovery drill
- [ ] Update backup documentation
- [ ] Review and update RTO/RPO targets

---

## 📞 Escalation

### Backup Failure
- **< 2 hours**: Investigate and retry
- **> 2 hours**: Escalate to SRE Lead
- **> 4 hours**: Engage GCP Support

### Restore Failure
- **< 1 hour**: Troubleshoot
- **> 1 hour**: Escalate to SRE Lead
- **> 2 hours**: Engage GCP Support (P1)

---

## 🔗 Related Documentation

- [SRE Runbook](../SRE_RUNBOOK.md)
- [Rollback Runbook](rollback.md)
- [Firestore Backup Docs](https://cloud.google.com/firestore/docs/manage-data/export-import)
- [Redis Backup Docs](https://cloud.google.com/memorystore/docs/redis/import-export-data)

---

**Last Updated**: February 2026  
**Maintained By**: SRE Team  
**Review Frequency**: Monthly  
**Tested**: Last DR drill on 2026-01-15
