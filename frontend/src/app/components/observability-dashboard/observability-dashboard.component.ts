import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { interval, Subscription } from 'rxjs';
import { ChartData, ChartConfiguration } from 'chart.js';

interface SLO {
  name: string;
  target: number;
  current: number;
  status: string;
  error_budget_remaining: number;
}

interface ErrorBudget {
  service: string;
  slo_target: number;
  error_budget: number;
  consumed: number;
  remaining: number;
  burn_rate: number;
  status: string;
}

interface SyntheticCheck {
  endpoint: string;
  status: string;
  latency_ms: number;
  last_check: string;
  uptime_percentage: number;
}

interface Alert {
  alert_id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
}

@Component({
  selector: 'app-observability-dashboard',
  templateUrl: './observability-dashboard.component.html',
  styleUrls: ['./observability-dashboard.component.css']
})
export class ObservabilityDashboardComponent implements OnInit, OnDestroy {
  // Data
  slos: SLO[] = [];
  errorBudgets: ErrorBudget[] = [];
  syntheticChecks: SyntheticCheck[] = [];
  alerts: Alert[] = [];
  
  // Metrics
  apiAvailability = 0;
  p95Latency = 0;
  p99Latency = 0;
  errorRate = 0;

  // UI State
  loading = true;
  error: string | null = null;
  lastUpdated: Date | null = null;
  autoRefreshEnabled = true;

  // Subscriptions
  private refreshSubscription?: Subscription;

  // Chart Data
  availabilityChartData: ChartData<'line'> | null = null;
  latencyChartData: ChartData<'line'> | null = null;
  errorBudgetChartData: ChartData<'bar'> | null = null;

