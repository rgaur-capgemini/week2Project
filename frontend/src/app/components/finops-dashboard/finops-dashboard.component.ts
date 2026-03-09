import { Component, OnInit, OnDestroy } from '@angular/core';
import { FinopsService, CostData, CostForecast, CostAnomaly, TokenUsage, Budget, Alert } from '../../services/finops.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ChartConfiguration, ChartData, ChartType } from 'chart.js';

@Component({
  selector: 'app-finops-dashboard',
  templateUrl: './finops-dashboard.component.html',
  styleUrls: ['./finops-dashboard.component.css']
})
export class FinopsDashboardComponent implements OnInit, OnDestroy {
  // Data
  costs: CostData | null = null;
  forecast: CostForecast | null = null;
  anomalies: CostAnomaly[] = [];
  tokenUsage: TokenUsage | null = null;
  budgets: Budget[] = [];
  alerts: Alert[] = [];
  topUsers: any[] = [];

  // UI State
  loading = true;
  error: string | null = null;
  lastUpdated: Date | null = null;
  autoRefreshEnabled = true;
  refreshInterval = 60000; // 1 minute

  // Subscriptions
  private refreshSubscription?: Subscription;

  // Chart Data
  costChartData: ChartData<'bar'> | null = null;
  tokenChartData: ChartData<'line'> | null = null;
  budgetChartData: ChartData<'doughnut'> | null = null;

  // Chart Options
  costChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Cost by Service (Current Month)' }
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Cost ($)' } }
    }
  };

  tokenChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Token Usage Trend' }
    }
  };

  budgetChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'right' },
      title: { display: true, text: 'Budget Status' }
    }
  };

  constructor(private finopsService: FinopsService) {}

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

    console.log('FinOps Dashboard: Loading data...');

    Promise.all([
      this.finopsService.getCurrentMonthCosts().toPromise().catch(e => { console.error('getCurrentMonthCosts failed:', e); return null; }),
      this.finopsService.getCostForecast().toPromise().catch(e => { console.error('getCostForecast failed:', e); return null; }),
      this.finopsService.getCostAnomalies(7).toPromise().catch(e => { console.error('getCostAnomalies failed:', e); return { anomalies: [] }; }),
      this.finopsService.getVertexAITokens('current_month').toPromise().catch(e => { console.error('getVertexAITokens failed:', e); return null; }),
      this.finopsService.getBudgets().toPromise().catch(e => { console.error('getBudgets failed:', e); return { budgets: [] }; }),
      this.finopsService.getAlerts().toPromise().catch(e => { console.error('getAlerts failed:', e); return { alerts: [] }; }),
      this.finopsService.getTopUsers(10).toPromise().catch(e => { console.error('getTopUsers failed:', e); return { top_users: [] }; })
    ])
      .then(([costs, forecast, anomaliesData, tokens, budgetsData, alertsData, topUsersData]) => {
        console.log('FinOps Dashboard: Data loaded successfully');
        this.costs = costs || null;
        this.forecast = forecast || null;
        this.anomalies = anomaliesData?.anomalies || [];
        this.tokenUsage = tokens || null;
        this.budgets = budgetsData?.budgets || [];
        this.alerts = alertsData?.alerts || [];
        this.topUsers = topUsersData?.top_users || [];

        this.updateCharts();
        this.lastUpdated = new Date();
        this.loading = false;
      })
      .catch(error => {
        console.error('Error loading FinOps data:', error);
        this.error = 'Failed to load dashboard data. Please check the console for details.';
        this.loading = false;
      });
  }

  updateCharts(): void {
    // Update Cost Chart
    if (this.costs && this.costs.service_breakdown) {
      this.costChartData = {
        labels: this.costs.service_breakdown.map(s => s.service),
        datasets: [{
          label: 'Cost ($)',
          data: this.costs.service_breakdown.map(s => s.cost),
          backgroundColor: [
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(255, 159, 64, 0.6)'
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
          ],
          borderWidth: 1
        }]
      };
    }

    // Update Budget Chart
    if (this.budgets && this.budgets.length > 0) {
      this.budgetChartData = {
        labels: this.budgets.map(b => b.name),
        datasets: [{
          label: 'Budget Utilization',
          data: this.budgets.map(b => (b.spent / b.amount) * 100),
          backgroundColor: this.budgets.map(b => {
            const percent = (b.spent / b.amount) * 100;
            if (percent >= 90) return 'rgba(255, 99, 132, 0.6)';
            if (percent >= 75) return 'rgba(255, 206, 86, 0.6)';
            return 'rgba(75, 192, 192, 0.6)';
          }),
          borderWidth: 1
        }]
      };
    }
  }

  startAutoRefresh(): void {
    if (this.autoRefreshEnabled) {
      this.refreshSubscription = interval(this.refreshInterval)
        .pipe(switchMap(() => {
          this.loadAllData();
          return [];
        }))
        .subscribe();
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

  getSeverityClass(severity: string): string {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'severity-high';
      case 'medium':
        return 'severity-medium';
      case 'low':
        return 'severity-low';
      default:
        return 'severity-info';
    }
  }

  getBudgetStatusClass(budget: Budget): string {
    const percent = (budget.spent / budget.amount) * 100;
    if (percent >= 90) return 'budget-critical';
    if (percent >= 75) return 'budget-warning';
    if (percent >= 50) return 'budget-caution';
    return 'budget-ok';
  }

  getBudgetPercentage(budget: Budget): number {
    return Math.round((budget.spent / budget.amount) * 100);
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat('en-US').format(value);
  }

  formatDate(date: string | Date): string {
    return new Date(date).toLocaleString();
  }

  getAnomalySeverityIcon(severity: string): string {
    switch (severity.toLowerCase()) {
      case 'high':
        return '🔴';
      case 'medium':
        return '🟡';
      case 'low':
        return '🟢';
      default:
        return 'ℹ️';
    }
  }
}
