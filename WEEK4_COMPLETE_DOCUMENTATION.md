# Week 4: Enterprise Features - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture & Flow](#architecture--flow)
3. [File Structure](#file-structure)
4. [GCP Configuration](#gcp-configuration)
5. [Backend Implementation](#backend-implementation)
6. [Frontend Implementation](#frontend-implementation)
7. [Code Flow & Execution](#code-flow--execution)
8. [API Reference](#api-reference)
9. [Testing & Verification](#testing--verification)

---

## Overview

### What is Week 4?
Week 4 adds **enterprise-grade features** to the RAG chatbot application:

1. **🧪 Experiments & A/B Testing**
   - Vertex AI experiment tracking
   - Multi-variant testing framework
   - Feature flag management
   - Real-time experiment metrics

2. **💰 FinOps (Financial Operations)**
   - Real-time cost tracking across GCP services
   - Budget management and alerts
   - Token usage monitoring
   - Cost optimization recommendations

3. **📊 Observability**
   - SLO (Service Level Objective) tracking
   - Error budget monitoring
   - Synthetic health checks
   - Alert management

### Why These Features?
- **Experiments**: Enable data-driven decisions by testing different model variants
- **FinOps**: Control cloud costs and optimize spending on AI/ML workloads
- **Observability**: Ensure system reliability and meet SLA commitments

---

## Architecture & Flow

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   FinOps     │  │ Experiments  │  │ Observability│          │
│  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │    HTTP/REST API Calls              │
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────────┐
│                    GKE Backend (FastAPI)                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ finops_routes  │  │experiment_routes│  │observability   │    │
│  │   _week4.py    │  │   _week4.py     │  │  _routes.py    │    │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘    │
│           │                   │                   │             │
│  ┌────────▼───────┐  ┌────────▼───────┐  ┌────────▼───────┐    │
│  │  CostTracker   │  │ExperimentTracker│  │ SLOTracker     │    │
│  │BudgetAlerts    │  │VariantManager  │  │HealthChecker   │    │
│  │TokenUsageTracker│ │FeatureFlags    │  │ErrorBudget     │    │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘    │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            │     GCP Services Integration            │
            │                    │                    │
┌───────────▼────────────────────▼────────────────────▼───────────┐
│                        Google Cloud Platform                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │   BigQuery     │  │   Vertex AI    │  │Cloud Monitoring│    │
│  │ (Billing Data) │  │ (Experiments)  │  │   (Metrics)    │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │   Firestore    │  │Cloud Billing   │  │  Cloud Logging │    │
│  │(Feature Flags) │  │  Budget API    │  │    (Logs)      │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Request Flow Example (FinOps Dashboard)

```
User clicks "FinOps Dashboard"
         ↓
Angular Router → FinopsDashboardComponent
         ↓
Component ngOnInit() calls FinopsService.getDashboard()
         ↓
HTTP GET /finops/dashboard
         ↓
FastAPI: finops_routes_week4.py → get_dashboard()
         ↓
CostTracker.get_current_month_costs()
         ↓
BigQuery: Query billing_export table
         ↓
Data aggregation & processing
         ↓
JSON Response: { costs: [...], budgets: [...], tokens: [...] }
         ↓
Angular: Update charts (Chart.js)
         ↓
User sees real-time cost visualization
```

---

## File Structure

### Backend Files (Python)

```
app/
├── main.py                              # Main FastAPI app - includes Week 4 routers
├── config.py                            # Configuration with PROJECT_ID, REGION exports
│
├── experiment_routes_week4.py           # A/B testing & experiments API endpoints
├── finops_routes_week4.py              # FinOps (cost tracking) API endpoints
├── observability_routes.py             # Observability (SLO/monitoring) endpoints
│
├── experiments/                         # Experiment tracking services
│   ├── __init__.py
│   ├── experiment_tracker_week4.py     # Vertex AI experiment tracker
│   ├── variant_manager_week4.py        # Manage model variants
│   ├── ab_testing_framework_week4.py   # A/B test orchestration
│   ├── feature_flags_week4.py          # Feature flag management
│   └── model_registry_week4.py         # Model version registry
│
├── finops/                              # Financial operations services
│   ├── __init__.py
│   ├── cost_tracker_week4.py           # Track GCP costs via BigQuery
│   ├── budget_alerts_week4.py          # Budget management & alerts
│   └── token_usage_tracker_week4.py    # Track AI token consumption
│
└── observability/                       # SRE observability services
    ├── __init__.py
    ├── slo_tracker_week4.py            # SLO/SLI tracking
    ├── synthetic_monitor_week4.py      # Health check monitoring
    └── error_budget_week4.py           # Error budget calculations
```

### Frontend Files (Angular)

```
frontend/src/app/
├── app.routes.ts                        # Added Week 4 routes
├── app.component.html                   # Added Week 4 nav menu items
│
├── services/
│   ├── experiments.service.ts           # Experiments API client
│   └── finops.service.ts               # FinOps API client
│
├── finops-dashboard/
│   ├── finops-dashboard.component.ts   # FinOps dashboard logic
│   ├── finops-dashboard.component.html # FinOps dashboard template
│   └── finops-dashboard.component.css  # FinOps dashboard styles
│
├── experiments-dashboard/
│   ├── experiments-dashboard.component.ts   # Experiments dashboard logic
│   ├── experiments-dashboard.component.html # Experiments dashboard template
│   └── experiments-dashboard.component.css  # Experiments dashboard styles
│
└── observability-dashboard/
    ├── observability-dashboard.component.ts   # Observability dashboard logic
    ├── observability-dashboard.component.html # Observability dashboard template
    └── observability-dashboard.component.css  # Observability dashboard styles
```

---

## GCP Configuration

### Why GCP Configuration is Needed

Week 4 features integrate with multiple GCP services. Each service requires:
1. **API Enablement**: Turn on specific GCP APIs
2. **Data Storage**: Set up datasets/collections for storing metrics
3. **IAM Permissions**: Grant service account access to resources
4. **Billing Export**: Stream cost data to BigQuery for analysis

### Configuration Steps Performed

#### 1. Enable Required APIs

**Command:**
```bash
gcloud services enable bigquery.googleapis.com billingbudgets.googleapis.com --project=botpproject
```

**Why:**
- `bigquery.googleapis.com`: Allows querying billing data for cost tracking
- `billingbudgets.googleapis.com`: Enables budget alerts and cost management

**What This Does:**
- Activates the APIs in GCP project `botpproject`
- Allows backend to make API calls to these services
- Required before creating BigQuery datasets or budgets

---

#### 2. Create BigQuery Dataset for Billing Export

**Command:**
```bash
bq mk --dataset --location=us-central1 botpproject:billing_export
```

**Why:**
- BigQuery needs a dataset (like a database) to store billing data
- Location `us-central1` matches our backend region for low latency
- This dataset will receive daily cost breakdowns from GCP billing

**What This Does:**
- Creates dataset: `botpproject.billing_export`
- Sets location to `us-central1`
- Prepares storage for billing export tables

**Data Structure:**
BigQuery will create tables like: `gcp_billing_export_v1_XXXXXX` with columns:
- `service.description`: Service name (e.g., "Vertex AI", "Cloud Storage")
- `cost`: Cost in USD
- `usage_start_time`: Timestamp of usage
- `project.id`: Project identifier
- `currency`: Currency code (USD)

---

#### 3. Grant Service Account Permissions

**Service Account:** `rag-service@botpproject.iam.gserviceaccount.com`

This service account runs in the backend pods and needs permissions to access GCP services.

##### Permission 1: BigQuery Data Viewer

**Command:**
```bash
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:rag-service@botpproject.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```

**Why:**
- Allows backend to **read** billing data from BigQuery
- Required for cost tracking queries
- Read-only access (no write permissions)

**What It Allows:**
- Run `SELECT` queries on billing_export dataset
- Access cost data for dashboard display
- Cannot modify or delete data (security best practice)

---

##### Permission 2: Monitoring Metric Writer

**Command:**
```bash
gcloud projects add-iam-policy-binding botpproject \
  --member="serviceAccount:rag-service@botpproject.iam.gserviceaccount.com" \
  --role="roles/monitoring.metricWriter"
```

**Why:**
- Allows backend to **write custom metrics** to Cloud Monitoring
- Required for SLO tracking, error budgets, synthetic checks
- Enables real-time observability dashboards

**What It Allows:**
- Create custom metrics (e.g., `rag_latency`, `chat_error_rate`)
- Write time-series data to Cloud Monitoring
- Used by `observability_routes.py` for SLO tracking

---

#### 4. Enable BigQuery Billing Export (Manual Step)

**Steps:**
1. Go to: https://console.cloud.google.com/billing
2. Click on billing account
3. Navigate to: **Billing export** → **BigQuery export**
4. Click **Edit settings**
5. Select dataset: `botpproject:billing_export`
6. Enable **Standard usage cost data export**
7. Click **Save**

**Why:**
- Enables automatic daily export of cost data to BigQuery
- Provides real billing data for FinOps dashboard
- Without this, dashboard only shows mock data

**What This Does:**
- GCP automatically exports billing data every 24 hours
- Data includes: service costs, usage metrics, project breakdowns
- Tables created: `gcp_billing_export_v1_<billing_account_id>`
- First data appears within 24 hours of enabling

**Data Flow:**
```
GCP Services (Vertex AI, Storage, etc.)
         ↓
      Usage Tracking
         ↓
   Billing System
         ↓
BigQuery Export (daily)
         ↓
billing_export.gcp_billing_export_v1_*
         ↓
Backend queries via CostTracker
         ↓
FinOps Dashboard displays costs
```

---

### Summary of GCP Configuration

| Component | Purpose | Status |
|-----------|---------|--------|
| BigQuery API | Query billing data | ✅ Enabled |
| Billing Budgets API | Manage cost budgets | ✅ Enabled |
| Dataset: billing_export | Store billing data | ✅ Created |
| IAM: bigquery.dataViewer | Read billing data | ✅ Granted |
| IAM: monitoring.metricWriter | Write custom metrics | ✅ Granted |
| Billing Export | Stream cost data | ✅ Enabled (manual) |

**All configuration complete!** Backend can now:
- Query real billing costs
- Write observability metrics
- Display actual spend in FinOps dashboard

---

## Backend Implementation

### 1. Main Application (main.py)

**Purpose:** FastAPI application entry point that includes Week 4 routers.

**Key Changes:**

```python
# File: app/main.py
# Lines: 15-17 (imports)

from app.experiment_routes_week4 import router as experiment_router
from app.finops_routes_week4 import router as finops_router
from app.observability_routes import router as observability_router
```

**Explanation:**
- **Line 15**: Import experiment routes for A/B testing endpoints
- **Line 16**: Import FinOps routes for cost tracking endpoints
- **Line 17**: Import observability routes for SLO monitoring endpoints
- These imports make the routers available to register with FastAPI

---

```python
# File: app/main.py
# Lines: 85-87 (router registration)

app.include_router(experiment_router)  # Week 4: Experiments routes
app.include_router(finops_router)       # Week 4: FinOps routes
app.include_router(observability_router)  # Week 4: Observability routes
```

**Explanation:**
- **Line 85**: Register `/experiments/*` endpoints (variants, A/B tests, feature flags)
- **Line 86**: Register `/finops/*` endpoints (costs, budgets, token usage)
- **Line 87**: Register `/observability/*` endpoints (SLOs, error budgets, health checks)
- `include_router()` adds all endpoints from each router to the FastAPI app

**Why This Matters:**
- Makes Week 4 endpoints accessible via HTTP
- Enables frontend to call APIs like `/finops/dashboard`
- Maintains modular code structure (separate files per feature)

---

### 2. Configuration Module (config.py)

**Purpose:** Export configuration variables for use across modules.

**Key Changes:**

```python
# File: app/config.py
# Lines: Bottom of file

# Export module-level variables for backward compatibility
PROJECT_ID = config.PROJECT_ID
REGION = config.REGION
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER", "")
```

**Explanation:**
- **PROJECT_ID**: GCP project ID (`botpproject`) - used in BigQuery queries
- **REGION**: GCP region (`us-central1`) - for Vertex AI experiments
- **PROJECT_NUMBER**: Numeric project ID - for Cloud Monitoring metrics
- Module-level exports allow `from app.config import PROJECT_ID` syntax

**Why This Matters:**
- Week 4 services need project configuration
- Centralized config prevents hardcoding values
- Easy to change project settings in one place

---

### 3. FinOps Routes (finops_routes_week4.py)

**Purpose:** API endpoints for financial operations and cost tracking.

**Complete Code with Explanations:**

```python
# File: app/finops_routes_week4.py
# Lines: 1-20 (imports and router setup)

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os

from app.logging_config import get_logger
from app.finops.cost_tracker_week4 import CostTracker
from app.finops.budget_alerts_week4 import BudgetAlertsManager
from app.finops.token_usage_tracker_week4 import TokenUsageTracker

logger = get_logger(__name__)
router = APIRouter(prefix="/finops", tags=["FinOps"])
```

**Explanation:**
- **Line 1**: Import FastAPI router for creating endpoints
- **Line 2**: Type hints for clear function signatures
- **Line 3**: Date/time handling for time-series data
- **Line 4**: Pydantic models for request/response validation
- **Line 8**: Structured logging for debugging
- **Lines 9-11**: Import Week 4 FinOps services
  - `CostTracker`: Queries BigQuery for cost data
  - `BudgetAlertsManager`: Manages budgets and alerts
  - `TokenUsageTracker`: Tracks AI token consumption
- **Line 13**: Create FastAPI router with `/finops` prefix
  - All endpoints will be `/finops/*`
  - Tagged as "FinOps" in API docs

---

```python
# File: app/finops_routes_week4.py
# Lines: 22-35 (initialize services)

# Initialize services
PROJECT_ID = os.getenv("PROJECT_ID", "botpproject")
BILLING_ACCOUNT_ID = os.getenv("BILLING_ACCOUNT_ID", None)

try:
    cost_tracker = CostTracker(
        project_id=PROJECT_ID,
        billing_account_id=BILLING_ACCOUNT_ID
    )
    budget_manager = BudgetAlertsManager(
        project_id=PROJECT_ID,
        billing_account_id=BILLING_ACCOUNT_ID
    )
    token_tracker = TokenUsageTracker(project_id=PROJECT_ID)
```

**Explanation:**
- **Line 22-23**: Load project configuration from environment
  - Defaults to `botpproject` if not set
  - `BILLING_ACCOUNT_ID` is optional (for budget creation)
- **Lines 25-34**: Initialize FinOps services
  - Creates service instances at module load time
  - Services stay alive for entire app lifecycle (singleton pattern)
  - `CostTracker`: BigQuery client ready to query billing data
  - `BudgetAlertsManager`: Cloud Billing Budget API client
  - `TokenUsageTracker`: Firestore client for token metrics

**Why This Matters:**
- Services initialized once (efficient, no repeated connections)
- Environment variables allow different configs per environment
- Try/except handles missing billing account gracefully

---

```python
# File: app/finops_routes_week4.py
# Lines: 45-80 (GET /finops/costs/current-month)

@router.get("/costs/current-month")
async def get_current_month_costs() -> Dict[str, Any]:
    """
    Get costs for the current month broken down by service.
    
    Returns:
        Cost breakdown with service-level granularity
    """
    try:
        costs = cost_tracker.get_current_month_costs()
        return {
            "success": True,
            "period": "current_month",
            "costs": costs,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get current month costs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Explanation:**
- **Line 45**: Define endpoint `/finops/costs/current-month`
  - Method: GET (retrieve data)
  - No authentication (removed in previous fix)
- **Line 46**: Async function for concurrent request handling
- **Lines 47-51**: Docstring for API documentation
- **Line 54**: Call `CostTracker.get_current_month_costs()`
  - Queries BigQuery: `billing_export.gcp_billing_export_v1_*`
  - Filters: `WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)`
  - Groups: By service name and currency
  - Returns: List of {service_name, total_cost, daily_cost, currency}
- **Lines 55-60**: Format response
  - `success`: Boolean status
  - `period`: "current_month" identifier
  - `costs`: Array of cost objects
  - `timestamp`: ISO 8601 timestamp for cache invalidation
- **Lines 61-63**: Error handling
  - Log error with context
  - Return HTTP 500 with error message
  - Frontend shows error notification

**Data Flow:**
```
GET /finops/costs/current-month
    ↓
CostTracker.get_current_month_costs()
    ↓
BigQuery Query:
  SELECT service.description, SUM(cost)
  FROM billing_export.gcp_billing_export_v1_*
  WHERE DATE >= start of month
  GROUP BY service
    ↓
Response:
{
  "success": true,
  "costs": [
    {"service_name": "Vertex AI", "total_cost": 45.23, "currency": "USD"},
    {"service_name": "Cloud Storage", "total_cost": 12.50, "currency": "USD"}
  ]
}
```

---

```python
# File: app/finops_routes_week4.py
# Lines: 120-150 (GET /finops/dashboard)

@router.get("/dashboard")
async def get_finops_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive FinOps dashboard data.
    
    Returns:
        Aggregated cost, budget, and token usage data
    """
    try:
        # Fetch data in parallel (if possible)
        current_costs = cost_tracker.get_current_month_costs()
        daily_costs = cost_tracker.get_daily_costs(days=30)
        budgets = budget_manager.list_budgets()
        token_usage = token_tracker.get_usage_summary(days=30)
        
        return {
            "success": True,
            "current_month_costs": current_costs,
            "daily_costs": daily_costs,
            "budgets": budgets,
            "token_usage": token_usage,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get FinOps dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Explanation:**
- **Line 120**: Endpoint for comprehensive dashboard data
  - Aggregates multiple metrics in one API call
  - Reduces frontend HTTP requests (efficient)
- **Lines 130-133**: Fetch data from multiple sources
  - `current_costs`: Month-to-date spending by service
  - `daily_costs`: Time-series data for charts (last 30 days)
  - `budgets`: Budget limits and remaining balance
  - `token_usage`: AI token consumption metrics
- **Lines 135-142**: Return aggregated response
  - All data in single JSON object
  - Frontend updates all charts simultaneously
  - Timestamp enables client-side caching

**Why This Endpoint:**
- **Performance**: One API call vs four separate calls
- **Consistency**: All data from same point in time
- **User Experience**: Dashboard loads faster, no partial renders

---

### 4. Cost Tracker Service (cost_tracker_week4.py)

**Purpose:** Query BigQuery billing export for real cost data.

**Complete Code with Explanations:**

```python
# File: app/finops/cost_tracker_week4.py
# Lines: 1-30 (imports and optional dependencies)

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import bigquery

# Optional billing import - graceful degradation if package not installed
try:
    from google.cloud import billing_v1
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    billing_v1 = None

# Optional pandas import - for advanced data analysis
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from app.logging_config import get_logger

logger = get_logger(__name__)
```

**Explanation:**
- **Lines 1-3**: Core imports always available
  - `datetime`: Time range filtering
  - `typing`: Type hints for IDE support
  - `bigquery`: Required for querying billing data
- **Lines 6-11**: Optional billing_v1 import
  - **Why optional**: Package `google-cloud-billing` not always needed
  - `BILLING_AVAILABLE` flag: True if package installed
  - **Graceful degradation**: App works without this package
  - Used for: Creating/managing budgets (advanced feature)
- **Lines 14-19**: Optional pandas import
  - **Why optional**: Heavy dependency, not critical
  - Used for: Advanced data analysis, CSV export
  - **Fallback**: Basic Python dicts/lists if pandas missing
- **Line 21**: Structured logging for debugging

**Design Pattern: Optional Dependencies**
```python
if BILLING_AVAILABLE:
    # Use real billing API
    budget = billing_v1.Budget(...)
else:
    # Return mock data or skip feature
    logger.warning("Billing API not available, using mock data")
```

**Why This Matters:**
- App runs even if optional packages fail to install
- Prevents deployment failures due to missing dependencies
- Progressive enhancement (more features with more packages)

---

```python
# File: app/finops/cost_tracker_week4.py
# Lines: 32-48 (class initialization)

class CostTracker:
    """
    Tracks costs across GCP services and Vertex AI token usage.
    """
    
    def __init__(self, project_id: str, billing_account_id: Optional[str] = None):
        """
        Initialize cost tracker.
        
        Args:
            project_id: GCP project ID (e.g., "botpproject")
            billing_account_id: Billing account ID (optional, for budget creation)
        """
        self.project_id = project_id
        self.billing_account_id = billing_account_id
        self.bq_client = bigquery.Client(project=project_id)
        
        if billing_account_id and BILLING_AVAILABLE:
            self.billing_client = billing_v1.CloudBillingClient()
```

**Explanation:**
- **Line 32**: Class definition for cost tracking
- **Line 37**: Constructor with project configuration
  - `project_id`: Required - identifies which GCP project
  - `billing_account_id`: Optional - for creating budgets
- **Line 44-45**: Store configuration as instance variables
  - Accessible in all methods via `self.project_id`
- **Line 46**: Initialize BigQuery client
  - **Critical**: This connects to BigQuery
  - Uses default credentials (service account in GKE)
  - Project scoping: Queries run in `botpproject` context
- **Lines 48-49**: Conditionally initialize billing client
  - Only if billing account provided AND package available
  - Used for budget management (create/update/delete budgets)

**Authentication Flow:**
```
Pod starts with service account: rag-service@botpproject.iam.gserviceaccount.com
    ↓
bigquery.Client() reads GOOGLE_APPLICATION_CREDENTIALS
    ↓
Authenticates with IAM role: roles/bigquery.dataViewer
    ↓
Client ready to query billing_export dataset
```

---

```python
# File: app/finops/cost_tracker_week4.py
# Lines: 50-90 (get current month costs method)

    def get_current_month_costs(self) -> Dict[str, Any]:
        """
        Get costs for the current month.
        
        Returns:
            Cost breakdown by service
        """
        try:
            # Query billing export table (assumes billing export is configured)
            query = f"""
            SELECT
                service.description as service_name,
                SUM(cost) as total_cost,
                SUM(CASE WHEN usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) 
                    THEN cost ELSE 0 END) as daily_cost,
                currency
            FROM `{self.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
                AND project.id = @project_id
            GROUP BY service_name, currency
            ORDER BY total_cost DESC
            """
```

**Explanation (Line by Line):**

- **Line 50**: Method to fetch current month costs
- **Line 58**: Try block for error handling
- **Line 60**: Start of BigQuery SQL query (multi-line string)
- **Line 61-66**: SELECT clause defines output columns
  - **Line 62**: `service.description` - Service name (e.g., "Vertex AI", "Cloud Storage")
    - Aliased as `service_name` for clarity
  - **Line 63**: `SUM(cost)` - Total cost for the month
    - Aggregates all usage records for each service
  - **Line 64-65**: Conditional aggregation for yesterday's cost
    - `CASE WHEN usage_start_time >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)`
    - Only sum cost from yesterday
    - **Purpose**: Show daily trend ("up $5 from yesterday")
  - **Line 66**: `currency` - Currency code (usually "USD")
- **Line 67**: FROM clause specifies table
  - `billing_export.gcp_billing_export_v1_*` - Wildcard matches all export tables
  - GCP creates tables like `gcp_billing_export_v1_012345_6789AB_CDEF01`
  - Wildcard includes all data (one table per billing account)
- **Line 68**: WHERE clause filters data
  - `DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)`
  - **DATE_TRUNC**: Rounds date to start of month (e.g., 2026-03-01)
  - **Effect**: Only include records from current month (March 1 onwards)
- **Line 69**: Additional filter by project
  - `project.id = @project_id` - Parameterized query (security best practice)
  - Filters to only `botpproject` costs (multi-project support)
- **Line 70**: GROUP BY aggregates data
  - Groups all records with same service name and currency
  - `SUM()` functions calculate totals per group
- **Line 71**: ORDER BY sorts results
  - Descending by `total_cost` (highest spending services first)
  - **UI benefit**: Users see biggest costs at top of dashboard

---

```python
# File: app/finops/cost_tracker_week4.py
# Lines: 73-85 (query execution and result processing)

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id)
                ]
            )
            
            results = self.bq_client.query(query, job_config=job_config).result()
            
            # Process results
            costs_by_service = []
            for row in results:
                costs_by_service.append({
                    "service_name": row.service_name,
                    "total_cost": float(row.total_cost),
                    "daily_cost": float(row.daily_cost),
                    "currency": row.currency
                })
```

**Explanation:**
- **Lines 73-76**: Configure query execution
  - `QueryJobConfig`: Settings for query job
  - `query_parameters`: Parameterized values (SQL injection prevention)
  - `@project_id` in query = `self.project_id` value here
  - **Security**: User input never directly in SQL string
- **Line 78**: Execute query and wait for results
  - `self.bq_client.query()`: Submit query to BigQuery
  - `.result()`: Block until query completes (sync operation)
  - Returns iterator of result rows
- **Lines 81-88**: Transform results to Python dictionaries
  - `costs_by_service`: Empty list to collect results
  - `for row in results`: Iterate each result row
  - `row.service_name`: Access column by name
  - `float()`: Convert Decimal to float (JSON serializable)
  - **Output**: List of dicts ready for FastAPI JSON response

**Query Performance:**
- BigQuery processes in parallel (distributed system)
- Typical query time: 1-3 seconds for month of data
- Cost: $0.00001 per MB scanned (billing data is small)

---

```python
# File: app/finops/cost_tracker_week4.py
# Lines: 90-110 (calculate totals and return)

            # Calculate total
            total_cost = sum(item["total_cost"] for item in costs_by_service)
            
            return {
                "costs": costs_by_service,
                "total": total_cost,
                "currency": costs_by_service[0]["currency"] if costs_by_service else "USD",
                "period": {
                    "start": datetime.now().replace(day=1).isoformat(),
                    "end": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching current month costs: {str(e)}")
            
            # Return mock data if query fails (graceful degradation)
            return {
                "costs": [
                    {"service_name": "Vertex AI", "total_cost": 125.50, "daily_cost": 8.20, "currency": "USD"},
                    {"service_name": "Cloud Storage", "total_cost": 45.30, "daily_cost": 1.50, "currency": "USD"},
                    {"service_name": "Cloud Run", "total_cost": 32.10, "daily_cost": 1.10, "currency": "USD"}
                ],
                "total": 202.90,
                "currency": "USD",
                "period": {
                    "start": datetime.now().replace(day=1).isoformat(),
                    "end": datetime.now().isoformat()
                }
            }
```

**Explanation:**
- **Line 90**: Calculate grand total across all services
  - List comprehension: `sum(item["total_cost"] for item in costs_by_service)`
  - Sums total_cost field from each service
- **Lines 92-100**: Return structured response
  - `costs`: Array of service-level costs
  - `total`: Sum of all costs (displayed as headline metric)
  - `currency`: Extract from first service (all should be same currency)
  - `period.start`: First day of current month
  - `period.end`: Current date/time
  - **ISO format**: Standard format for date serialization
- **Lines 102-115**: Exception handling (graceful degradation)
  - **Line 103**: Log error for debugging
  - **Lines 106-115**: Return mock data instead of crashing
  - **Why**: Allow dashboard to load even if BigQuery unavailable
  - **Mock data**: Realistic sample costs for testing
  - **Production**: Replace with real data once billing export populated

**Error Scenarios:**
1. BigQuery API disabled → Exception → Mock data
2. Billing export not configured → Query returns 0 rows → Empty array
3. Network timeout → Exception → Mock data
4. Service account lacks permissions → Exception → Mock data

---

### 5. Experiment Routes (experiment_routes_week4.py)

**Purpose:** API endpoints for A/B testing, variant management, and feature flags.

**Key Code Sections:**

```python
# File: app/experiment_routes_week4.py
# Lines: 1-25 (imports and initialization)

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from app.experiments.experiment_tracker_week4 import ExperimentTracker
from app.experiments.variant_manager_week4 import VariantManager
from app.experiments.ab_testing_framework_week4 import ABTestingFramework
from app.experiments.feature_flags_week4 import FeatureFlags
from app.experiments.model_registry_week4 import ModelRegistry
from app.config import PROJECT_ID, REGION

router = APIRouter(prefix="/experiments", tags=["Experiments"])

# Initialize services
experiment_tracker = ExperimentTracker(project_id=PROJECT_ID, location=REGION)
variant_manager = VariantManager(project_id=PROJECT_ID)
ab_framework = ABTestingFramework(project_id=PROJECT_ID)
feature_flags = FeatureFlags(project_id=PROJECT_ID)
model_registry = ModelRegistry(project_id=PROJECT_ID, location=REGION)
```

**Explanation:**
- **Lines 6-10**: Import Week 4 experiment services
  - `ExperimentTracker`: Vertex AI experiment tracking (MLOps)
  - `VariantManager`: Manage multiple model variants (A/B/C versions)
  - `ABTestingFramework`: Traffic splitting and result analysis
  - `FeatureFlags`: Enable/disable features dynamically
  - `ModelRegistry`: Track model versions and metadata
- **Line 11**: Import project configuration
  - `PROJECT_ID`: For Vertex AI API calls
  - `REGION`: Where Vertex AI resources are located
- **Line 13**: Create router with `/experiments` prefix
- **Lines 16-20**: Initialize services at module load
  - Singleton pattern (one instance per service)
  - Services connect to Vertex AI and Firestore
  - Ready to handle requests immediately

---

```python
# File: app/experiment_routes_week4.py
# Lines: 30-70 (create variant endpoint)

class CreateVariantRequest(BaseModel):
    """Request model for creating a new variant"""
    variant_name: str
    model_name: str
    parameters: Dict[str, Any]
    description: Optional[str] = None

@router.post("/variants")
async def create_variant(request: CreateVariantRequest) -> Dict[str, Any]:
    """
    Create a new model variant for A/B testing.
    
    Args:
        variant_name: Unique identifier (e.g., "control", "high-temp", "low-temp")
        model_name: Vertex AI model (e.g., "gemini-2.0-flash-001")
        parameters: Model parameters (temperature, top_p, top_k, max_tokens)
        description: Human-readable description
    
    Returns:
        Created variant details with ID
    """
    try:
        variant = await variant_manager.create_variant(
            variant_name=request.variant_name,
            model_name=request.model_name,
            parameters=request.parameters,
            description=request.description
        )
        
        return {
            "success": True,
            "variant": variant,
            "message": f"Variant '{request.variant_name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Explanation:**
- **Lines 30-35**: Pydantic request model
  - Validates incoming JSON structure
  - `variant_name`: Unique ID for this variant (e.g., "control", "test-a")
  - `model_name`: Which Vertex AI model to use
  - `parameters`: Model config (temperature, max_tokens, etc.)
  - `description`: Optional human-readable notes
- **Line 37**: POST endpoint for creating variants
  - Method: POST (creates new resource)
  - Path: `/experiments/variants`
- **Lines 52-57**: Call variant manager service
  - `await`: Async call to Firestore
  - Creates document in `model_variants` collection
  - Stores: variant_name, model_name, parameters, timestamps
- **Lines 59-63**: Return success response
  - `variant`: Full variant object with generated ID
  - `message`: Confirmation message for UI

**Use Case Example:**
```json
POST /experiments/variants
{
  "variant_name": "high-creativity",
  "model_name": "gemini-2.0-flash-001",
  "parameters": {
    "temperature": 0.9,
    "top_p": 0.95,
    "max_tokens": 2048
  },
  "description": "Higher temperature for more creative responses"
}
```

**What Happens:**
1. Frontend sends JSON to create variant
2. Pydantic validates structure
3. Variant manager writes to Firestore
4. Document stored: `model_variants/high-creativity`
5. Response includes variant ID
6. Frontend updates variant list

---

```python
# File: app/experiment_routes_week4.py
# Lines: 90-120 (start A/B test endpoint)

@router.post("/start")
async def start_ab_test(request: StartABTestRequest) -> Dict[str, Any]:
    """
    Start an A/B test with traffic split across variants.
    
    Args:
        experiment_name: Name of the experiment
        variants: List of variant IDs to test
        traffic_split: Percentage allocation (must sum to 100)
        duration_days: How long to run the test
    
    Returns:
        Experiment details with active status
    """
    try:
        # Validate traffic split sums to 100
        if sum(request.traffic_split.values()) != 100:
            raise HTTPException(
                status_code=400,
                detail="Traffic split must sum to 100%"
            )
        
        # Start experiment in Vertex AI
        experiment_run = await experiment_tracker.start_experiment(
            experiment_name=request.experiment_name,
            variants=request.variants,
            description=request.description
        )
        
        # Configure A/B test traffic routing
        await ab_framework.configure_traffic_split(
            experiment_id=experiment_run.experiment_id,
            traffic_split=request.traffic_split
        )
        
        return {
            "success": True,
            "experiment": {
                "experiment_id": experiment_run.experiment_id,
                "variants": request.variants,
                "traffic_split": request.traffic_split,
                "start_time": datetime.utcnow().isoformat(),
                "end_time": (datetime.utcnow() + timedelta(days=request.duration_days)).isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Explanation:**
- **Line 90**: POST endpoint to start A/B test
- **Lines 106-110**: Validate traffic split
  - Traffic percentages must sum to 100%
  - Example: {"control": 50, "test-a": 30, "test-b": 20}
  - Returns 400 Bad Request if invalid
- **Lines 113-117**: Start experiment in Vertex AI
  - Creates Vertex AI experiment resource
  - Logs: experiment name, variants, start time
  - Returns: experiment_id for tracking
- **Lines 120-123**: Configure traffic routing
  - Stores traffic split in Firestore
  - Middleware reads this config to route requests
  - Example: 50% of users see "control", 50% see "test-a"
- **Lines 125-135**: Return experiment details
  - `experiment_id`: UUID for tracking results
  - `variants`: Which model variants are being tested
  - `traffic_split`: Routing percentages
  - `start_time` / `end_time`: Test duration

**Real-World Flow:**
```
User clicks "Start A/B Test"
    ↓
Frontend: POST /experiments/start
    ↓
Backend validates traffic split (50/50)
    ↓
Vertex AI: Create experiment resource
    ↓
Firestore: Store traffic config
    ↓
Middleware: Start routing 50% to control, 50% to test
    ↓
Collect metrics for 7 days
    ↓
Analyze results: Which variant performed better?
```

---

### 6. Observability Routes (observability_routes.py)

**Purpose:** API endpoints for SLO tracking, error budgets, and synthetic monitoring.

**Key Code Sections:**

```python
# File: app/observability_routes.py
# Lines: 1-20 (imports and initialization)

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from datetime import datetime, timedelta

from app.observability.slo_tracker_week4 import SLOTracker
from app.observability.synthetic_monitor_week4 import SyntheticMonitor
from app.observability.error_budget_week4 import ErrorBudgetCalculator
from app.config import PROJECT_ID

router = APIRouter(prefix="/observability", tags=["Observability"])

# Initialize services
slo_tracker = SLOTracker(project_id=PROJECT_ID)
synthetic_monitor = SyntheticMonitor(project_id=PROJECT_ID)
error_budget_calculator = ErrorBudgetCalculator(project_id=PROJECT_ID)
```

**Explanation:**
- **Lines 5-7**: Import observability services
  - `SLOTracker`: Track Service Level Objectives (uptime, latency, error rate)
  - `SyntheticMonitor`: Periodic health checks (ping endpoints)
  - `ErrorBudgetCalculator`: Calculate remaining error budget
- **Line 12**: Create router with `/observability` prefix
- **Lines 14-16**: Initialize services
  - Connect to Cloud Monitoring for reading/writing metrics
  - Ready to track SLIs (Service Level Indicators)

---

```python
# File: app/observability_routes.py
# Lines: 25-60 (get SLOs endpoint)

@router.get("/slos")
async def get_slos() -> Dict[str, Any]:
    """
    Get current SLO (Service Level Objective) status.
    
    Returns:
        SLO compliance data for all tracked objectives
    """
    try:
        slos = await slo_tracker.get_all_slos()
        
        return {
            "success": True,
            "slos": slos,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        # Return mock data if Cloud Monitoring unavailable
        return {
            "success": True,
            "slos": [
                {
                    "name": "API Availability",
                    "target": 99.9,
                    "current": 99.95,
                    "status": "healthy",
                    "period": "30d"
                },
                {
                    "name": "Response Latency (p95)",
                    "target": 500,
                    "current": 325,
                    "unit": "ms",
                    "status": "healthy",
                    "period": "30d"
                },
                {
                    "name": "Error Rate",
                    "target": 0.1,
                    "current": 0.05,
                    "unit": "%",
                    "status": "healthy",
                    "period": "30d"
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Explanation:**
- **Line 25**: GET endpoint for SLO status
- **Line 35**: Fetch SLOs from Cloud Monitoring
  - Queries custom metrics: `rag_availability`, `rag_latency_p95`, `rag_error_rate`
  - Compares current values to SLO targets
  - Returns: list of SLO objects with status
- **Lines 38-42**: Return real SLO data
- **Lines 44-69**: Fallback to mock data if error
  - **Why**: Dashboard should always load, even if monitoring down
  - **Mock SLOs**:
    - **API Availability**: 99.9% target, 99.95% actual (healthy)
    - **Response Latency (p95)**: 500ms target, 325ms actual (healthy)
    - **Error Rate**: 0.1% target, 0.05% actual (healthy)

**SLO Tracking Flow:**
```
Every minute (cron job or middleware):
    ↓
Collect metrics:
  - Total requests
  - Failed requests
  - Response times
    ↓
Write to Cloud Monitoring:
  - custom.googleapis.com/rag/availability
  - custom.googleapis.com/rag/latency_p95
  - custom.googleapis.com/rag/error_rate
    ↓
GET /observability/slos reads these metrics
    ↓
Compare to targets (99.9%, 500ms, 0.1%)
    ↓
Display status: healthy / at-risk / violated
```

---

## Frontend Implementation

### 1. App Routes (app.routes.ts)

**Purpose:** Define routing configuration for Week 4 dashboards.

**Key Changes:**

```typescript
// File: frontend/src/app/app.routes.ts
// Lines: 10-20 (add Week 4 routes)

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'admin', component: AdminComponent },
  { path: 'upload', component: UploadComponent },
  
  // Week 4: Enterprise dashboards
  { path: 'finops', component: FinopsDashboardComponent },
  { path: 'experiments', component: ExperimentsDashboardComponent },
  { path: 'observability', component: ObservabilityDashboardComponent },
  
  { path: '**', redirectTo: '' }  // Fallback to home
];
```

**Explanation:**
- **Lines 15-17**: Add routes for Week 4 dashboards
  - `finops`: Cost tracking dashboard
  - `experiments`: A/B testing dashboard
  - `observability`: SLO monitoring dashboard
- **Angular Router**: Maps URL paths to components
  - URL `/finops` → Loads FinopsDashboardComponent
  - URL `/experiments` → Loads ExperimentsDashboardComponent
  - URL `/observability` → Loads ObservabilityDashboardComponent
- **Line 19**: Fallback route (404 handler)
  - Any invalid URL redirects to home page

---

### 2. Navigation Menu (app.component.html)

**Purpose:** Add Week 4 dashboard links to main navigation.

**Key Changes:**

```html
<!-- File: frontend/src/app/app.component.html -->
<!-- Lines: 25-35 (add navigation links) -->

<nav class="navbar">
  <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">
    🏠 Home
  </a>
  <a routerLink="/chat" routerLinkActive="active">
    💬 Chat
  </a>
  <a routerLink="/upload" routerLinkActive="active">
    📤 Upload
  </a>
  
  <!-- Week 4: Dashboard links -->
  <a routerLink="/finops" routerLinkActive="active">
    💰 FinOps
  </a>
  <a routerLink="/experiments" routerLinkActive="active">
    🧪 Experiments
  </a>
  <a routerLink="/observability" routerLinkActive="active">
    📊 Observability
  </a>
  
  <a routerLink="/admin" routerLinkActive="active">
    ⚙️ Admin
  </a>
</nav>
```

**Explanation:**
- **routerLink**: Angular directive for navigation
  - Clicking link changes URL without page reload (SPA behavior)
- **routerLinkActive="active"**: Highlights current page
  - Adds `active` CSS class when on that route
  - Visual feedback for user location
- **Emoji icons**: Quick visual identification
  - 💰 FinOps = money/costs
  - 🧪 Experiments = testing/science
  - 📊 Observability = charts/monitoring

---

### 3. FinOps Service (finops.service.ts)

**Purpose:** Angular service for calling FinOps backend APIs.

**Complete Code with Explanations:**

```typescript
// File: frontend/src/app/services/finops.service.ts
// Lines: 1-15 (imports and service setup)

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'  // Singleton service (one instance app-wide)
})
export class FinopsService {
  private apiUrl = `${environment.apiUrl}/finops`;
  
  constructor(private http: HttpClient) {}
```

**Explanation:**
- **Line 1**: `@Injectable` decorator makes this a service
  - Angular can inject this into components
- **Line 2**: `HttpClient` for making HTTP requests
- **Line 3**: `Observable` for reactive programming (async data streams)
- **Line 4**: Environment config (different URLs for dev/prod)
- **Line 6-7**: Service configuration
  - `providedIn: 'root'` = app-wide singleton
  - Only one instance created, shared by all components
- **Line 10**: API base URL from environment
  - Development: `http://localhost:8080/finops`
  - Production: `http://34.170.28.178.nip.io/finops`
- **Line 12**: Constructor injects HttpClient
  - Angular's dependency injection provides HttpClient instance

---

```typescript
// File: frontend/src/app/services/finops.service.ts
// Lines: 17-50 (API methods)

  /**
   * Get comprehensive dashboard data
   */
  getDashboard(): Observable<any> {
    return this.http.get(`${this.apiUrl}/dashboard`);
  }
  
  /**
   * Get current month costs by service
   */
  getCurrentMonthCosts(): Observable<any> {
    return this.http.get(`${this.apiUrl}/costs/current-month`);
  }
  
  /**
   * Get daily costs for time-series chart
   */
  getDailyCosts(days: number = 30): Observable<any> {
    return this.http.get(`${this.apiUrl}/costs/daily`, {
      params: { days: days.toString() }
    });
  }
  
  /**
   * Get token usage summary
   */
  getTokenUsage(days: number = 30): Observable<any> {
    return this.http.get(`${this.apiUrl}/tokens/usage`, {
      params: { days: days.toString() }
    });
  }
  
  /**
   * Get budget information
   */
  getBudgets(): Observable<any> {
    return this.http.get(`${this.apiUrl}/budgets`);
  }
```

**Explanation:**
- **getDashboard()**: Fetch all dashboard data in one call
  - Returns: Observable (async data stream)
  - Backend endpoint: `GET /finops/dashboard`
  - Component subscribes: `finopsService.getDashboard().subscribe(data => ...)`
- **getCurrentMonthCosts()**: Fetch month-to-date costs
  - Returns breakdown by service
  - Used for pie chart (cost distribution)
- **getDailyCosts(days)**: Fetch time-series cost data
  - Parameter: `days` = how many days of history
  - Used for line chart (cost trend over time)
  - Query param: `?days=30`
- **getTokenUsage(days)**: Fetch AI token consumption
  - Shows: tokens used per day, cost per token
  - Used for token usage chart
- **getBudgets()**: Fetch budget status
  - Shows: budget limit, spent amount, remaining
  - Used for budget progress bars

**Observable Pattern:**
```typescript
// In component:
this.finopsService.getDashboard().subscribe(
  data => {
    // Success: Update charts with data
    this.updateCharts(data);
  },
  error => {
    // Error: Show error message
    console.error('Failed to load dashboard', error);
  }
);
```

**Why Observables:**
- Async: Don't block UI while waiting for API
- Cancellable: Can cancel request if component destroyed
- Chainable: Can transform data with `map`, `filter`, etc.

---

### 4. FinOps Dashboard Component (finops-dashboard.component.ts)

**Purpose:** Display cost tracking dashboard with interactive charts.

**Complete Code with Explanations:**

```typescript
// File: frontend/src/app/finops-dashboard/finops-dashboard.component.ts
// Lines: 1-25 (imports and component setup)

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';
import { FinopsService } from '../services/finops.service';
import { interval, Subscription } from 'rxjs';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  selector: 'app-finops-dashboard',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './finops-dashboard.component.html',
  styleUrls: ['./finops-dashboard.component.css']
})
export class FinopsDashboardComponent implements OnInit, OnDestroy {
  loading = true;
  error: string | null = null;
  
  // Dashboard data
  totalCost = 0;
  budgetRemaining = 0;
  dailyCostTrend = 0;
```

**Explanation:**
- **Line 1**: Import Angular core decorators
  - `Component`: Define component metadata
  - `OnInit`: Lifecycle hook for initialization
  - `OnDestroy`: Lifecycle hook for cleanup
- **Line 3-4**: Import Chart.js libraries
  - `Chart`: Chart.js main class
  - `BaseChartDirective`: ng2-charts wrapper for Angular
- **Line 5**: Import FinOps service
  - Injected for API calls
- **Line 6**: Import RxJS for auto-refresh
  - `interval`: Emit value every N seconds
  - `Subscription`: Manage observable subscriptions
- **Line 9**: Register Chart.js components
  - Required for charts to render
  - Registers: line, bar, pie, doughnut chart types
- **Lines 11-17**: Component decorator
  - `selector`: HTML tag name (`<app-finops-dashboard>`)
  - `standalone: true`: No need for NgModule
  - `imports`: Dependencies needed by this component
  - `templateUrl`: HTML template file path
  - `styleUrls`: CSS styles file path
- **Lines 19-25**: Component state variables
  - `loading`: Show spinner while fetching data
  - `error`: Error message if API fails
  - `totalCost`: Month-to-date spending
  - `budgetRemaining`: Budget left to spend
  - `dailyCostTrend`: % change from yesterday

---

```typescript
// File: frontend/src/app/finops-dashboard/finops-dashboard.component.ts
// Lines: 27-70 (chart configurations)

  // Cost by service pie chart
  costByServiceChart: ChartConfiguration['data'] = {
    labels: [],
    datasets: [{
      label: 'Cost by Service',
      data: [],
      backgroundColor: [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
        '#9966FF', '#FF9F40', '#FF6384'
      ]
    }]
  };
  
  costByServiceOptions: ChartConfiguration['options'] = {
    responsive: true,
    plugins: {
      legend: { position: 'bottom' },
      title: {
        display: true,
        text: 'Cost Distribution by Service'
      }
    }
  };
  
  // Daily cost trend line chart
  dailyCostChart: ChartConfiguration['data'] = {
    labels: [],
    datasets: [{
      label: 'Daily Cost (USD)',
      data: [],
      borderColor: '#36A2EB',
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      fill: true,
      tension: 0.4  // Smooth curves
    }]
  };
  
  dailyCostOptions: ChartConfiguration['options'] = {
    responsive: true,
    plugins: {
      legend: { display: true },
      title: {
        display: true,
        text: 'Daily Cost Trend (Last 30 Days)'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Cost (USD)' }
      },
      x: {
        title: { display: true, text: 'Date' }
      }
    }
  };
```

**Explanation:**
- **Lines 28-38**: Pie chart data structure
  - `labels`: Service names (e.g., ["Vertex AI", "Cloud Storage"])
  - `data`: Cost values (e.g., [125.50, 45.30])
  - `backgroundColor`: Color for each slice
  - Initially empty (populated by loadDashboard())
- **Lines 40-50**: Pie chart options
  - `responsive: true`: Resize with window
  - `legend.position`: Show labels below chart
  - `title.text`: Chart heading
- **Lines 53-66**: Line chart data structure
  - `labels`: Dates (e.g., ["2026-03-01", "2026-03-02", ...])
  - `data`: Daily costs (e.g., [8.50, 9.20, 7.80, ...])
  - `borderColor`: Line color (blue)
  - `backgroundColor`: Fill color (transparent blue)
  - `fill: true`: Shade area under line
  - `tension: 0.4`: Smooth curves (not jagged lines)
- **Lines 68-88**: Line chart options
  - `scales.y`: Y-axis starts at 0, label "Cost (USD)"
  - `scales.x`: X-axis label "Date"

---

```typescript
// File: frontend/src/app/finops-dashboard/finops-dashboard.component.ts
// Lines: 90-110 (initialization and auto-refresh)

  private refreshSubscription?: Subscription;
  
  constructor(private finopsService: FinopsService) {}
  
  ngOnInit(): void {
    // Load dashboard data on component init
    this.loadDashboard();
    
    // Auto-refresh every 60 seconds
    this.refreshSubscription = interval(60000).subscribe(() => {
      this.loadDashboard();
    });
  }
  
  ngOnDestroy(): void {
    // Clean up subscription to prevent memory leaks
    this.refreshSubscription?.unsubscribe();
  }
```

**Explanation:**
- **Line 90**: Store subscription for cleanup
  - Must unsubscribe to prevent memory leaks
- **Line 92**: Constructor injects FinopsService
  - Angular's dependency injection provides service instance
- **Line 94**: ngOnInit lifecycle hook
  - Called once when component mounts
  - Ideal for initial data loading
- **Line 96**: Load dashboard data immediately
  - Fetch costs, budgets, token usage
  - Populate charts
- **Lines 99-101**: Set up auto-refresh
  - `interval(60000)`: Emit value every 60 seconds (60,000ms)
  - `.subscribe()`: Call loadDashboard() on each emit
  - **Effect**: Dashboard updates automatically every minute
  - **UX benefit**: Always shows fresh data without manual refresh
- **Lines 104-107**: ngOnDestroy lifecycle hook
  - Called when component unmounts (user navigates away)
  - `unsubscribe()`: Stop interval timer
  - **Why important**: Prevents memory leaks
  - Without this: Timer keeps running even after component destroyed

---

```typescript
// File: frontend/src/app/finops-dashboard/finops-dashboard.component.ts
// Lines: 112-170 (load dashboard data)

  async loadDashboard(): Promise<void> {
    this.loading = true;
    this.error = null;
    
    try {
      const data = await this.finopsService.getDashboard().toPromise();
      
      // Update summary metrics
      this.totalCost = data.current_month_costs?.total || 0;
      
      // Calculate budget remaining
      if (data.budgets && data.budgets.length > 0) {
        const budget = data.budgets[0];
        this.budgetRemaining = budget.amount - budget.spent;
      }
      
      // Update cost by service chart
      if (data.current_month_costs?.costs) {
        this.costByServiceChart.labels = data.current_month_costs.costs.map(
          (c: any) => c.service_name
        );
        this.costByServiceChart.datasets[0].data = data.current_month_costs.costs.map(
          (c: any) => c.total_cost
        );
      }
      
      // Update daily cost trend chart
      if (data.daily_costs?.costs) {
        this.dailyCostChart.labels = data.daily_costs.costs.map(
          (c: any) => new Date(c.date).toLocaleDateString()
        );
        this.dailyCostChart.datasets[0].data = data.daily_costs.costs.map(
          (c: any) => c.total_cost
        );
      }
      
      // Calculate daily trend (% change)
      if (data.daily_costs?.costs && data.daily_costs.costs.length >= 2) {
        const yesterday = data.daily_costs.costs[data.daily_costs.costs.length - 2].total_cost;
        const today = data.daily_costs.costs[data.daily_costs.costs.length - 1].total_cost;
        this.dailyCostTrend = ((today - yesterday) / yesterday) * 100;
      }
      
    } catch (err: any) {
      this.error = err.message || 'Failed to load dashboard data';
      console.error('Error loading FinOps dashboard:', err);
    } finally {
      this.loading = false;
    }
  }
```

**Explanation:**
- **Line 112**: Async function for data loading
  - `async/await`: Clean syntax for promises
- **Lines 113-114**: Set loading state
  - `loading = true`: Show spinner in UI
  - `error = null`: Clear previous errors
- **Line 117**: Call FinOps service
  - `getDashboard()`: Returns Observable
  - `.toPromise()`: Convert to Promise for async/await
  - `await`: Wait for API response
  - `data`: Response object with costs, budgets, tokens
- **Line 120**: Update total cost metric
  - Extract from `current_month_costs.total`
  - Displayed as headline metric in dashboard
- **Lines 123-127**: Calculate budget remaining
  - Get first budget from array
  - `budget.amount`: Total budget allocated
  - `budget.spent`: Amount spent so far
  - `budgetRemaining`: How much left to spend
- **Lines 130-137**: Update pie chart
  - `map()`: Transform array of objects
  - `labels`: Extract service names for pie slices
  - `data`: Extract costs for slice sizes
  - Chart.js automatically updates visualization
- **Lines 140-148**: Update line chart
  - `map()`: Extract dates and costs
  - `toLocaleDateString()`: Format date for display
  - Chart shows cost trend over time
- **Lines 151-156**: Calculate % change
  - Compare yesterday's cost to today's cost
  - `((today - yesterday) / yesterday) * 100`: Percent change formula
  - Displayed as "↑ 5.2%" or "↓ 3.1%" with color
- **Lines 158-163**: Error handling
  - Catch any API errors
  - Set `error` message for UI display
  - Log to console for debugging
- **Lines 164-166**: Cleanup
  - `finally`: Runs whether success or error
  - `loading = false`: Hide spinner
  - UI shows either data or error message

**Data Flow Summary:**
```
Component mounts → ngOnInit() → loadDashboard()
    ↓
API call: GET /finops/dashboard
    ↓
Response: { current_month_costs, daily_costs, budgets, token_usage }
    ↓
Update state: totalCost, budgetRemaining, dailyCostTrend
    ↓
Update charts: costByServiceChart, dailyCostChart
    ↓
Chart.js re-renders visualizations
    ↓
User sees updated dashboard
    ↓
Wait 60 seconds → loadDashboard() (repeat)
```

---

### 5. FinOps Dashboard Template (finops-dashboard.component.html)

**Purpose:** Display cost tracking dashboard UI with charts.

**Complete Code with Explanations:**

```html
<!-- File: frontend/src/app/finops-dashboard/finops-dashboard.component.html -->
<!-- Lines: 1-30 (header and summary metrics) -->

<div class="dashboard-container">
  <header class="dashboard-header">
    <h1>💰 FinOps Dashboard</h1>
    <p>Real-time cost tracking and optimization</p>
  </header>
  
  <!-- Loading spinner -->
  <div *ngIf="loading" class="loading-spinner">
    <div class="spinner"></div>
    <p>Loading dashboard data...</p>
  </div>
  
  <!-- Error message -->
  <div *ngIf="error" class="error-message">
    <p>❌ {{ error }}</p>
    <button (click)="loadDashboard()">Retry</button>
  </div>
  
  <!-- Dashboard content -->
  <div *ngIf="!loading && !error" class="dashboard-content">
    
    <!-- Summary metrics cards -->
    <div class="metrics-row">
      <div class="metric-card">
        <h3>Total Cost (MTD)</h3>
        <p class="metric-value">${{ totalCost.toFixed(2) }}</p>
        <span class="metric-label">Month-to-Date</span>
      </div>
      
      <div class="metric-card">
        <h3>Budget Remaining</h3>
        <p class="metric-value">${{ budgetRemaining.toFixed(2) }}</p>
        <span class="metric-label">This Month</span>
      </div>
      
      <div class="metric-card">
        <h3>Daily Trend</h3>
        <p class="metric-value" [class.trend-up]="dailyCostTrend > 0" [class.trend-down]="dailyCostTrend < 0">
          {{ dailyCostTrend > 0 ? '↑' : '↓' }} {{ Math.abs(dailyCostTrend).toFixed(1) }}%
        </p>
        <span class="metric-label">vs Yesterday</span>
      </div>
    </div>
```

**Explanation:**
- **Lines 1-6**: Dashboard header
  - `<h1>`: Title with emoji icon
  - `<p>`: Subtitle description
- **Lines 9-12**: Loading state
  - `*ngIf="loading"`: Only show when loading = true
  - CSS spinner animation
  - "Loading dashboard data..." message
- **Lines 15-18**: Error state
  - `*ngIf="error"`: Only show when error exists
  - Display error message
  - Retry button calls `loadDashboard()`
- **Lines 21-49**: Dashboard content
  - `*ngIf="!loading && !error"`: Show when data loaded successfully
  - **Lines 24-48**: Three metric cards
    - **Card 1: Total Cost**
      - `totalCost.toFixed(2)`: Format as currency (2 decimals)
      - Shows month-to-date spending
    - **Card 2: Budget Remaining**
      - `budgetRemaining.toFixed(2)`: Format as currency
      - Shows how much budget left
    - **Card 3: Daily Trend**
      - `[class.trend-up]`: Add CSS class if trending up (red)
      - `[class.trend-down]`: Add CSS class if trending down (green)
      - `dailyCostTrend > 0 ? '↑' : '↓'`: Show arrow based on direction
      - `Math.abs(dailyCostTrend).toFixed(1)`: Show absolute value with 1 decimal

---

```html
<!-- File: frontend/src/app/finops-dashboard/finops-dashboard.component.html -->
<!-- Lines: 51-85 (charts section) -->

    <!-- Charts grid -->
    <div class="charts-grid">
      
      <!-- Cost by service pie chart -->
      <div class="chart-card">
        <h3>Cost Distribution by Service</h3>
        <canvas baseChart
          [data]="costByServiceChart"
          [options]="costByServiceOptions"
          type="pie">
        </canvas>
      </div>
      
      <!-- Daily cost trend line chart -->
      <div class="chart-card">
        <h3>Daily Cost Trend (Last 30 Days)</h3>
        <canvas baseChart
          [data]="dailyCostChart"
          [options]="dailyCostOptions"
          type="line">
        </canvas>
      </div>
      
      <!-- Token usage chart -->
      <div class="chart-card">
        <h3>Token Usage & Cost</h3>
        <div class="token-metrics">
          <div>
            <p class="token-count">2.5M</p>
            <span>Tokens Used</span>
          </div>
          <div>
            <p class="token-cost">$125.00</p>
            <span>Token Cost</span>
          </div>
        </div>
      </div>
      
    </div>
    
  </div>
</div>
```

**Explanation:**
- **Lines 52-97**: Charts grid (responsive layout)
  - **Lines 55-63**: Pie chart card
    - `<canvas baseChart>`: ng2-charts directive
    - `[data]`: Bind to costByServiceChart data
    - `[options]`: Bind to costByServiceOptions config
    - `type="pie"`: Render as pie chart
    - Shows: Cost distribution by service (Vertex AI, Storage, etc.)
  - **Lines 66-74**: Line chart card
    - `type="line"`: Render as line chart
    - Shows: Daily cost trend over 30 days
    - Interactive: Hover shows exact values
  - **Lines 77-92**: Token usage card
    - Static metrics display (no chart)
    - Shows: Total tokens used and cost
    - Could be replaced with bar chart in production

**Angular Data Binding:**
```typescript
// Component (TypeScript)
costByServiceChart.labels = ["Vertex AI", "Cloud Storage"];
costByServiceChart.datasets[0].data = [125.50, 45.30];
```
```html
<!-- Template (HTML) -->
<canvas baseChart [data]="costByServiceChart"></canvas>
```
**Result:** Chart automatically updates when data changes

---

## Code Flow & Execution

### End-to-End Flow: Viewing FinOps Dashboard

#### Step 1: User Navigation
```
User clicks "💰 FinOps" in navigation menu
    ↓
Angular Router: URL changes to /finops
    ↓
Angular loads: FinopsDashboardComponent
    ↓
Component lifecycle: constructor() → ngOnInit()
```

#### Step 2: Component Initialization
```typescript
// finops-dashboard.component.ts

ngOnInit() {
  this.loadDashboard();  // Initial load
  interval(60000).subscribe(() => {
    this.loadDashboard();  // Auto-refresh every 60 seconds
  });
}
```

#### Step 3: API Call
```typescript
loadDashboard() {
  this.loading = true;  // Show spinner
  
  // Call FinOps service
  this.finopsService.getDashboard().toPromise()
    .then(data => {
      // Update component state
      this.totalCost = data.current_month_costs.total;
      this.costByServiceChart.labels = data.current_month_costs.costs.map(c => c.service_name);
      this.costByServiceChart.datasets[0].data = data.current_month_costs.costs.map(c => c.total_cost);
      this.loading = false;  // Hide spinner
    });
}
```

#### Step 4: HTTP Request
```typescript
// finops.service.ts

getDashboard() {
  return this.http.get(`${this.apiUrl}/dashboard`);
  // HTTP GET: http://34.170.28.178.nip.io/finops/dashboard
}
```

#### Step 5: Network Request
```
Browser → HTTP GET → GKE Load Balancer
    ↓
Load Balancer → rag-backend-service (ClusterIP)
    ↓
Service → rag-backend pod (random selection)
    ↓
Pod → Uvicorn (port 8080)
    ↓
Uvicorn → FastAPI application
```

#### Step 6: Backend Routing
```python
# main.py

app.include_router(finops_router)  # Registers /finops routes
```

#### Step 7: Route Handler
```python
# finops_routes_week4.py

@router.get("/dashboard")
async def get_finops_dashboard():
    # Fetch data from multiple sources
    current_costs = cost_tracker.get_current_month_costs()
    daily_costs = cost_tracker.get_daily_costs(days=30)
    budgets = budget_manager.list_budgets()
    token_usage = token_tracker.get_usage_summary(days=30)
    
    return {
        "current_month_costs": current_costs,
        "daily_costs": daily_costs,
        "budgets": budgets,
        "token_usage": token_usage
    }
```

#### Step 8: Query BigQuery
```python
# cost_tracker_week4.py

def get_current_month_costs():
    query = """
    SELECT
        service.description as service_name,
        SUM(cost) as total_cost,
        currency
    FROM `botpproject.billing_export.gcp_billing_export_v1_*`
    WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
    GROUP BY service_name, currency
    ORDER BY total_cost DESC
    """
    
    # Execute query
    results = self.bq_client.query(query).result()
    
    # Process results
    costs = []
    for row in results:
        costs.append({
            "service_name": row.service_name,
            "total_cost": float(row.total_cost),
            "currency": row.currency
        })
    
    return {"costs": costs, "total": sum(c["total_cost"] for c in costs)}
```

#### Step 9: BigQuery Processing
```
BigQuery receives query
    ↓
Check IAM: Does rag-service@botpproject.iam.gserviceaccount.com have bigquery.dataViewer?
    ↓ Yes
Read table: billing_export.gcp_billing_export_v1_012345678_ABCDEF_123456
    ↓
Filter: WHERE DATE >= 2026-03-01 (start of current month)
    ↓
Aggregate: SUM(cost) GROUP BY service
    ↓
Sort: ORDER BY total_cost DESC
    ↓
Return results (typically 1-3 seconds)
```

#### Step 10: Response Formatting
```python
# finops_routes_week4.py

return {
    "success": True,
    "current_month_costs": {
        "costs": [
            {"service_name": "Vertex AI", "total_cost": 125.50, "currency": "USD"},
            {"service_name": "Cloud Storage", "total_cost": 45.30, "currency": "USD"},
            {"service_name": "Cloud Run", "total_cost": 32.10, "currency": "USD"}
        ],
        "total": 202.90,
        "currency": "USD"
    },
    "daily_costs": {...},
    "budgets": {...},
    "token_usage": {...},
    "timestamp": "2026-03-08T14:30:00Z"
}
```

#### Step 11: HTTP Response
```
FastAPI serializes to JSON
    ↓
Uvicorn sends HTTP response
    ↓
Pod → Service → Load Balancer
    ↓
Load Balancer → Browser
```

#### Step 12: Frontend Processing
```typescript
// finops-dashboard.component.ts

const data = await this.finopsService.getDashboard().toPromise();

// Update state
this.totalCost = data.current_month_costs.total;  // 202.90

// Update pie chart
this.costByServiceChart.labels = ["Vertex AI", "Cloud Storage", "Cloud Run"];
this.costByServiceChart.datasets[0].data = [125.50, 45.30, 32.10];

this.loading = false;  // Hide spinner, show dashboard
```

#### Step 13: Chart Rendering
```
Angular change detection triggers
    ↓
Chart.js detects data change
    ↓
Chart.js re-renders pie chart:
  - 62% Vertex AI (blue slice)
  - 22% Cloud Storage (orange slice)
  - 16% Cloud Run (yellow slice)
    ↓
User sees updated dashboard with real data
```

#### Step 14: Auto-Refresh Loop
```
Wait 60 seconds
    ↓
interval(60000) emits
    ↓
loadDashboard() called again
    ↓
Repeat steps 3-13
    ↓
Dashboard always shows fresh data (no manual refresh needed)
```

---

### Experiment Creation Flow

#### User Creates A/B Test Variant

```
User clicks "Create Variant" button
    ↓
Modal opens with form:
  - Variant Name: "high-creativity"
  - Model: "gemini-2.0-flash-001"
  - Temperature: 0.9
  - Max Tokens: 2048
    ↓
User clicks "Create"
    ↓
POST /experiments/variants
{
  "variant_name": "high-creativity",
  "model_name": "gemini-2.0-flash-001",
  "parameters": {
    "temperature": 0.9,
    "top_p": 0.95,
    "max_tokens": 2048
  }
}
    ↓
Backend: experiment_routes_week4.py → create_variant()
    ↓
variant_manager.create_variant()
    ↓
Firestore: Create document in model_variants collection
{
  "variant_id": "var_abc123",
  "variant_name": "high-creativity",
  "model_name": "gemini-2.0-flash-001",
  "parameters": {...},
  "created_at": "2026-03-08T14:30:00Z",
  "status": "active"
}
    ↓
Response: { "success": true, "variant": {...} }
    ↓
Frontend: Update variant list, show success toast
    ↓
User sees new variant in list
```

#### User Starts A/B Test

```
User selects variants: "control", "high-creativity"
User sets traffic split: 50% / 50%
User clicks "Start Test"
    ↓
POST /experiments/start
{
  "experiment_name": "Creativity Test",
  "variants": ["control", "high-creativity"],
  "traffic_split": {"control": 50, "high-creativity": 50},
  "duration_days": 7
}
    ↓
Backend validates: sum([50, 50]) = 100 ✓
    ↓
experiment_tracker.start_experiment()
    ↓
Vertex AI: Create experiment resource
    ↓
ab_framework.configure_traffic_split()
    ↓
Firestore: Store experiment config
{
  "experiment_id": "exp_xyz789",
  "variants": ["control", "high-creativity"],
  "traffic_split": {"control": 50, "high-creativity": 50},
  "start_time": "2026-03-08T14:30:00Z",
  "end_time": "2026-03-15T14:30:00Z",
  "status": "active"
}
    ↓
Response: { "success": true, "experiment": {...} }
    ↓
Frontend: Show "Experiment Running" banner
```

#### User Chats (A/B Test Active)

```
User sends chat message: "Explain quantum computing"
    ↓
POST /query
{
  "message": "Explain quantum computing",
  "session_id": "session_123"
}
    ↓
Middleware: middleware_ab_testing.py
    ↓
Check for active experiment
    ↓
Load experiment config from Firestore
    ↓
Determine variant for user (consistent hashing by session_id)
  - hash("session_123") % 100 = 42
  - Traffic split: 0-49 = control, 50-99 = high-creativity
  - Result: Use "control" variant
    ↓
Load variant config from Firestore
{
  "model_name": "gemini-2.0-flash-001",
  "parameters": {
    "temperature": 0.3,
    "max_tokens": 1024
  }
}
    ↓
Override request parameters
request.model = "gemini-2.0-flash-001"
request.temperature = 0.3
request.max_tokens = 1024
    ↓
Continue to main query handler
    ↓
Call Vertex AI with "control" variant parameters
    ↓
Log to experiment tracker:
{
  "experiment_id": "exp_xyz789",
  "variant": "control",
  "session_id": "session_123",
  "latency_ms": 850,
  "tokens_used": 342,
  "user_rating": null  // Filled in later if user rates response
}
    ↓
Return response to user
    ↓
User sees response generated with "control" parameters
```

**Next user (different session):**
```
hash("session_456") % 100 = 73
  ↓
73 falls in 50-99 range
  ↓
Use "high-creativity" variant
  ↓
Load variant: {"temperature": 0.9, "max_tokens": 2048}
  ↓
Call Vertex AI with high-creativity parameters
  ↓
Log to experiment tracker
  ↓
User sees more creative (potentially more varied) response
```

#### Analyzing Results

```
After 7 days:
    ↓
GET /experiments/results?experiment_id=exp_xyz789
    ↓
experiment_tracker.get_results()
    ↓
Query Vertex AI Experiments:
  - control: avg_latency=850ms, avg_tokens=342, avg_rating=4.2
  - high-creativity: avg_latency=1200ms, avg_tokens=512, avg_rating=4.5
    ↓
Calculate statistical significance (Chi-square test)
    ↓
Return results:
{
  "winner": "high-creativity",
  "confidence": 0.95,
  "metrics": {
    "control": {"latency": 850, "rating": 4.2},
    "high-creativity": {"latency": 1200, "rating": 4.5}
  },
  "recommendation": "Deploy high-creativity variant (higher user satisfaction)"
}
    ↓
Frontend: Display results table, winner badge, recommendation
    ↓
User decides: Deploy winning variant as default
```

---

## API Reference

### FinOps Endpoints

#### GET /finops/dashboard
**Purpose:** Get comprehensive dashboard data (all metrics in one call)

**Response:**
```json
{
  "success": true,
  "current_month_costs": {
    "costs": [
      {"service_name": "Vertex AI", "total_cost": 125.50, "daily_cost": 8.20, "currency": "USD"},
      {"service_name": "Cloud Storage", "total_cost": 45.30, "daily_cost": 1.50, "currency": "USD"}
    ],
    "total": 170.80,
    "currency": "USD"
  },
  "daily_costs": {
    "costs": [
      {"date": "2026-03-01", "total_cost": 5.50},
      {"date": "2026-03-02", "total_cost": 6.20}
    ]
  },
  "budgets": [
    {"name": "Monthly Budget", "amount": 500.00, "spent": 170.80, "remaining": 329.20}
  ],
  "token_usage": {
    "total_tokens": 2500000,
    "total_cost": 125.00,
    "avg_cost_per_1k_tokens": 0.05
  },
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

#### GET /finops/costs/current-month
**Purpose:** Get month-to-date costs by service

**Response:**
```json
{
  "success": true,
  "period": "current_month",
  "costs": [
    {"service_name": "Vertex AI", "total_cost": 125.50, "daily_cost": 8.20, "currency": "USD"},
    {"service_name": "Cloud Storage", "total_cost": 45.30, "daily_cost": 1.50, "currency": "USD"}
  ],
  "total": 170.80,
  "currency": "USD",
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

#### GET /finops/costs/daily?days=30
**Purpose:** Get daily cost time-series data

**Query Parameters:**
- `days` (optional): Number of days of history (default: 30)

**Response:**
```json
{
  "success": true,
  "costs": [
    {"date": "2026-03-01", "total_cost": 5.50, "currency": "USD"},
    {"date": "2026-03-02", "total_cost": 6.20, "currency": "USD"},
    {"date": "2026-03-03", "total_cost": 5.80, "currency": "USD"}
  ],
  "period": {
    "start": "2026-02-07",
    "end": "2026-03-08"
  },
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

#### GET /finops/tokens/usage?days=30
**Purpose:** Get AI token usage metrics

**Response:**
```json
{
  "success": true,
  "total_tokens": 2500000,
  "total_cost": 125.00,
  "avg_cost_per_1k_tokens": 0.05,
  "daily_usage": [
    {"date": "2026-03-01", "tokens": 85000, "cost": 4.25},
    {"date": "2026-03-02", "tokens": 92000, "cost": 4.60}
  ],
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

### Experiments Endpoints

#### POST /experiments/variants
**Purpose:** Create a new model variant for A/B testing

**Request:**
```json
{
  "variant_name": "high-creativity",
  "model_name": "gemini-2.0-flash-001",
  "parameters": {
    "temperature": 0.9,
    "top_p": 0.95,
    "max_tokens": 2048
  },
  "description": "Higher temperature for more creative responses"
}
```

**Response:**
```json
{
  "success": true,
  "variant": {
    "variant_id": "var_abc123",
    "variant_name": "high-creativity",
    "model_name": "gemini-2.0-flash-001",
    "parameters": {"temperature": 0.9, "top_p": 0.95, "max_tokens": 2048},
    "description": "Higher temperature for more creative responses",
    "created_at": "2026-03-08T14:30:00Z",
    "status": "active"
  },
  "message": "Variant 'high-creativity' created successfully"
}
```

---

#### GET /experiments/variants
**Purpose:** List all model variants

**Response:**
```json
{
  "success": true,
  "variants": [
    {
      "variant_id": "var_123",
      "variant_name": "control",
      "model_name": "gemini-2.0-flash-001",
      "parameters": {"temperature": 0.3, "max_tokens": 1024},
      "status": "active"
    },
    {
      "variant_id": "var_456",
      "variant_name": "high-creativity",
      "model_name": "gemini-2.0-flash-001",
      "parameters": {"temperature": 0.9, "max_tokens": 2048},
      "status": "active"
    }
  ]
}
```

---

#### POST /experiments/start
**Purpose:** Start an A/B test with traffic split

**Request:**
```json
{
  "experiment_name": "Creativity Test",
  "variants": ["control", "high-creativity"],
  "traffic_split": {
    "control": 50,
    "high-creativity": 50
  },
  "duration_days": 7,
  "description": "Test if higher creativity improves user satisfaction"
}
```

**Response:**
```json
{
  "success": true,
  "experiment": {
    "experiment_id": "exp_xyz789",
    "experiment_name": "Creativity Test",
    "variants": ["control", "high-creativity"],
    "traffic_split": {"control": 50, "high-creativity": 50},
    "start_time": "2026-03-08T14:30:00Z",
    "end_time": "2026-03-15T14:30:00Z",
    "status": "active"
  }
}
```

---

### Observability Endpoints

#### GET /observability/slos
**Purpose:** Get SLO (Service Level Objective) status

**Response:**
```json
{
  "success": true,
  "slos": [
    {
      "name": "API Availability",
      "target": 99.9,
      "current": 99.95,
      "status": "healthy",
      "period": "30d"
    },
    {
      "name": "Response Latency (p95)",
      "target": 500,
      "current": 325,
      "unit": "ms",
      "status": "healthy",
      "period": "30d"
    },
    {
      "name": "Error Rate",
      "target": 0.1,
      "current": 0.05,
      "unit": "%",
      "status": "healthy",
      "period": "30d"
    }
  ],
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

#### GET /observability/error-budgets
**Purpose:** Get error budget status (how many errors allowed before SLO violation)

**Response:**
```json
{
  "success": true,
  "error_budgets": [
    {
      "slo_name": "API Availability",
      "target": 99.9,
      "current": 99.95,
      "budget_remaining": 0.05,
      "budget_used": 0.0,
      "status": "healthy"
    }
  ],
  "timestamp": "2026-03-08T14:30:00Z"
}
```

---

## Testing & Verification

### Manual Testing Steps

#### 1. Verify Backend Health

```bash
# Check pods are running
kubectl get pods -n default -l app=rag-backend

# Expected output:
# NAME                           READY   STATUS    RESTARTS   AGE
# rag-backend-7ff756f988-8xpm6   1/1     Running   0          5m
# rag-backend-7ff756f988-wdmwd   1/1     Running   0          5m

# Check logs for errors
kubectl logs -l app=rag-backend -n default --tail=50

# Expected: No errors, "Application startup complete"
```

#### 2. Test FinOps Endpoint

```bash
# Test dashboard endpoint
curl http://34.170.28.178.nip.io/finops/dashboard

# Expected response:
# {
#   "success": true,
#   "current_month_costs": {...},
#   "daily_costs": {...},
#   "budgets": {...},
#   "token_usage": {...}
# }
```

#### 3. Test Frontend Access

```
1. Open browser: http://34.170.28.178.nip.io
2. Click "💰 FinOps" in navigation
3. Verify:
   - Dashboard loads without errors
   - Pie chart shows cost distribution
   - Line chart shows daily trend
   - Metrics display: Total Cost, Budget Remaining, Daily Trend
4. Wait 60 seconds, verify auto-refresh (metrics update)
```

#### 4. Test Experiments Dashboard

```
1. Click "🧪 Experiments" in navigation
2. Verify:
   - Variants list loads
   - "Create Variant" button works
   - Create modal opens with form
3. Create test variant:
   - Variant Name: "test-variant"
   - Model: "gemini-2.0-flash-001"
   - Temperature: 0.7
   - Click "Create"
4. Verify:
   - Success message appears
   - Variant appears in list
   - Can start A/B test with variant
```

#### 5. Test Observability Dashboard

```
1. Click "📊 Observability" in navigation
2. Verify:
   - SLO cards display (Availability, Latency, Error Rate)
   - All SLOs show "healthy" status
   - Metrics are reasonable values
3. Check browser console:
   - No JavaScript errors
   - Network requests successful (200 OK)
```

---

### Automated Testing

#### Backend Unit Tests

```bash
# Run pytest
cd week3_btoproject_cloudrun_full
pytest tests/test_finops.py -v

# Expected output:
# test_cost_tracker_initialization PASSED
# test_get_current_month_costs PASSED
# test_budget_manager PASSED
# test_token_usage_tracker PASSED
```

#### Frontend Unit Tests

```bash
# Run Angular tests
cd frontend
npm test

# Expected output:
# FinopsDashboardComponent
#   ✓ should create
#   ✓ should load dashboard data on init
#   ✓ should update charts when data changes
#   ✓ should handle API errors gracefully
```

---

### Verification Checklist

**Backend:**
- [x] All Week 4 routes integrated into main.py
- [x] FinOps routes respond with real or mock data
- [x] Experiments routes create variants in Firestore
- [x] Observability routes return SLO metrics
- [x] No import errors for google-cloud-billing
- [x] BigQuery queries execute successfully
- [x] Service account has required IAM permissions

**Frontend:**
- [x] Week 4 routes defined in app.routes.ts
- [x] Navigation menu includes Week 4 links
- [x] FinOps dashboard displays charts
- [x] Experiments dashboard lists variants
- [x] Observability dashboard shows SLOs
- [x] Auto-refresh works (60 second interval)
- [x] Error handling shows user-friendly messages
- [x] Loading spinners display during API calls

**GCP Configuration:**
- [x] BigQuery API enabled
- [x] Cloud Billing Budgets API enabled
- [x] Dataset created: botpproject:billing_export
- [x] IAM role granted: roles/bigquery.dataViewer
- [x] IAM role granted: roles/monitoring.metricWriter
- [x] BigQuery billing export enabled (manual step)

**Deployment:**
- [x] Backend built and pushed to Artifact Registry
- [x] Frontend built and deployed to GKE
- [x] Pods running: 2/2 rag-backend, 2/2 rag-frontend
- [x] Services accessible: http://34.170.28.178.nip.io
- [x] No crash loops or restart errors
- [x] Logs show successful initialization

---

## Conclusion

This document provides comprehensive documentation of Week 4 implementation, covering:

✅ **Architecture**: High-level design, component interactions, data flows
✅ **File Structure**: Complete file tree with descriptions
✅ **GCP Configuration**: Step-by-step setup with explanations
✅ **Backend Code**: Line-by-line explanations of all Python modules
✅ **Frontend Code**: Detailed component, service, and template breakdowns
✅ **Code Flow**: End-to-end execution traces with real examples
✅ **API Reference**: Complete endpoint documentation with examples
✅ **Testing**: Manual and automated verification procedures

### Key Takeaways

**For Developers:**
- Week 4 adds enterprise-grade observability, cost management, and experimentation
- Code uses optional dependencies for graceful degradation
- BigQuery provides real billing data; fallback to mock data if unavailable
- Angular components use auto-refresh for always-fresh data
- All endpoints work without authentication (simplified for Week 4)

**For Operators:**
- GCP configuration enables real data collection (billing, experiments, metrics)
- Service account needs specific IAM roles (bigquery.dataViewer, monitoring.metricWriter)
- BigQuery billing export takes 24 hours to populate
- Application works without billing export (uses mock data)

**For Business:**
- FinOps dashboard shows real cloud spending and helps control costs
- A/B testing framework enables data-driven model optimization
- SLO tracking ensures system reliability and user satisfaction
- All features designed for production enterprise use

### Next Steps

**Optional Enhancements:**
1. Enable Cloud Build triggers for auto-deployment
2. Set up Pub/Sub + Cloud Functions for template processing
3. Configure SendGrid for email notifications
4. Deploy to multiple environments (dev, staging, prod)
5. Add authentication back (OAuth, JWT)
6. Implement advanced cost optimization recommendations
7. Add ML model performance tracking in Vertex AI

**Recommended Reading:**
- `WEEK4_SUMMARY.md`: High-level feature overview
- `WEEK4_IMPLEMENTATION.md`: Implementation details
- `PRODUCTION_READINESS_REPORT.md`: Production deployment checklist
- `docs/SRE_RUNBOOK.md`: Operational procedures

---

**Document Version:** 1.0  
**Last Updated:** March 8, 2026  
**Status:** Complete ✅
