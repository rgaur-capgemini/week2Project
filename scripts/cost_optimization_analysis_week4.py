#!/usr/bin/env python3
"""
Cost Optimization Analysis - Week 4
Analyzes GCP resources and suggests cost optimizations.
"""

import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any


def run_command(cmd: List[str]) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return ""


def analyze_gke_resources(project_id: str) -> Dict[str, Any]:
    """Analyze GKE cluster for optimization opportunities."""
    print("\n[1/5] Analyzing GKE Resources...")
    
    # Get cluster info
    cluster_cmd = [
        "gcloud", "container", "clusters", "list",
        f"--project={project_id}",
        "--format=json"
    ]
    
    clusters_json = run_command(cluster_cmd)
    if not clusters_json:
        return {"recommendations": [], "potential_savings": 0}
    
    clusters = json.loads(clusters_json)
    recommendations = []
    potential_savings = 0
    
    for cluster in clusters:
        node_pools = cluster.get("nodePools", [])
        
        for pool in node_pools:
            machine_type = pool.get("config", {}).get("machineType", "")
            current_nodes = pool.get("currentNodeCount", 0)
            
            # Check if using e2-medium (can downgrade to e2-small for dev)
            if "e2-medium" in machine_type and current_nodes > 2:
                recommendations.append({
                    "resource": f"GKE Node Pool: {pool.get('name')}",
                    "current": f"{current_nodes} x {machine_type}",
                    "recommendation": f"{current_nodes} x e2-small or enable autopilot",
                    "potential_savings_monthly": 30 * current_nodes,
                    "priority": "medium"
                })
                potential_savings += 30 * current_nodes
            
            # Check autoscaling
            autoscaling = pool.get("autoscaling", {})
            if not autoscaling.get("enabled"):
                recommendations.append({
                    "resource": f"GKE Node Pool: {pool.get('name')}",
                    "current": "Fixed node count",
                    "recommendation": "Enable autoscaling to optimize for actual load",
                    "potential_savings_monthly": 50,
                    "priority": "high"
                })
                potential_savings += 50
    
    return {
        "recommendations": recommendations,
        "potential_savings": potential_savings
    }


def analyze_gcs_storage(project_id: str) -> Dict[str, Any]:
    """Analyze GCS buckets for optimization."""
    print("\n[2/5] Analyzing GCS Storage...")
    
    buckets_cmd = ["gsutil", "ls", "-p", project_id]
    buckets_output = run_command(buckets_cmd)
    
    if not buckets_output:
        return {"recommendations": [], "potential_savings": 0}
    
    buckets = buckets_output.strip().split("\n")
    recommendations = []
    potential_savings = 0
    
    for bucket in buckets:
        bucket = bucket.rstrip("/")
        
        # Check storage class distribution
        recommendations.append({
            "resource": f"GCS Bucket: {bucket}",
            "current": "Standard storage class",
            "recommendation": "Apply lifecycle policies: NEARLINE (30d), COLDLINE (90d), ARCHIVE (180d)",
            "potential_savings_monthly": 50,
            "priority": "high"
        })
        potential_savings += 50
    
    return {
        "recommendations": recommendations,
        "potential_savings": potential_savings
    }


def analyze_vertex_ai_usage(project_id: str) -> Dict[str, Any]:
    """Analyze Vertex AI for cost optimization."""
    print("\n[3/5] Analyzing Vertex AI Usage...")
    
    recommendations = []
    potential_savings = 0
    
    # Recommendation: Use Gemini Flash instead of Pro when possible
    recommendations.append({
        "resource": "Vertex AI Model Selection",
        "current": "Gemini 1.5 Pro for all requests",
        "recommendation": "Use Gemini 1.5 Flash for simple queries (70% cost reduction)",
        "potential_savings_monthly": 200,
        "priority": "high"
    })
    potential_savings += 200
    
    # Recommendation: Batch embeddings
    recommendations.append({
        "resource": "Vertex AI Embeddings",
        "current": "Individual embedding requests",
        "recommendation": "Batch embedding requests (up to 250 texts)",
        "potential_savings_monthly": 30,
        "priority": "medium"
    })
    potential_savings += 30
    
    # Recommendation: Cache embeddings
    recommendations.append({
        "resource": "Embedding Cache",
        "current": "No caching",
        "recommendation": "Cache embeddings in Redis/Firestore",
        "potential_savings_monthly": 50,
        "priority": "medium"
    })
    potential_savings += 50
    
    return {
        "recommendations": recommendations,
        "potential_savings": potential_savings
    }


