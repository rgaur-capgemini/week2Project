# Email Notification Setup Guide

## Overview
Email notifications are sent when compliance reports are completed, informing users about:
- Compliance score
- Number of identified gaps
- Direct link to view the full report
- Detailed recommendations

## Email Service Configuration

### Prerequisites
1. **SendGrid Account**: Sign up at https://sendgrid.com/
2. **API Key**: Generate an API key with "Mail Send" permission
3. **Verified Sender**: Verify your sender email address in SendGrid

### Setup Steps

#### 1. Get SendGrid API Key
```bash
# Login to SendGrid dashboard
# Navigate to: Settings > API Keys
# Create API Key with "Mail Send" permission
# Copy the API key (starts with "SG.")
```

#### 2. Store API Key in GCP Secret Manager
```bash
# In Cloud Shell:
PROJECT_ID="btoproject-486405-486604"

# Create secret
gcloud secrets create sendgrid-api-key \
  --replication-policy="automatic" \
  --project=${PROJECT_ID}

# Add the API key value
echo -n "YOUR_SENDGRID_API_KEY" | gcloud secrets versions add sendgrid-api-key \
  --data-file=- \
  --project=${PROJECT_ID}

# Grant access to service account
gcloud secrets add-iam-policy-binding sendgrid-api-key \
  --member="serviceAccount:chatbot-rag-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=${PROJECT_ID}
```

#### 3. Create Kubernetes Secret
```bash
# Get the API key from Secret Manager
API_KEY=$(gcloud secrets versions access latest --secret="sendgrid-api-key" --project=${PROJECT_ID})

# Create Kubernetes secret
kubectl create secret generic sendgrid-secret \
  --from-literal=api-key="${API_KEY}" \
  --namespace=default

# Verify secret created
kubectl get secret sendgrid-secret -o yaml
```

#### 4. Update FROM_EMAIL in ConfigMap
```bash
# Edit k8s/configmap.yaml
# Update FROM_EMAIL to your verified sender email:
# FROM_EMAIL: "noreply@yourdomain.com"

# Apply the updated configmap
kubectl apply -f k8s/configmap.yaml
```

#### 5. Deploy Updated Backend
```bash
# Commit changes
git add k8s/backend-deployment.yaml k8s/configmap.yaml
git commit -m "Add email notification configuration"
git push origin develop

# Trigger Cloud Build (if not automatic)
gcloud builds submit --config=ci/cloudbuild-gke.yaml --project=${PROJECT_ID}

# Or restart existing deployment
kubectl rollout restart deployment rag-backend
```

### Verification

#### Check Email Service Logs
```bash
# Check if email service initialized
kubectl logs -l app=rag-backend --tail=100 | grep -i "emailservice\|sendgrid"

# Expected output:
# EmailService initialized with from_email=noreply@yourdomain.com
```

#### Test Email Notification
```bash
# Upload a document via the API
TOKEN="your-jwt-token"

curl -X POST "http://34.28.73.87/compliance/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-document.txt" \
  -F "template_type=ISO27001"

# Check backend logs for email sending
kubectl logs -l app=rag-backend --tail=50 | grep -i "email\|notification"

# Expected output:
# Sending compliance report email to user@example.com
# Email sent successfully to user@example.com
```

#### Check Your Email Inbox
- You should receive an email with subject: "Compliance Report Ready - X% (status)"
- Email contains:
  - Compliance score
  - Number of gaps
  - Link to view report
  - Detailed breakdown

### Email Template

The email includes:
```
✓ Compliance Report Ready

Hello [User Name],

Your compliance analysis has been completed. Here are the results:

Document ID: xxx-xxx-xxx
Report ID: xxx-xxx-xxx
Compliance Score: 85.5% (Good)
Identified Gaps: 3

[View Full Report Button]

The report includes:
- Detailed compliance analysis
- Identified gaps and deficiencies
- Actionable recommendations
- Section-by-section breakdown
```

### Troubleshooting

