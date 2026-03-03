import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface CostSummary {
  total_cost_usd: number;
  by_service: { [key: string]: number };
  token_costs: {
    total_tokens: number;
    cost_usd: number;
  };
  budget_status: {
    monthly_budget_usd: number;
    current_spend_usd: number;
    remaining_budget_usd: number;
    percent_used: number;
    alert_level: string;
  };
}

interface CostAnomaly {
  service: string;
  current_cost: number;
  baseline_cost: number;
  increase_percent: number;
  reason: string;
  recommendation: string;
}

@Component({
  selector: 'app-finops-dashboard',
  templateUrl: './finops-dashboard.component.html',
  styleUrls: ['./finops-dashboard.component.scss']
})
export class FinopsDashboardComponent implements OnInit {
  costSummary: CostSummary | null = null;
  anomalies: CostAnomaly[] = [];
  loading = true;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadFinOpsData();
    this.loadAnomalies();
  }

  loadFinOpsData(): void {
    this.loading = true;
    this.http.get<CostSummary>(`${environment.apiUrl}/finops/dashboard`)
      .subscribe({
        next: (data) => {
          this.costSummary = data;
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load FinOps data';
          this.loading = false;
          console.error(err);
        }
      });
  }

  loadAnomalies(): void {
    this.http.get<CostAnomaly[]>(`${environment.apiUrl}/finops/anomalies`)
      .subscribe({
        next: (data) => {
          this.anomalies = data;
        },
        error: (err) => {
          console.error('Failed to load anomalies:', err);
        }
      });
  }

  getBudgetColor(): string {
    if (!this.costSummary) return 'primary';
    const percent = this.costSummary.budget_status.percent_used;
    if (percent >= 100) return 'warn';
    if (percent >= 75) return 'accent';
    return 'primary';
  }

  getAlertLevelClass(): string {
    if (!this.costSummary) return '';
    return this.costSummary.budget_status.alert_level.toLowerCase();
  }

  getServiceCostEntries() {
    if (!this.costSummary) return [];
    return Object.entries(this.costSummary.by_service);
  }

  refresh(): void {
    this.loadFinOpsData();
    this.loadAnomalies();
  }
}
