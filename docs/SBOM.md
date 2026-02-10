# Software Bill of Materials (SBOM)

## 📋 Overview

This project automatically generates comprehensive Software Bill of Materials (SBOM) for all components using industry-standard formats to ensure software supply chain transparency and security compliance.

## 🎯 Purpose

SBOMs provide a complete inventory of software components, dependencies, and their relationships, enabling:
- **Security Analysis**: Identify vulnerable dependencies
- **License Compliance**: Track open-source license obligations
- **Supply Chain Security**: Meet regulatory requirements (EO 14028, NTIA)
- **Incident Response**: Quickly determine exposure to vulnerabilities

---

## 📦 SBOM Formats

We generate SBOMs in multiple industry-standard formats:

### 1. SPDX 2.3 (Software Package Data Exchange)
- **Format**: JSON
- **Standard**: ISO/IEC 5962:2021
- **Use Case**: License compliance, legal review
- **Files Generated**:
  - `backend-sbom.spdx.json` - Backend source dependencies
  - `backend-image-sbom.spdx.json` - Backend container image
  - `frontend-image-sbom.spdx.json` - Frontend container image

### 2. CycloneDX 1.5
- **Format**: JSON
- **Standard**: OWASP CycloneDX
- **Use Case**: Vulnerability management, DevSecOps
- **Files Generated**:
  - `backend-sbom.cdx.json` - Backend source dependencies
  - `backend-image-sbom.cdx.json` - Backend container
  - `frontend-deps-sbom.cdx.json` - Frontend npm dependencies
  - `frontend-image-sbom.cdx.json` - Frontend container

---

## 🔧 Generation Tools

