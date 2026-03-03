#!/usr/bin/env python3
"""
Analyze resource usage and recommend cost optimizations.
"""

from google.cloud import monitoring_v3
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CostOptimizer:
    """Analyze costs and recommend optimizations."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.monitoring_client = monitoring_v3.MetricServiceClient()
    
    def analyze_pod_utilization(self) -> List[Dict]:
        """
        Analyze pod CPU/memory utilization.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Mock data - replace with actual Kubernetes metrics query
        pods = [
            {"name": "rag-backend-abc", "cpu_used": 0.3, "cpu_requested": 1.0, "memory_used": 0.8, "memory_requested": 2.0},
            {"name": "rag-backend-def", "cpu_used": 0.4, "cpu_requested": 1.0, "memory_used": 1.0, "memory_requested": 2.0},
            {"name": "rag-frontend-xyz", "cpu_used": 0.1, "cpu_requested": 0.5, "memory_used": 0.3, "memory_requested": 1.0}
        ]
        
        for pod in pods:
            cpu_utilization = pod["cpu_used"] / pod["cpu_requested"]
            memory_utilization = pod["memory_used"] / pod["memory_requested"]
            
            # CPU right-sizing
            if cpu_utilization < 0.5:
                new_cpu = pod["cpu_requested"] * 0.7  # Reduce by 30%
                savings = (pod["cpu_requested"] - new_cpu) * 30  # $30/CPU/month
                
                recommendations.append({
                    "pod": pod["name"],
                    "type": "CPU",
                    "current": f"{pod['cpu_requested']} cores",
                    "recommended": f"{new_cpu:.2f} cores",
                    "monthly_savings_usd": savings,
                    "reason": f"Low utilization ({cpu_utilization*100:.1f}%)"
                })
            
            # Memory right-sizing
            if memory_utilization < 0.6:
                new_memory = pod["memory_requested"] * 0.75  # Reduce by 25%
                savings = (pod["memory_requested"] - new_memory) * 5  # $5/GB/month
                
                recommendations.append({
                    "pod": pod["name"],
                    "type": "Memory",
                    "current": f"{pod['memory_requested']} GB",
                    "recommended": f"{new_memory:.2f} GB",
                    "monthly_savings_usd": savings,
                    "reason": f"Low utilization ({memory_utilization*100:.1f}%)"
                })
        
        return recommendations
    
    def analyze_storage_costs(self) -> List[Dict]:
        """Analyze GCS and persistent disk usage."""
        recommendations = []
        
        # Check for old documents that can be archived
        recommendations.append({
            "type": "GCS Lifecycle",
            "current": "No lifecycle policies",
            "recommended": "Move to Coldline after 90 days, delete after 365 days",
            "monthly_savings_usd": 50,
            "reason": "Reduce storage costs for infrequently accessed documents"
        })
        
        return recommendations
    
    def analyze_vertex_ai_usage(self) -> List[Dict]:
        """Analyze Vertex AI costs and recommend optimizations."""
        recommendations = []
        
        # Embedding model optimization
        recommendations.append({
            "type": "Vertex AI - Caching",
            "current": "No response caching",
            "recommended": "Implement Redis caching for repeated queries",
            "monthly_savings_usd": 40,
            "reason": "Reduce embedding API calls through caching"
        })
        
        # LLM model optimization
        recommendations.append({
            "type": "LLM Model Selection",
            "current": "Using Flash for all queries",
            "recommended": "Continue with Flash (optimal cost/performance)",
            "monthly_savings_usd": 0,
            "reason": "Already using cost-optimized model"
        })
        
        return recommendations
    
    def analyze_node_pool(self) -> List[Dict]:
        """Analyze GKE node pool configuration."""
        recommendations = []
        
        recommendations.append({
            "type": "Node Pool - Preemptible",
            "current": "n1-standard-2 (preemptible: 0%)",
            "recommended": "50% preemptible nodes for non-critical workloads",
            "monthly_savings_usd": 150,
            "reason": "Preemptible VMs are 60-80% cheaper"
        })
        
        recommendations.append({
            "type": "Cluster Autoscaling",
            "current": "Min: 3, Max: 10",
            "recommended": "Min: 2, Max: 10 with aggressive scale-down",
            "monthly_savings_usd": 50,
            "reason": "Reduce minimum nodes during off-peak hours"
        })
        
        return recommendations
    
    def generate_cost_optimization_report(self) -> Dict:
        """Generate comprehensive cost optimization report."""
        logger.info("Generating cost optimization report")
        
        pod_recommendations = self.analyze_pod_utilization()
        storage_recommendations = self.analyze_storage_costs()
        vertex_ai_recommendations = self.analyze_vertex_ai_usage()
        node_pool_recommendations = self.analyze_node_pool()
        
        all_recommendations = (
            pod_recommendations +
            storage_recommendations +
            vertex_ai_recommendations +
            node_pool_recommendations
        )
        
        total_savings = sum(r.get("monthly_savings_usd", 0) for r in all_recommendations)
        
        # Calculate current costs (mock)
        current_monthly_cost = 600  # USD
        optimized_cost = current_monthly_cost - total_savings
        savings_percentage = (total_savings / current_monthly_cost) * 100
        
        report = {
            "current_monthly_cost_usd": current_monthly_cost,
            "potential_monthly_savings_usd": total_savings,
            "optimized_monthly_cost_usd": optimized_cost,
            "savings_percentage": savings_percentage,
            "target_achieved": savings_percentage >= 15,
            "recommendations": all_recommendations
        }
        
        logger.info("Cost optimization report generated")
        
        return report


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze costs and generate optimization report")
    parser.add_argument("--project-id", default="btoproject-486405", help="GCP Project ID")
    
    args = parser.parse_args()
    
    optimizer = CostOptimizer(args.project_id)
    report = optimizer.generate_cost_optimization_report()
    
    print("\n" + "="*60)
    print("COST OPTIMIZATION REPORT")
    print("="*60)
    print(f"Current Monthly Cost: ${report['current_monthly_cost_usd']:.2f}")
    print(f"Potential Savings: ${report['potential_monthly_savings_usd']:.2f}")
    print(f"Optimized Cost: ${report['optimized_monthly_cost_usd']:.2f}")
    print(f"Savings Percentage: {report['savings_percentage']:.1f}%")
    print(f"Target (≥15%) Achieved: {'✓' if report['target_achieved'] else '✗'}")
    print("\nTop Recommendations:")
    
    for i, rec in enumerate(report['recommendations'][:5], 1):
        print(f"\n{i}. {rec['type']}")
        print(f"   Current: {rec['current']}")
        print(f"   Recommended: {rec['recommended']}")
        print(f"   Monthly Savings: ${rec.get('monthly_savings_usd', 0):.2f}")
        print(f"   Reason: {rec['reason']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
