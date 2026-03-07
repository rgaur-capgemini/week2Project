# Week 3 Compliance Features - Quick Start Guide

## Prerequisites
- Week 1 & 2 implementation running successfully
- GCP project configured with existing services
- Python 3.11+ and Node.js 18+ installed
- SendGrid account (optional, for email notifications)

## Step 1: Install Dependencies

### Backend
```bash
# Add SendGrid for email notifications
pip install sendgrid==6.11.0

# Or reinstall all dependencies
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
# No new dependencies needed - uses existing Angular Material
```

## Step 2: Configure Environment Variables

Add to your environment (`.env` file or shell):

```bash
# Email Notifications (Optional)
export SENDGRID_API_KEY="SG.your-api-key"
export FROM_EMAIL="noreply@yourdomain.com"

# Already configured from Week 1/2
export PROJECT_ID="btoproject-486405"
export REGION="us-central1"
export VERTEX_INDEX_ID="5347067982386298880"
export VERTEX_INDEX_ENDPOINT="332186652006940672"
export DEPLOYED_INDEX_ID="rag_chatbot_deployed"
```

## Step 3: Create GCP Resources

### Create Pub/Sub Topic
```bash
gcloud pubsub topics create compliance-template-ingestion --project=btoproject-486405
```

### Create GCS Bucket for Templates
```bash
gsutil mb -l us-central1 gs://btoproject-486405-compliance-templates
```

### Create Firestore Collections
No action needed - collections are auto-created on first use:
- `compliance_reports`
- `compliance_templates`
- `compliance_template_chunks`

## Step 4: Run the Application

### Start Backend (Terminal 1)
```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend (Terminal 2)
```bash
cd frontend
ng serve --port 4200
```

### Access Application
Open browser: `http://localhost:4200`

## Step 5: Test Compliance Features

### 1. Login
- Use Google OAuth to sign in
- You'll be redirected to the chat interface

### 2. Navigate to Compliance
- Click **Compliance** in the navbar
- You'll see the compliance dashboard

### 3. Upload a Test Document

Create a test document `test-policy.txt`:
```text
Information Security Policy

1. Access Control
All systems must require authentication. Users must have unique credentials.
Strong passwords are required with minimum 12 characters.

2. Data Protection
All sensitive data must be encrypted at rest and in transit.
Regular backups must be performed weekly.

3. Incident Response
Security incidents must be reported within 24 hours.
An incident response team must be available 24/7.
```

Upload it:
- Click **Select Document** in the Compliance dashboard
- Choose `test-policy.txt`
- Optionally select a template type (e.g., "ISO27001")
- Click **Check Compliance**

### 4. View Report
- Wait 30-60 seconds for processing
- The page will show "Processing" status and auto-refresh
- Once complete, you'll see:
  - Compliance score (e.g., 75%)
  - Number of gaps found
  - Status: "completed"
- Click the **View** icon to see the full report

### 5. Explore Report Details
In the report viewer, you'll see:
- **Score Badge**: Color-coded compliance score
- **Recommendations**: Top 10 actionable recommendations
- **Identified Gaps**: Expandable list with severity levels
  - High (red)
  - Medium (yellow)
  - Low (green)
- **Full Report**: Detailed Markdown report
- **Download**: Save report as `.md` file

## Step 6: Upload a Compliance Template (Admin Only)

### Create a Test Template
Create `iso27001-template.txt`:
```text
ISO 27001 Information Security Management Requirements

A.9.1 Access Control
A.9.1.1 Access control policy shall be established and documented
A.9.1.2 Users shall only be provided access to services for which they are authorized

A.10.1 Cryptographic Controls
A.10.1.1 A policy on the use of cryptographic controls shall be developed
A.10.1.2 Key management shall be supported by appropriate procedures

A.16.1 Incident Management
A.16.1.1 Responsibilities and procedures shall be established for incident response
A.16.1.2 Information security events shall be reported through management channels
A.16.1.3 Information security weaknesses shall be reported
```

### Upload Template (Admin user required)
```bash
# Using curl (replace with your admin JWT token)
curl -X POST "http://localhost:8000/compliance/templates/upload" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -F "file=@iso27001-template.txt" \
  -F "template_type=ISO27001" \
  -F "version=1.0"
```

Or via the UI (if you add template upload component).

## Step 7: Deploy Cloud Function (Optional)

For production template processing via Pub/Sub:

```bash
cd cloud-functions/template-processor

gcloud functions deploy compliance-template-processor \
  --gen2 \
  --region=us-central1 \
  --runtime=python311 \
  --source=. \
  --entry-point=process_template \
  --trigger-topic=compliance-template-ingestion \
  --set-env-vars PROJECT_ID=btoproject-486405,REGION=us-central1,VERTEX_INDEX_ID=5347067982386298880,VERTEX_INDEX_ENDPOINT=332186652006940672,DEPLOYED_INDEX_ID=rag_chatbot_deployed \
  --service-account=template-processor-sa@btoproject-486405.iam.gserviceaccount.com \
  --memory=1Gi \
  --timeout=540s
```

