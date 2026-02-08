/**
 * GKE-based RAG Chatbot Infrastructure
 * Production-grade deployment with 99.9% availability
 */

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "gcs" {
    bucket = "btoproject-486405-terraform-state"
    prefix = "rag-chatbot"
  }
}

# ====================  Provider Configuration ====================

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "kubernetes" {
  host  = "https://${google_container_cluster.main.endpoint}"
  token = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.main.master_auth[0].cluster_ca_certificate
  )
}

data "google_client_config" "default" {}

# ==================== Variables ====================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "btoproject-486405-486604"
}

variable "project_number" {
  description = "GCP Project Number"
  type        = string
  default     = "382685100652"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "production"
}

# ==================== Enable APIs ====================

resource "google_project_service" "services" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "aiplatform.googleapis.com",
    "storage-api.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "redis.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "servicenetworking.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "firestore.googleapis.com",
  ])
  
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# ==================== VPC Network ====================

resource "google_compute_network" "vpc" {
  name                    = "chatbot-rag-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
  
  depends_on = [google_project_service.services]
}

resource "google_compute_subnetwork" "gke_subnet" {
  name          = "gke-subnet"
  ip_cidr_range = "10.0.0.0/20"
  region        = var.region
  network       = google_compute_network.vpc.id
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.4.0.0/14"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.8.0.0/20"
  }
  
  private_ip_google_access = true
}

# Cloud Router and NAT for private GKE nodes
resource "google_compute_router" "router" {
  name    = "gke-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name   = "gke-nat"
  router = google_compute_router.router.name
  region = var.region
  
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ==================== GKE Cluster ====================

resource "google_container_cluster" "main" {
  name     = "rag-chatbot-cluster"
  location = var.region
  project  = var.project_id
  
  # We can't create a cluster with no node pool, so we create the smallest possible default node pool and immediately delete it
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.gke_subnet.name
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false  # Keep endpoint public for CI/CD access
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  # IP allocation policy
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  
  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Release channel for automatic updates
  release_channel {
    channel = "REGULAR"
  }
  
  # Logging and monitoring
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"
  
  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"  # 3 AM UTC
    }
  }
  
  # Addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }
  
  # Network policy
  network_policy {
    enabled = true
  }
  
  # Binary authorization (for security)
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
  
  depends_on = [
    google_project_service.services,
    google_compute_subnetwork.gke_subnet
  ]
}

# ==================== GKE Node Pools ====================

# Backend node pool
resource "google_container_node_pool" "backend_pool" {
  name       = "backend-pool"
  cluster    = google_container_cluster.main.name
  location   = var.region
  node_count = 2  # Minimum for HA
  
  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  node_config {
    machine_type = "n2-standard-4"  # 4 vCPUs, 16 GB RAM
    disk_size_gb = 100
    disk_type    = "pd-standard"
    
    labels = {
      workload = "backend"
      env      = var.environment
    }
    
    tags = ["gke-node", "backend"]
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Shielded instance config
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }
}

# Frontend node pool
resource "google_container_node_pool" "frontend_pool" {
  name       = "frontend-pool"
  cluster    = google_container_cluster.main.name
  location   = var.region
  node_count = 2
  
  autoscaling {
    min_node_count = 2
    max_node_count = 5
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  node_config {
    machine_type = "n2-standard-2"  # 2 vCPUs, 8 GB RAM
    disk_size_gb = 50
    disk_type    = "pd-standard"
    
    labels = {
      workload = "frontend"
      env      = var.environment
    }
    
    tags = ["gke-node", "frontend"]
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }
}

# ==================== Redis (Memorystore) ====================

resource "google_redis_instance" "cache" {
  name           = "rag-chatbot-redis"
  tier           = "STANDARD_HA"  # High availability
  memory_size_gb = 5
  region         = var.region
  
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  
  redis_version = "REDIS_7_0"
  display_name  = "RAG Chatbot Redis"
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }
  
  depends_on = [google_project_service.services]
}

# ==================== Service Accounts ====================

# Backend service account
resource "google_service_account" "backend" {
  account_id   = "rag-backend-sa"
  display_name = "RAG Backend Service Account"
  project      = var.project_id
}

# Backend IAM roles
resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/aiplatform.user",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/firestore.user",
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Frontend service account
resource "google_service_account" "frontend" {
  account_id   = "rag-frontend-sa"
  display_name = "RAG Frontend Service Account"
  project      = var.project_id
}

# Workload Identity binding for backend
resource "google_service_account_iam_binding" "backend_workload_identity" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/rag-backend]"
  ]
}

# Workload Identity binding for frontend
resource "google_service_account_iam_binding" "frontend_workload_identity" {
  service_account_id = google_service_account.frontend.name
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/rag-frontend]"
  ]
}

# ==================== Secrets ====================

# OAuth Client ID
resource "google_secret_manager_secret" "oauth_client_id" {
  secret_id = "oauth-client-id"
  project   = var.project_id
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.services]
}

# OAuth Client Secret
resource "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "oauth-client-secret"
  project   = var.project_id
  
  replication {
    auto {}
  }
}

# JWT Secret
resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret"
  project   = var.project_id
  
  replication {
    auto {}
  }
}

# Redis Password (if needed)
resource "google_secret_manager_secret" "redis_password" {
  secret_id = "redis-password"
  project   = var.project_id
  
  replication {
    auto {}
  }
}

# ==================== GCS Buckets ====================

# Documents bucket
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-rag-documents"
  location      = var.region
  project       = var.project_id
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# ==================== Outputs ====================

output "gke_cluster_name" {
  value       = google_container_cluster.main.name
  description = "GKE cluster name"
}

output "gke_cluster_endpoint" {
  value       = google_container_cluster.main.endpoint
  description = "GKE cluster endpoint"
  sensitive   = true
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis host IP"
}

output "redis_port" {
  value       = google_redis_instance.cache.port
  description = "Redis port"
}

output "backend_service_account_email" {
  value       = google_service_account.backend.email
  description = "Backend service account email"
}

output "frontend_service_account_email" {
  value       = google_service_account.frontend.email
  description = "Frontend service account email"
}

output "vpc_network" {
  value       = google_compute_network.vpc.name
  description = "VPC network name"
}

output "gcs_bucket_documents" {
  value       = google_storage_bucket.documents.name
  description = "GCS bucket for documents"
}