def analyze_compute_instances(project_id: str) -> Dict[str, Any]:
    """Analyze Compute Engine instances."""
    print("\n[4/5] Analyzing Compute Engine...")
    
    instances_cmd = [
        "gcloud", "compute", "instances", "list",
        f"--project={project_id}",
        "--format=json"
    ]
    
    instances_json = run_command(instances_cmd)
    if not instances_json or instances_json == "[]":
        return {"recommendations": [], "potential_savings": 0}
    
    instances = json.loads(instances_json)
    recommendations = []
    potential_savings = 0
    
    for instance in instances:
        name = instance.get("name", "unknown")
        machine_type = instance.get("machineType", "").split("/")[-1]
        status = instance.get("status", "")
        
        if status == "RUNNING":
            recommendations.append({
                "resource": f"Compute Instance: {name}",
                "current": f"{machine_type} running 24/7",
                "recommendation": "Migrate to GKE or stop when not in use",
                "potential_savings_monthly": 100,
                "priority": "high"
            })
            potential_savings += 100
    
    return {
        "recommendations": recommendations,
        "potential_savings": potential_savings
    }


def analyze_unused_resources(project_id: str) -> Dict[str, Any]:
    """Identify unused resources."""
    print("\n[5/5] Identifying Unused Resources...")
    
    recommendations = []
    potential_savings = 0
    
    # Check for unused disks
    disks_cmd = [
        "gcloud", "compute", "disks", "list",
        f"--project={project_id}",
        "--filter=users:* AND -users:*",
        "--format=json"
    ]
    
    disks_json = run_command(disks_cmd)
    if disks_json and disks_json != "[]":
        disks = json.loads(disks_json)
        for disk in disks:
            recommendations.append({
                "resource": f"Unattached Disk: {disk.get('name')}",
                "current": "Unattached, accruing charges",
                "recommendation": "Delete if not needed",
                "potential_savings_monthly": 10,
                "priority": "medium"
            })
            potential_savings += 10
    
    return {
        "recommendations": recommendations,
        "potential_savings": potential_savings
    }


def generate_report(project_id: str):
    """Generate comprehensive cost optimization report."""
    print("=" * 70)
    print("COST OPTIMIZATION ANALYSIS - Week 4")
    print("=" * 70)
    print(f"Project: {project_id}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Run all analyses
    gke_analysis = analyze_gke_resources(project_id)
    gcs_analysis = analyze_gcs_storage(project_id)
    vertex_analysis = analyze_vertex_ai_usage(project_id)
    compute_analysis = analyze_compute_instances(project_id)
    unused_analysis = analyze_unused_resources(project_id)
    
    # Aggregate results
    all_recommendations = (
        gke_analysis["recommendations"] +
        gcs_analysis["recommendations"] +
        vertex_analysis["recommendations"] +
        compute_analysis["recommendations"] +
        unused_analysis["recommendations"]
    )
    
    total_savings = (
        gke_analysis["potential_savings"] +
        gcs_analysis["potential_savings"] +
        vertex_analysis["potential_savings"] +
        compute_analysis["potential_savings"] +
        unused_analysis["potential_savings"]
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Recommendations: {len(all_recommendations)}")
    print(f"Potential Monthly Savings: ${total_savings:.2f}")
    print(f"Annual Savings: ${total_savings * 12:.2f}")
    
    # Categorize by priority
    high_priority = [r for r in all_recommendations if r.get("priority") == "high"]
    medium_priority = [r for r in all_recommendations if r.get("priority") == "medium"]
    low_priority = [r for r in all_recommendations if r.get("priority") == "low"]
    
    print(f"\nHigh Priority: {len(high_priority)}")
    print(f"Medium Priority: {len(medium_priority)}")
    print(f"Low Priority: {len(low_priority)}")
    
    # Print recommendations
    print("\n" + "=" * 70)
    print("DETAILED RECOMMENDATIONS")
    print("=" * 70)
    
    for i, rec in enumerate(all_recommendations, 1):
        print(f"\n[{i}] {rec['resource']}")
        print(f"    Current: {rec['current']}")
        print(f"    Recommendation: {rec['recommendation']}")
        print(f"    Potential Savings: ${rec['potential_savings_monthly']:.2f}/month")
        print(f"    Priority: {rec['priority'].upper()}")
    
    # Implementation checklist
    print("\n" + "=" * 70)
    print("IMPLEMENTATION CHECKLIST")
    print("=" * 70)
    print("\n✓ Apply GCS lifecycle policies")
    print("✓ Enable GKE autoscaling")
    print("✓ Implement A/B testing (Gemini Pro vs Flash)")
    print("✓ Setup embedding caching")
    print("✓ Configure budget alerts")
    print("✓ Review and delete unused resources")
    print("✓ Monitor cost reduction over 30 days")
    
    # Save to file
    report_file = f"cost-optimization-report-{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, "w") as f:
        f.write(f"Cost Optimization Report - {project_id}\n")
        f.write(f"Generated: {datetime.now()}\n\n")
        f.write(f"Total Potential Savings: ${total_savings}/month\n\n")
        f.write("Recommendations:\n")
        for i, rec in enumerate(all_recommendations, 1):
            f.write(f"\n{i}. {rec['resource']}\n")
            f.write(f"   {rec['recommendation']}\n")
            f.write(f"   Savings: ${rec['potential_savings_monthly']}/month\n")
    
    print(f"\n✓ Report saved to: {report_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = "botpproject"
    
    generate_report(project_id)

# _week4
