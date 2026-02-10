# Certificate and Credential Rotation Runbook

## 📋 Purpose

Step-by-step procedures for rotating TLS certificates, service account keys, OAuth credentials, JWT secrets, and API keys to maintain security and compliance.

## 🔐 Rotation Schedule

| Credential Type | Rotation Frequency | Auto/Manual | Priority |
|----------------|-------------------|-------------|----------|
| **TLS/SSL Certificates** | 90 days (30 days before expiry) | Manual | P1 |
| **GCP Service Account Keys** | 90 days | Manual | P1 |
| **JWT Secret Keys** | 180 days | Manual | P2 |
| **OAuth 2.0 Client Secret** | Annually or on breach | Manual | P1 |
| **API Keys (External)** | Annually | Manual | P2 |
| **Database Passwords** | 90 days | Manual | P1 |
| **Redis Password** | 90 days | Manual | P2 |

---

## 🔑 Prerequisites

### Required Access
- Secret Manager Admin (`roles/secretmanager.admin`)
- GKE Admin (`roles/container.admin`)
- Service Account Admin (`roles/iam.serviceAccountAdmin`)
- Certificate Authority Admin (if using Certificate Manager)

### Required Tools
```bash
gcloud version    # Latest
kubectl version   # >= 1.28
openssl version   # >= 1.1.1
```

---

## 🔄 Certificate Rotation Procedures

### 1. TLS Certificate Rotation (Load Balancer)

#### 1.1 Check Current Certificate Expiry

```bash
# Get ingress details
kubectl get ingress -o yaml

# Check certificate expiry
echo | openssl s_client -servername <YOUR_DOMAIN> \
  -connect <YOUR_DOMAIN>:443 2>/dev/null | \
  openssl x509 -noout -dates

# Expected output:
# notBefore=Jan  1 00:00:00 2026 GMT
# notAfter=Apr  1 23:59:59 2026 GMT
```

**Rotate when**: < 30 days until expiry

---

#### 1.2 Generate New Certificate

**Option A: Using cert-manager (Recommended)**

```bash
# Install cert-manager (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: sre@yourcompany.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update ingress to use cert-manager
kubectl annotate ingress <INGRESS_NAME> \
  cert-manager.io/cluster-issuer=letsencrypt-prod

# cert-manager will auto-renew 30 days before expiry
```

**Option B: Manual Certificate (Self-Signed or CA)**

```bash
# Generate new private key
openssl genrsa -out tls-new.key 2048

# Generate certificate signing request (CSR)
openssl req -new -key tls-new.key -out tls-new.csr \
  -subj "/CN=<YOUR_DOMAIN>/O=Your Org/C=US"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 \
  -in tls-new.csr \
  -signkey tls-new.key \
  -out tls-new.crt

# Or submit CSR to your CA for signing
```

---

#### 1.3 Update Kubernetes Secret

```bash
# Backup existing certificate secret
kubectl get secret tls-secret -o yaml > tls-secret-backup.yaml

# Delete old secret
kubectl delete secret tls-secret

# Create new secret with new certificate
kubectl create secret tls tls-secret \
  --cert=tls-new.crt \
  --key=tls-new.key

# Verify secret
kubectl describe secret tls-secret
```

---

#### 1.4 Verify Certificate

```bash
# Check ingress uses new certificate
kubectl rollout restart deployment/rag-backend

# Test HTTPS connection
curl -vI https://<YOUR_DOMAIN>

# Verify certificate details
echo | openssl s_client -servername <YOUR_DOMAIN> \
  -connect <YOUR_DOMAIN>:443 2>/dev/null | \
  openssl x509 -noout -text

# Check expiry date
echo | openssl s_client -servername <YOUR_DOMAIN> \
  -connect <YOUR_DOMAIN>:443 2>/dev/null | \
  openssl x509 -noout -dates
```

---

### 2. GCP Service Account Key Rotation

#### 2.1 List Existing Keys

```bash
export PROJECT_ID="btoproject-486405-486604"
export SA_EMAIL="rag-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# List all keys for service account
gcloud iam service-accounts keys list \
  --iam-account=${SA_EMAIL} \
  --project=${PROJECT_ID}

# Check key age
gcloud iam service-accounts keys list \
  --iam-account=${SA_EMAIL} \
  --format="table(name,validAfterTime,validBeforeTime)" \
  --project=${PROJECT_ID}
```

---

#### 2.2 Create New Service Account Key

```bash
# Create new key
gcloud iam service-accounts keys create new-sa-key.json \
  --iam-account=${SA_EMAIL} \
  --project=${PROJECT_ID}

# Verify key created
gcloud iam service-accounts keys list --iam-account=${SA_EMAIL}

# Should see 2 keys now (old + new)
```

---

#### 2.3 Update Application to Use New Key

**Option A: Using Workload Identity (Recommended - No Keys!)**

```bash
# Already configured - no key rotation needed!
# Workload Identity uses short-lived tokens automatically
kubectl describe serviceaccount rag-backend-sa | grep Annotations
# Should see: iam.gke.io/gcp-service-account annotation
```

