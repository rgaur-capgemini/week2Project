import { Component, OnInit, OnDestroy } from '@angular/core';
import { ObservabilityService, SLO, ErrorBudget, SyntheticCheck, Alert } from '../../services/observability.service';
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

  constructor(private observabilityService: ObservabilityService) {}

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

    console.log('Observability Dashboard: Loading data...');

    Promise.all([
      this.observabilityService.getSLOs().toPromise()
        .catch(e => { console.error('getSLOs failed:', e); return null; }),
      this.observabilityService.getErrorBudgets().toPromise()
        .catch(e => { console.error('getErrorBudgets failed:', e); return null; }),
      this.observabilityService.getSyntheticChecks().toPromise()
        .catch(e => { console.error('getSyntheticChecks failed:', e); return null; }),
      this.observabilityService.getAlerts().toPromise()
        .catch(e => { console.error('getAlerts failed:', e); return null; })
    ])
      .then(([sloData, budgetData, checksData, alertsData]) => {
        this.slos = sloData?.slos || [];
        this.errorBudgets = budgetData?.error_budgets || [];
        this.syntheticChecks = checksData?.synthetic_checks || [];
        this.alerts = alertsData?.alerts || [];

        // Update metrics from SLOs
        if (this.slos.length > 0) {
          const availabilitySLO = this.slos.find(s => s.name === 'API Availability');
          const p95SLO = this.slos.find(s => s.name === 'P95 Latency');
          const p99SLO = this.slos.find(s => s.name === 'P99 Latency');
          const errorRateSLO = this.slos.find(s => s.name === 'Error Rate');

          if (availabilitySLO) this.apiAvailability = availabilitySLO.current;
          if (p95SLO) this.p95Latency = p95SLO.current;
          if (p99SLO) this.p99Latency = p99SLO.current;
          if (errorRateSLO) this.errorRate = errorRateSLO.current;
        }

        console.log('Observability data loaded:', {
          slos: this.slos.length,
          errorBudgets: this.errorBudgets.length,
          syntheticChecks: this.syntheticChecks.length,
          alerts: this.alerts.length
        });

        this.updateCharts();
        this.lastUpdated = new Date();
        this.loading = false;
      })
      .catch(error => {
        console.error('Error loading observability data:', error);
        this.error = 'Failed to load observability data. Please try again.';
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