### Backend (Python)
- **Tool**: [Syft](https://github.com/anchore/syft) by Anchore
- **Scope**: Python packages, system packages, Docker image layers
- **Output**: SPDX + CycloneDX

### Frontend (Node.js)
- **Tool**: [@cyclonedx/cyclonedx-npm](https://github.com/CycloneDX/cyclonedx-node-npm)
- **Scope**: npm packages (production + dev dependencies)
- **Output**: CycloneDX

### Container Images
- **Tool**: [Syft](https://github.com/anchore/syft)
- **Scope**: OS packages, application dependencies, image layers
- **Output**: SPDX + CycloneDX

---

## 🚀 Automatic Generation

SBOMs are automatically generated during every CI/CD build:

### CI/CD Pipeline Steps

1. **Backend Source SBOM** (after backend build)
   ```bash
   syft dir:. -o spdx-json=backend-sbom.spdx.json
   syft dir:. -o cyclonedx-json=backend-sbom.cdx.json
   ```

2. **Backend Container SBOM** (after Docker build)
   ```bash
   syft ${BACKEND_IMAGE} -o spdx-json=backend-image-sbom.spdx.json
   ```

3. **Frontend Dependencies SBOM** (after npm install)
   ```bash
   cd frontend
   cyclonedx-npm --output-file frontend-deps-sbom.cdx.json
   ```

4. **Frontend Container SBOM** (after frontend build)
   ```bash
   syft dir:frontend -o spdx-json=frontend-image-sbom.spdx.json
   ```

5. **Upload to Cloud Storage**
   ```bash
   gsutil cp sbom-artifacts/* gs://[PROJECT_ID]-sbom/[BUILD_ID]/
   ```

---

## 📂 Storage Structure

SBOMs are stored in Google Cloud Storage with the following structure:

```
gs://btoproject-486405-486604-sbom/
├── [BUILD_ID]/
│   ├── backend-sbom.spdx.json
│   ├── backend-sbom.cdx.json
│   ├── backend-image-sbom.spdx.json
│   ├── backend-image-sbom.cdx.json
│   ├── frontend-deps-sbom.cdx.json
│   ├── frontend-image-sbom.spdx.json
│   ├── frontend-image-sbom.cdx.json
│   └── metadata.json
```

### Metadata File

Each build includes a `metadata.json` file with build context:

```json
{
  "build_id": "12345678-abcd-1234-abcd-123456789abc",
  "commit_sha": "a1b2c3d4e5f6...",
  "short_sha": "a1b2c3d",
  "timestamp": "2026-02-10T14:30:00Z",
  "project_id": "btoproject-486405-486604",
  "backend_image": "us-central1-docker.pkg.dev/.../backend:a1b2c3d",
  "frontend_image": "us-central1-docker.pkg.dev/.../frontend:a1b2c3d"
}
```

---

## 🔍 Manual SBOM Generation

### Backend (Local)

```bash
# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Generate SBOM
syft dir:. -o spdx-json=backend-sbom.spdx.json
syft dir:. -o cyclonedx-json=backend-sbom.cdx.json

# Generate from Docker image
docker build -t backend:local .
syft backend:local -o spdx-json=backend-image-sbom.spdx.json
```

### Frontend (Local)

```bash
# Install CycloneDX npm
npm install -g @cyclonedx/cyclonedx-npm

# Generate SBOM
cd frontend
cyclonedx-npm --output-file sbom.json
```

---

## 📊 SBOM Analysis

### View SBOM Contents

```bash
# Download SBOM from GCS
gsutil cp gs://btoproject-486405-486604-sbom/[BUILD_ID]/backend-sbom.spdx.json .

# View with jq
cat backend-sbom.spdx.json | jq '.packages[] | {name: .name, version: .versionInfo}'

# Count packages
cat backend-sbom.spdx.json | jq '.packages | length'
```

### Vulnerability Scanning with Grype

```bash
# Install Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Scan SBOM for vulnerabilities
grype sbom:backend-sbom.spdx.json

# Filter by severity
grype sbom:backend-sbom.spdx.json --severity critical,high
```

### Import into Dependency-Track

1. Deploy Dependency-Track:
   ```bash
   docker run -d -p 8080:8080 dependencytrack/bundled
   ```

2. Upload SBOM via UI:
   - Navigate to http://localhost:8080
   - Create new project
   - Upload `backend-sbom.cdx.json` or `frontend-deps-sbom.cdx.json`

3. View vulnerabilities, license compliance, and policy violations

---

## 🔐 Security & Compliance

### NTIA Minimum Elements

Our SBOMs meet NTIA minimum elements requirements:
- ✅ Supplier Name
- ✅ Component Name
- ✅ Version of Component
- ✅ Other Unique Identifiers (Package URLs, CPEs)
- ✅ Dependency Relationships
- ✅ Author of SBOM Data
- ✅ Timestamp

### Executive Order 14028 (Software Supply Chain Security)

- ✅ Automatic SBOM generation
- ✅ SBOM included with software artifacts
- ✅ Machine-readable format (SPDX, CycloneDX)
- ✅ Accessible to authorized users

### Standards Compliance

- ✅ **SPDX 2.3**: ISO/IEC 5962:2021
- ✅ **CycloneDX 1.5**: OWASP standard
- ✅ **NTIA Guidelines**: Minimum elements
- ✅ **CISA**: Software supply chain guidance

---

## 📋 SBOM Retention Policy

| SBOM Type | Retention Period | Storage Tier |
|-----------|-----------------|--------------|
| **Production Releases** | 2 years | Standard |
| **Development Builds** | 90 days | Standard |
| **Failed Builds** | 30 days | Nearline |
| **Archived Versions** | 7 years | Archive |

### Lifecycle Management

```bash
# Set lifecycle policy on GCS bucket
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["dev/", "test/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://btoproject-486405-486604-sbom
```

---

## 🔄 SBOM Verification

### Verify SBOM Generation in CI/CD

```bash
# Check if SBOM was generated in recent build
BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)")
gsutil ls gs://btoproject-486405-486604-sbom/${BUILD_ID}/

# Expected output:
# gs://btoproject-486405-486604-sbom/[BUILD_ID]/backend-sbom.spdx.json
# gs://btoproject-486405-486604-sbom/[BUILD_ID]/backend-sbom.cdx.json
# ...
```

### Validate SBOM Format

```bash
# Validate SPDX SBOM
curl -sS https://tools.spdx.org/app/validate/ \
  -F file=@backend-sbom.spdx.json

# Validate CycloneDX SBOM
docker run --rm -v $(pwd):/sbom cyclonedx/cyclonedx-cli validate \
  --input-file /sbom/backend-sbom.cdx.json
```

---

## 🛠️ Integration with Tools

### Dependency-Track
```bash
# API upload to Dependency-Track
curl -X "POST" "http://dtrack.company.com/api/v1/bom" \
  -H "X-Api-Key: ${API_KEY}" \
  -H "Content-Type: multipart/form-data" \
  -F "project=${PROJECT_UUID}" \
  -F "bom=@backend-sbom.cdx.json"
```

### GUAC (Graph for Understanding Artifact Composition)
```bash
# Ingest SBOM into GUAC
guac-ingest sbom backend-sbom.spdx.json
```

### Trivy
```bash
# Scan SBOM with Trivy
trivy sbom backend-sbom.spdx.json
```

---

## 📝 Best Practices

1. **Generate at Build Time**: Always generate fresh SBOMs during CI/CD
2. **Store with Artifacts**: Keep SBOMs alongside container images
3. **Version Control**: Track SBOM changes over time
4. **Automate Scanning**: Continuously scan SBOMs for vulnerabilities
5. **Audit Trail**: Maintain metadata about SBOM generation
6. **Access Control**: Limit access to production SBOMs
7. **Regular Review**: Review dependencies quarterly

---

## 🔗 Related Documentation

- [CI/CD Pipeline](../ci/cloudbuild-gke.yaml)
- [Security Documentation](../README.md#-security)
- [SRE Runbook](SRE_RUNBOOK.md)

### External Resources
- [SPDX Specification](https://spdx.github.io/spdx-spec/)
- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [NTIA SBOM Minimum Elements](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom)
- [Syft Documentation](https://github.com/anchore/syft)
- [Grype Documentation](https://github.com/anchore/grype)

---

## 📞 Support

For SBOM-related questions:
- **Security Team**: security@yourcompany.com
- **DevSecOps Team**: devsecops@yourcompany.com
- **Compliance Team**: compliance@yourcompany.com

---

**Last Updated**: February 10, 2026  
**Maintained By**: DevSecOps & Security Team  
**Version**: 1.0.0