**Option B: Using Key File (Legacy)**

```bash
# Store new key in Secret Manager
gcloud secrets create sa-key-new \
  --data-file=new-sa-key.json \
  --project=${PROJECT_ID}

# Update Kubernetes secret
kubectl create secret generic gcp-sa-key \
  --from-file=key.json=new-sa-key.json \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new key
kubectl rollout restart deployment/rag-backend
kubectl rollout restart deployment/rag-frontend

# Verify pods are running
kubectl get pods -w
```

---

#### 2.4 Delete Old Service Account Key

```bash
# Wait 24-48 hours to ensure no issues with new key

# Get old key ID
OLD_KEY_ID=$(gcloud iam service-accounts keys list \
  --iam-account=${SA_EMAIL} \
  --format="value(name)" \
  --filter="validAfterTime<$(date -d '90 days ago' --iso-8601)")

# Delete old key
gcloud iam service-accounts keys delete ${OLD_KEY_ID} \
  --iam-account=${SA_EMAIL} \
  --project=${PROJECT_ID} \
  --quiet

# Verify only new key remains
gcloud iam service-accounts keys list --iam-account=${SA_EMAIL}
```

---

### 3. JWT Secret Key Rotation

#### 3.1 Generate New JWT Secret

```bash
# Generate strong random secret (256-bit)
NEW_JWT_SECRET=$(openssl rand -base64 32)

echo "New JWT Secret: ${NEW_JWT_SECRET}"

# Store in Secret Manager
echo -n "${NEW_JWT_SECRET}" | gcloud secrets create jwt-secret-new \
  --data-file=- \
  --project=${PROJECT_ID}

# Or update existing secret with new version
echo -n "${NEW_JWT_SECRET}" | gcloud secrets versions add jwt-secret \
  --data-file=- \
  --project=${PROJECT_ID}
```

---

#### 3.2 Deploy with Both Keys (Grace Period)

Update application to accept BOTH old and new JWT secrets during transition:

```python
# In app/auth/jwt_handler.py
OLD_JWT_SECRET = get_secret("jwt-secret", version="1")
NEW_JWT_SECRET = get_secret("jwt-secret", version="2")

def verify_token(token):
    try:
        # Try new secret first
        return jwt.decode(token, NEW_JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidSignatureError:
        # Fallback to old secret
        return jwt.decode(token, OLD_JWT_SECRET, algorithms=["HS256"])
```

Deploy updated code:
```bash
# Build and deploy
kubectl set image deployment/rag-backend \
  rag-backend=gcr.io/${PROJECT_ID}/rag-backend:v2.1.0

kubectl rollout status deployment/rag-backend
```

---

#### 3.3 Issue New Tokens with New Secret

```bash
# All new logins will use new JWT secret
# Existing tokens (with old secret) remain valid for grace period

# Grace period: 24 hours (or your token TTL)
```

---

#### 3.4 Remove Old Secret Support

After grace period (24-48 hours):

```python
# Update app/auth/jwt_handler.py to only use new secret
JWT_SECRET = get_secret("jwt-secret", version="2")  # Only new secret
```

Deploy and delete old secret version:
```bash
# Deploy
kubectl set image deployment/rag-backend \
  rag-backend=gcr.io/${PROJECT_ID}/rag-backend:v2.1.1

# Delete old secret version
gcloud secrets versions destroy 1 \
  --secret=jwt-secret \
  --project=${PROJECT_ID}
```

---

### 4. OAuth 2.0 Client Secret Rotation

#### 4.1 Create New OAuth Client Secret

```bash
# Go to GCP Console > APIs & Services > Credentials
# Click on OAuth 2.0 Client ID
# Click "Add Secret" (keeps old secret active)

# Or regenerate (invalidates old secret immediately - not recommended)
```

**Best Practice**: Add new secret without deleting old one first.

---

#### 4.2 Update Backend Configuration

```bash
# Store new OAuth secret in Secret Manager
echo -n "NEW_CLIENT_SECRET" | gcloud secrets versions add oauth-client-secret \
  --data-file=- \
  --project=${PROJECT_ID}

# Update ConfigMap (if using env vars)
kubectl create configmap rag-config \
  --from-literal=GOOGLE_CLIENT_SECRET=<NEW_SECRET> \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart backend
kubectl rollout restart deployment/rag-backend
```

---

#### 4.3 Verify OAuth Login Works

```bash
# Test login flow
# 1. Navigate to https://<YOUR_DOMAIN>/login
# 2. Click "Sign in with Google"
# 3. Complete OAuth flow
# 4. Verify successful login

# Check backend logs
kubectl logs -l app=rag-backend | grep oauth
```

---

#### 4.4 Delete Old OAuth Client Secret

```bash
# Wait 24-48 hours

# Go to GCP Console > APIs & Services > Credentials
# Click on OAuth 2.0 Client ID
# Delete old secret
```

---

### 5. API Keys Rotation (External Services)

#### 5.1 Vertex AI API Key (Not Applicable)

