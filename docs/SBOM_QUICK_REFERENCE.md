# SBOM Quick Reference Guide

## 🚀 Quick Start

### View Latest SBOM

```bash
# Get latest build ID
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)")

# List all SBOMs for the build
gsutil ls gs://btoproject-486405-486604-sbom/${BUILD_ID}/

# Download backend SBOM (SPDX format)
gsutil cp gs://btoproject-486405-486604-sbom/${BUILD_ID}/backend-sbom.spdx.json .

# Download frontend SBOM (CycloneDX format)
gsutil cp gs://btoproject-486405-486604-sbom/${BUILD_ID}/frontend-deps-sbom.cdx.json .
```

---

## 📊 Common Commands

### List All Dependencies

```bash
# Backend dependencies (from SPDX)
cat backend-sbom.spdx.json | jq -r '.packages[] | "\(.name) \(.versionInfo)"' | sort

# Frontend dependencies (from CycloneDX)
cat frontend-deps-sbom.cdx.json | jq -r '.components[] | "\(.name) \(.version)"' | sort
```

### Count Packages

```bash
# Count backend packages
cat backend-sbom.spdx.json | jq '.packages | length'

# Count frontend packages
cat frontend-deps-sbom.cdx.json | jq '.components | length'
```

### Find Specific Package

```bash
# Search for a package in backend SBOM
cat backend-sbom.spdx.json | jq '.packages[] | select(.name | contains("fastapi"))'

# Search for a package in frontend SBOM
cat frontend-deps-sbom.cdx.json | jq '.components[] | select(.name | contains("angular"))'
```

---

## 🔍 Vulnerability Scanning

### Scan with Grype

```bash
# Install Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Scan backend SBOM
grype sbom:backend-sbom.spdx.json

# Scan with severity filter
grype sbom:backend-sbom.spdx.json --severity critical,high

# Output as JSON
grype sbom:backend-sbom.spdx.json -o json > vulnerabilities.json
```

### Scan with Trivy

```bash
# Scan SBOM with Trivy
trivy sbom backend-sbom.spdx.json

# Filter by severity
trivy sbom backend-sbom.spdx.json --severity HIGH,CRITICAL
```

---

## 📈 CI/CD Integration

### Trigger Build with SBOM Generation

```bash
# Submit build to Cloud Build
gcloud builds submit --config=ci/cloudbuild-gke.yaml

# Monitor build
gcloud builds log --stream

# Verify SBOM was generated
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)")
gsutil ls gs://btoproject-486405-486604-sbom/${BUILD_ID}/
```

### View SBOM Metadata

```bash
# Download metadata
gsutil cp gs://btoproject-486405-486604-sbom/${BUILD_ID}/metadata.json .

# View metadata
cat metadata.json | jq .
```

---

## 🔄 SBOM Comparison

### Compare Two Builds

```bash
# Get two build IDs
BUILD1="abc123"
BUILD2="def456"

# Download SBOMs
gsutil cp gs://btoproject-486405-486604-sbom/${BUILD1}/backend-sbom.spdx.json ./sbom1.json
gsutil cp gs://btoproject-486405-486604-sbom/${BUILD2}/backend-sbom.spdx.json ./sbom2.json

# Extract package lists
jq -r '.packages[] | "\(.name)@\(.versionInfo)"' sbom1.json | sort > packages1.txt
jq -r '.packages[] | "\(.name)@\(.versionInfo)"' sbom2.json | sort > packages2.txt

# Show differences
diff packages1.txt packages2.txt
```

---

## 📦 License Compliance

### Extract License Information

```bash
# List all licenses (SPDX)
cat backend-sbom.spdx.json | jq -r '.packages[] | "\(.name): \(.licenseConcluded)"' | grep -v NOASSERTION

# Count licenses
cat backend-sbom.spdx.json | jq -r '.packages[].licenseConcluded' | sort | uniq -c | sort -rn

# Find specific license
cat backend-sbom.spdx.json | jq '.packages[] | select(.licenseConcluded | contains("MIT"))'
```

---

## 🗂️ SBOM Management

### List All SBOMs

```bash
# List all builds with SBOMs
gsutil ls gs://btoproject-486405-486604-sbom/

# List SBOMs from last week
gsutil ls -l gs://btoproject-486405-486604-sbom/** | grep "$(date -d '7 days ago' +%Y-%m)"
```

### Download All SBOMs for a Build

```bash
# Download all SBOMs for specific build
BUILD_ID="your-build-id"
mkdir -p sbom-${BUILD_ID}
gsutil -m cp -r gs://btoproject-486405-486604-sbom/${BUILD_ID}/* sbom-${BUILD_ID}/
```

### Clean Up Old SBOMs

```bash
# List SBOMs older than 90 days
gsutil ls -l gs://btoproject-486405-486604-sbom/** | awk '{if ($2 < (systime() - 7776000)) print $3}'

# Delete old SBOMs (use with caution!)
# gsutil -m rm -r gs://btoproject-486405-486604-sbom/[OLD_BUILD_ID]/
```

---

## 🔗 Integration Examples

### Upload to Dependency-Track

```bash
# Set variables
DTRACK_URL="http://localhost:8080"
DTRACK_API_KEY="your-api-key"
PROJECT_UUID="your-project-uuid"

# Upload SBOM
curl -X "POST" "${DTRACK_URL}/api/v1/bom" \
  -H "X-Api-Key: ${DTRACK_API_KEY}" \
  -H "Content-Type: multipart/form-data" \
  -F "project=${PROJECT_UUID}" \
  -F "bom=@backend-sbom.cdx.json"
```

### Export to CSV

```bash
# Convert SBOM to CSV
cat backend-sbom.spdx.json | jq -r '.packages[] | [.name, .versionInfo, .licenseConcluded] | @csv' > sbom.csv

# Add header
echo "Package,Version,License" | cat - sbom.csv > sbom-with-header.csv
```

---

## 🛡️ Security Best Practices

1. **Regular Scanning**: Scan SBOMs weekly for new vulnerabilities
2. **Version Tracking**: Compare SBOMs between releases
3. **License Review**: Audit licenses before major releases
4. **Access Control**: Limit access to production SBOMs
5. **Retention**: Keep SBOMs for regulatory compliance (2+ years)

---

## 📞 Troubleshooting

### SBOM Not Found

```bash
# Check if build completed successfully
gcloud builds list --limit=5

# Check if SBOM bucket exists
gsutil ls gs://btoproject-486405-486604-sbom/

# Create bucket if missing
gsutil mb gs://btoproject-486405-486604-sbom/
```

### Invalid SBOM Format

```bash
# Validate SPDX SBOM
jq empty backend-sbom.spdx.json

# Validate CycloneDX SBOM
docker run --rm -v $(pwd):/sbom cyclonedx/cyclonedx-cli validate \
  --input-file /sbom/backend-sbom.cdx.json
```

### Missing Dependencies

```bash
# Regenerate SBOM locally
syft dir:. -o spdx-json=backend-sbom-new.spdx.json

# Compare with CI-generated SBOM
diff <(jq -S . backend-sbom.spdx.json) <(jq -S . backend-sbom-new.spdx.json)
```

---

**For detailed documentation, see [SBOM.md](SBOM.md)**

*Last Updated: February 10, 2026*