  // Chart Options
  availabilityChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'API Availability (Last 24h)' }
    },
    scales: {
      y: { min: 95, max: 100, title: { display: true, text: 'Availability (%)' } }
    }
  };

  latencyChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Latency Percentiles' }
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Latency (ms)' } }
    }
  };

  errorBudgetChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Error Budget Status' }
    },
    scales: {
      y: { beginAtZero: true, max: 100, title: { display: true, text: 'Remaining (%)' } }
    }
  };

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadAllData();
    this.startAutoRefresh();
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
  }

  loadAllData(): void {
    this.loading = true;
    this.error = null;

    // Mock data for now - replace with actual API calls
    Promise.resolve().then(() => {
      // Mock SLOs
      this.slos = [
        { name: 'API Availability', target: 99.9, current: 99.95, status: 'healthy', error_budget_remaining: 0.08 },
        { name: 'P95 Latency', target: 500, current: 342, status: 'healthy', error_budget_remaining: 0.32 },
        { name: 'P99 Latency', target: 1000, current: 678, status: 'healthy', error_budget_remaining: 0.32 },
        { name: 'Error Rate', target: 0.1, current: 0.05, status: 'healthy', error_budget_remaining: 0.5 }
      ];

      // Mock Error Budgets
      this.errorBudgets = [
        { service: 'rag-chatbot-api', slo_target: 99.9, error_budget: 0.1, consumed: 0.02, remaining: 0.08, burn_rate: 0.5, status: 'healthy' },
        { service: 'document-ingestion', slo_target: 99.5, error_budget: 0.5, consumed: 0.15, remaining: 0.35, burn_rate: 0.8, status: 'warning' },
        { service: 'compliance-checker', slo_target: 99.0, error_budget: 1.0, consumed: 0.3, remaining: 0.7, burn_rate: 0.6, status: 'healthy' },
        { service: 'vertex-ai-embeddings', slo_target: 99.9, error_budget: 0.1, consumed: 0.01, remaining: 0.09, burn_rate: 0.2, status: 'healthy' }
      ];

      // Mock Synthetic Checks
      this.syntheticChecks = [
        { endpoint: '/health', status: 'up', latency_ms: 45, last_check: new Date().toISOString(), uptime_percentage: 100 },
        { endpoint: '/chat', status: 'up', latency_ms: 234, last_check: new Date().toISOString(), uptime_percentage: 99.98 },
        { endpoint: '/compliance/check', status: 'up', latency_ms: 567, last_check: new Date().toISOString(), uptime_percentage: 99.85 },
        { endpoint: '/documents/upload', status: 'up', latency_ms: 123, last_check: new Date().toISOString(), uptime_percentage: 99.92 }
      ];

      // Mock Alerts
      this.alerts = [
        { alert_id: '1', type: 'error_budget', severity: 'warning', message: 'document-ingestion error budget at 70% consumption', timestamp: new Date(Date.now() - 3600000).toISOString() }
      ];

      // Metrics
      this.apiAvailability = 99.95;
      this.p95Latency = 342;
      this.p99Latency = 678;
      this.errorRate = 0.05;

      this.updateCharts();
      this.lastUpdated = new Date();
      this.loading = false;
    });
  }

  updateCharts(): void {
    // Availability Chart (mock data - 24 data points)
    const hours = Array.from({length: 24}, (_, i) => `${23-i}h ago`).reverse();
    this.availabilityChartData = {
      labels: hours,
      datasets: [{
        label: 'Availability (%)',
        data: Array.from({length: 24}, () => 99.9 + Math.random() * 0.1),
        borderColor: 'rgba(52, 168, 83, 1)',
        backgroundColor: 'rgba(52, 168, 83, 0.1)',
        fill: true,
        tension: 0.4
      }]
    };

    // Latency Chart
    this.latencyChartData = {
      labels: hours,
      datasets: [
        {
          label: 'P50',
          data: Array.from({length: 24}, () => 150 + Math.random() * 50),
          borderColor: 'rgba(26, 115, 232, 1)',
          backgroundColor: 'rgba(26, 115, 232, 0.1)',
          tension: 0.4
        },
        {
          label: 'P95',
          data: Array.from({length: 24}, () => 300 + Math.random() * 100),
          borderColor: 'rgba(251, 188, 4, 1)',
          backgroundColor: 'rgba(251, 188, 4, 0.1)',
          tension: 0.4
        },
        {
          label: 'P99',
          data: Array.from({length: 24}, () => 600 + Math.random() * 150),
          borderColor: 'rgba(234, 67, 53, 1)',
          backgroundColor: 'rgba(234, 67, 53, 0.1)',
          tension: 0.4
        }
      ]
    };

    // Error Budget Chart
    this.errorBudgetChartData = {
      labels: this.errorBudgets.map(eb => eb.service),
      datasets: [{
        label: 'Remaining (%)',
        data: this.errorBudgets.map(eb => (eb.remaining / eb.error_budget) * 100),
        backgroundColor: this.errorBudgets.map(eb => {
          const percent = (eb.remaining / eb.error_budget) * 100;
          if (percent < 20) return 'rgba(234, 67, 53, 0.6)';
          if (percent < 50) return 'rgba(251, 188, 4, 0.6)';
          return 'rgba(52, 168, 83, 0.6)';
        }),
        borderWidth: 1
      }]
    };
  }

  startAutoRefresh(): void {
    if (this.autoRefreshEnabled) {
      this.refreshSubscription = interval(30000) // 30 seconds
        .subscribe(() => this.loadAllData());
    }
  }

  stopAutoRefresh(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  toggleAutoRefresh(): void {
    this.autoRefreshEnabled = !this.autoRefreshEnabled;
    if (this.autoRefreshEnabled) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
  }

  refresh(): void {
    this.loadAllData();
  }

  getSLOStatusClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'healthy': return 'status-healthy';
      case 'warning': return 'status-warning';
      case 'critical': return 'status-critical';
      default: return 'status-unknown';
    }
  }

  getErrorBudgetStatusClass(budget: ErrorBudget): string {
    const remaining = (budget.remaining / budget.error_budget) * 100;
    if (remaining < 20) return 'budget-critical';
    if (remaining < 50) return 'budget-warning';
    return 'budget-healthy';
  }

  getCheckStatusClass(status: string): string {
    return status === 'up' ? 'check-up' : 'check-down';
  }

  getSeverityClass(severity: string): string {
    switch (severity.toLowerCase()) {
      case 'critical': return 'severity-critical';
      case 'high': return 'severity-high';
      case 'warning': return 'severity-warning';
      case 'medium': return 'severity-medium';
      default: return 'severity-low';
    }
  }

  formatDate(date: string | Date): string {
    return new Date(date).toLocaleString();
  }

  formatNumber(value: number, decimals: number = 2): string {
    return value.toFixed(decimals);
  }

  formatPercent(value: number): string {
    return `${value.toFixed(2)}%`;
  }
}