Vertex AI uses service account authentication (Workload Identity) - no API key rotation needed.

---

#### 5.2 Third-Party API Keys

Example: OpenAI, SendGrid, etc. (if used)

```bash
# Generate new API key from third-party service

# Update Secret Manager
echo -n "NEW_API_KEY" | gcloud secrets versions add third-party-api-key \
  --data-file=- \
  --project=${PROJECT_ID}

# Update application
kubectl rollout restart deployment/rag-backend

# Verify
kubectl logs -l app=rag-backend | grep "API key"

# Delete old API key from third-party service after 24 hours
```

---

### 6. Redis Password Rotation

#### 6.1 Update Redis AUTH Password

```bash
# For Memorystore Redis, password rotation requires:
# 1. Update instance config
# 2. Rolling restart of application

# Update Redis instance auth
gcloud redis instances update rag-redis-instance \
  --update-auth-string="NEW_STRONG_PASSWORD" \
  --region=${REGION}

# Store new password in Secret Manager
echo -n "NEW_STRONG_PASSWORD" | gcloud secrets versions add redis-password \
  --data-file=- \
  --project=${PROJECT_ID}
```

---

#### 6.2 Update Application Configuration

```bash
# Update backend to use new Redis password
kubectl create secret generic redis-secret \
  --from-literal=password=NEW_STRONG_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart
kubectl rollout restart deployment/rag-backend

# Verify Redis connection
kubectl logs -l app=rag-backend | grep redis
```

---

## ✅ Verification Checklist

### Post-Rotation Verification

- [ ] Health check passing: `curl https://<DOMAIN>/health`
- [ ] Readiness check passing: `curl https://<DOMAIN>/readiness`
- [ ] OAuth login working
- [ ] JWT tokens validating correctly
- [ ] API calls to GCP services successful
- [ ] No authentication errors in logs
- [ ] Redis connections working
- [ ] End-to-end flow tested

### Monitoring (24-48 hours post-rotation)

- [ ] No spike in authentication errors
- [ ] No spike in 401/403 errors
- [ ] Normal request latency
- [ ] Normal request throughput
- [ ] No alerts triggered

---

## 🚨 Rollback Procedures

### If Rotation Causes Issues

#### TLS Certificate Rollback
```bash
# Restore old certificate
kubectl apply -f tls-secret-backup.yaml

# Restart ingress controller
kubectl rollout restart deployment/nginx-ingress-controller
```

#### Service Account Key Rollback
```bash
# Use old key
kubectl create secret generic gcp-sa-key \
  --from-file=key.json=old-sa-key.json \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/rag-backend
```

#### JWT Secret Rollback
```bash
# Revert to old secret version
gcloud secrets versions enable 1 --secret=jwt-secret

# Deploy previous version
kubectl rollout undo deployment/rag-backend
```

---

## 📋 Rotation Log Template

```markdown
## Credential Rotation Log

**Date**: 2026-02-10 14:00 UTC
**Operator**: SRE Team
**Credential Type**: JWT Secret Key

### Pre-Rotation
- Old secret version: 1
- Old secret age: 185 days
- Backup created: ✅
- Stakeholders notified: ✅

### Rotation
- New secret generated: ✅ 14:05 UTC
- New secret deployed: ✅ 14:10 UTC
- Grace period started: 14:10 UTC
- Grace period ended: 14:10 UTC + 48h

### Verification
- Health checks: ✅ PASS
- OAuth login: ✅ PASS
- API calls: ✅ PASS
- Error logs: ✅ No errors
- Monitoring: ✅ Normal

### Cleanup
- Old secret deleted: ✅ 2026-02-12 14:30 UTC
- Documentation updated: ✅
- Next rotation due: 2026-08-09

### Issues
- None

### Notes
- Smooth rotation, no user impact
```

---

## 📊 Rotation Schedule Calendar

### Q1 2026
- Jan 15: TLS Certificate (90 days)
- Feb 10: JWT Secret (180 days)
- Mar 1: Service Account Keys (90 days)

### Q2 2026
- Apr 15: TLS Certificate (90 days)
- May 1: Redis Password (90 days)
- Jun 1: Service Account Keys (90 days)

### Q3 2026
- Jul 15: TLS Certificate (90 days)
- Aug 10: JWT Secret (180 days)
- Sep 1: Service Account Keys (90 days)

### Q4 2026
- Oct 15: TLS Certificate (90 days)
- Nov 1: Redis Password (90 days)
- Dec 1: Service Account Keys (90 days)
- Dec 15: OAuth Client Secret (Annual)

---

## 🔗 Related Documentation

- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [GKE Certificate Management](https://cloud.google.com/kubernetes-engine/docs/how-to/ingress-multi-ssl)
- [Service Account Key Management](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)

## 📞 Escalation

- **Rotation Issues**: SRE Lead
- **Certificate Expiry**: P1 Incident, escalate immediately
- **Auth Failures**: SRE Lead + Security Team

---

**Last Updated**: February 2026  
**Maintained By**: SRE Team  
**Review Frequency**: Quarterly