#### Email Not Received
```bash
# 1. Check if SENDGRID_API_KEY is set
kubectl exec -it $(kubectl get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}') \
  -- env | grep SENDGRID

# 2. Check backend logs for errors
kubectl logs -l app=rag-backend --tail=200 | grep -i "email\|sendgrid"

# 3. Verify secret exists
kubectl get secret sendgrid-secret -o yaml

# 4. Check SendGrid dashboard for delivery status
# Login to SendGrid > Activity > Delivery
```

#### "SendGrid SDK not available"
```bash
# Check if sendgrid package is installed
kubectl exec -it $(kubectl get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}') \
  -- pip list | grep sendgrid

# Should show: sendgrid==6.11.0
# If missing, rebuild image with updated requirements.txt
```

#### "SendGrid API key not configured"
```bash
# Secret not mounted or ENV not set
# Check deployment for SENDGRID_API_KEY env var
kubectl describe deployment rag-backend | grep -A 5 SENDGRID

# Recreate secret if needed
kubectl delete secret sendgrid-secret
kubectl create secret generic sendgrid-secret --from-literal=api-key="SG.xxx"
kubectl rollout restart deployment rag-backend
```

#### Emails Go to Spam
1. **Verify Sender Identity** in SendGrid dashboard
2. **Set up Domain Authentication** (SPF/DKIM)
3. **Use a verified domain** instead of generic email
4. **Check email content** - avoid spam trigger words

### Cost Considerations

**SendGrid Pricing (as of 2024):**
- Free Tier: 100 emails/day forever
- Essentials: $19.95/month for 50,000 emails
- Pro: $89.95/month for 100,000 emails

**Recommendations:**
- Use free tier for development/testing
- Upgrade to paid plan for production use
- Monitor email volume in SendGrid dashboard
- Set up alerts for quota limits

### Security Best Practices

1. **Never commit API keys** to Git
2. **Use Secret Manager** for sensitive values
3. **Rotate API keys** regularly (every 90 days)
4. **Restrict API key permissions** to "Mail Send" only
5. **Monitor SendGrid activity** for suspicious usage
6. **Use verified sender domains** to prevent phishing

### Alternative Email Providers

If not using SendGrid, update `app/notifications/email_service.py`:

#### Gmail (for development only)
```python
# Not recommended for production
# Requires app-specific password
```

#### Amazon SES
```python
# Install boto3
# Use AWS SES API instead of SendGrid
```

#### Google Workspace / Gmail API
```python
# Use google-api-python-client
# Requires OAuth2 setup
```

### Email Notification Flow

```
User uploads document
    ↓
Document chunked & analyzed
    ↓
Compliance report generated
    ↓
Report saved to Firestore
    ↓
Background task triggers email notification
    ↓
EmailService sends email via SendGrid
    ↓
User receives email with report link
```

### Configuration Summary

**Files Modified:**
- `k8s/backend-deployment.yaml` - Added SENDGRID_API_KEY and FROM_EMAIL env vars
- `k8s/configmap.yaml` - Added FROM_EMAIL configuration
- `app/compliance_routes.py` - Updated report_url to actual frontend URL
- `requirements.txt` - SendGrid already included

**GCP Resources:**
- Secret Manager: `sendgrid-api-key` secret
- Kubernetes Secret: `sendgrid-secret`
- ConfigMap: `rag-config` with FROM_EMAIL

**Environment Variables:**
- `SENDGRID_API_KEY` - API key from Secret Manager
- `FROM_EMAIL` - Sender email address (from ConfigMap)

## Testing Checklist

- [ ] SendGrid account created
- [ ] API key generated and verified
- [ ] Sender email verified in SendGrid
- [ ] Secret created in GCP Secret Manager
- [ ] Kubernetes secret created
- [ ] ConfigMap updated with FROM_EMAIL
- [ ] Backend deployment updated
- [ ] Build triggered and deployed
- [ ] Email service initialized (check logs)
- [ ] Test document uploaded
- [ ] Email notification received
- [ ] Email contains correct report URL
- [ ] Link in email works

## Support

For issues with email notifications:
1. Check backend logs: `kubectl logs -l app=rag-backend --tail=200`
2. Verify SendGrid dashboard for delivery status
3. Check spam/junk folder
4. Verify sender email is verified in SendGrid
5. Test with different email addresses