### Test Cloud Function
```bash
# Publish test message
gcloud pubsub topics publish compliance-template-ingestion \
  --message='{"template_id":"test-123","bucket":"btoproject-486405-compliance-templates","blob_name":"templates/ISO27001/test.txt","template_type":"ISO27001","version":"1.0"}'

# Check logs
gcloud functions logs read compliance-template-processor --limit=20
```

## Troubleshooting

### Issue: "Module 'sendgrid' not found"
**Solution**: Install sendgrid package
```bash
pip install sendgrid==6.11.0
```

### Issue: Compliance link not showing in navbar
**Solution**: Clear browser cache and reload
```bash
# Or rebuild frontend
cd frontend
rm -rf dist/
ng build
ng serve
```

### Issue: Reports stuck in "processing"
**Solution**: Check backend logs
```bash
# Look for errors in the compliance workflow
tail -f logs/backend.log
```

Or check the terminal where backend is running.

### Issue: Templates not being found
**Solution**: 
1. Check if templates are in Firestore:
   ```bash
   # Via GCP Console
   https://console.cloud.google.com/firestore/data
   ```
2. Verify vector search index is populated
3. Try uploading a new template

### Issue: Email notifications not sending
**Solution**:
1. Verify `SENDGRID_API_KEY` is set correctly
2. Check SendGrid dashboard for API key status
3. Email is optional - system works without it

### Issue: Permission denied on endpoints
**Solution**: 
1. Verify JWT token is valid
2. Check user role has required permission:
   - `DOCUMENT_UPLOAD` for document upload
   - `ADMIN_MANAGE_SYSTEM` for template upload

## Testing with Sample Data

### Sample Document for Testing
Save as `sample-security-policy.txt`:
```text
Company XYZ Security Policy

Access Management
- All employees must use multi-factor authentication
- Passwords must be at least 10 characters
- Access reviews are conducted quarterly

Data Protection
- Customer data is encrypted using AES-256
- Data backups are performed daily
- Data retention policy: 7 years

Incident Response
- Security team monitors systems 24/7
- Incidents are logged in ticketing system
- Post-incident reviews are conducted

Physical Security
- Badge access required for office entry
- Visitors must sign in and be escorted
- Security cameras monitor all entrances
```

This will generate:
- **Compliance Score**: ~70-80%
- **Gaps**: Missing items like:
  - Specific incident response timeframes
  - Encryption in transit
  - Key management procedures
  - Detailed access control policy
- **Recommendations**: Actionable steps to address gaps

## Monitoring

### Check Application Health
```bash
# Backend health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/readiness
```

### View Logs
```bash
# Backend logs (if using systemd or docker)
journalctl -u rag-backend -f

# Or check terminal output where uvicorn is running
```

### Check Database
```bash
# List Firestore collections
gcloud firestore collections list --project=btoproject-486405

# List documents in compliance_reports collection
gcloud firestore documents list compliance_reports --project=btoproject-486405
```

## Next Steps

1. **Add More Templates**: Upload templates for different compliance frameworks (GDPR, HIPAA, SOC2)
2. **Customize Matching**: Adjust similarity threshold in `TemplateMatcher` if needed
3. **Email Configuration**: Set up SendGrid for production email notifications
4. **Deploy to GKE**: Follow deployment steps in WEEK3_IMPLEMENTATION.md
5. **Create Custom Templates**: Tailor templates to your organization's specific requirements

## API Reference

### Quick API Examples

#### Upload Document
```bash
curl -X POST http://localhost:8000/compliance/documents/upload \
  -H "Authorization: Bearer YOUR_JWT" \
  -F "file=@document.pdf" \
  -F "template_type=ISO27001"
```

#### Get Report
```bash
curl http://localhost:8000/compliance/reports/REPORT_ID \
  -H "Authorization: Bearer YOUR_JWT"
```

#### List All Reports
```bash
curl http://localhost:8000/compliance/reports \
  -H "Authorization: Bearer YOUR_JWT"
```

#### Delete Report
```bash
curl -X DELETE http://localhost:8000/compliance/reports/REPORT_ID \
  -H "Authorization: Bearer YOUR_JWT"
```

## Support

- **Documentation**: See `WEEK3_IMPLEMENTATION.md` for comprehensive guide
- **Issues**: Check backend logs and Firestore for error messages
- **Questions**: Review troubleshooting section above

---

🎉 **You're all set!** Start checking document compliance and generating reports.
