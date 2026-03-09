import { Component, OnInit, OnDestroy } from '@angular/core';
import { ExperimentsService, Variant, VariantResult, FeatureFlag } from '../../services/experiments.service';
import { interval, Subscription } from 'rxjs';
import { ChartData, ChartConfiguration } from 'chart.js';

@Component({
  selector: 'app-experiments-dashboard',
  templateUrl: './experiments-dashboard.component.html',
  styleUrls: ['./experiments-dashboard.component.css']
})
export class ExperimentsDashboardComponent implements OnInit, OnDestroy {
  // Data
  variants: Variant[] = [];
  results: VariantResult[] = [];
  featureFlags: FeatureFlag[] = [];

  // UI State
  loading = true;
  error: string | null = null;
  lastUpdated: Date | null = null;
  autoRefreshEnabled = true;

  // Selected variant for details
  selectedVariant: Variant | null = null;

  // New Variant Form
  showCreateForm = false;
  newVariant = {
    name: '',
    variant_type: 'model',
    config: { model: 'gemini-pro' },
    traffic_weight: 10
  };

  // Subscriptions
  private refreshSubscription?: Subscription;

  // Chart Data
  performanceChartData: ChartData<'bar'> | null = null;
  costChartData: ChartData<'bar'> | null = null;
  trafficChartData: ChartData<'pie'> | null = null;

  // Chart Options
  performanceChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Variant Performance Comparison' }
    },
    scales: {
      y: { beginAtZero: true }
    }
  };

  costChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Cost Comparison by Variant' }
    }
  };

  trafficChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'right' },
      title: { display: true, text: 'Traffic Distribution' }
    }
  };

  constructor(private experimentsService: ExperimentsService) {}

  ngOnInit(): void {
    console.log('Experiments Dashboard Component: ngOnInit called');
    this.loadAllData();
    this.startAutoRefresh();
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
  }

  loadAllData(): void {
    this.loading = true;
    this.error = null;

    console.log('Experiments Dashboard: Loading data...');

    Promise.all([
      this.experimentsService.getVariants().toPromise()
        .catch(e => { console.error('getVariants failed:', e); return null; }),
      this.experimentsService.getResults(7).toPromise()
        .catch(e => { console.error('getResults failed:', e); return null; }),
      this.experimentsService.getFeatureFlags().toPromise()
        .catch(e => { console.error('getFeatureFlags failed:', e); return null; })
    ])
      .then(([variantsData, resultsData, flagsData]) => {
        this.variants = variantsData?.variants || [];
        this.results = resultsData?.results || [];
        this.featureFlags = flagsData?.flags || [];

        console.log('Experiments data loaded:', {
          variants: this.variants.length,
          results: this.results.length,
          flags: this.featureFlags.length
        });

        this.updateCharts();
        this.lastUpdated = new Date();
        this.loading = false;
      })
      .catch(error => {
        console.error('Error loading experiments data:', error);
        this.error = 'Failed to load experiments data. Please try again.';
        this.loading = false;
      });
  }

  updateCharts(): void {
    // Performance Chart
    if (this.results.length > 0) {
      this.performanceChartData = {
        labels: this.results.map(r => r.name),
        datasets: [
          {
            label: 'Success Rate (%)',
            data: this.results.map(r => r.success_rate * 100),
            backgroundColor: 'rgba(52, 168, 83, 0.6)',
            borderColor: 'rgba(52, 168, 83, 1)',
            borderWidth: 1
          },
          {
            label: 'P95 Latency (ms)',
            data: this.results.map(r => r.p95_latency_ms),
            backgroundColor: 'rgba(26, 115, 232, 0.6)',
            borderColor: 'rgba(26, 115, 232, 1)',
            borderWidth: 1
          }
        ]
      };

      // Cost Chart
      this.costChartData = {
        labels: this.results.map(r => r.name),
        datasets: [{
          label: 'Average Cost ($)',
          data: this.results.map(r => r.avg_cost),
          backgroundColor: [
            'rgba(251, 188, 4, 0.6)',
            'rgba(234, 67, 53, 0.6)',
            'rgba(52, 168, 83, 0.6)',
            'rgba(26, 115, 232, 0.6)'
          ],
          borderWidth: 1
        }]
      };
    }

    // Traffic Distribution
    const activeVariants = this.variants.filter(v => v.is_active);
    if (activeVariants.length > 0) {
      this.trafficChartData = {
        labels: activeVariants.map(v => v.name),
        datasets: [{
          data: activeVariants.map(v => v.traffic_weight),
          backgroundColor: [
            'rgba(26, 115, 232, 0.6)',
            'rgba(52, 168, 83, 0.6)',
            'rgba(251, 188, 4, 0.6)',
            'rgba(234, 67, 53, 0.6)',
            'rgba(156, 39, 176, 0.6)'
          ],
          borderWidth: 1
        }]
      };
    }
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

  // Variant Management
  toggleVariant(variant: Variant): void {
    const action = variant.is_active 
      ? this.experimentsService.deactivateVariant(variant.variant_id)
      : this.experimentsService.activateVariant(variant.variant_id);

    action.subscribe(
      () => {
        variant.is_active = !variant.is_active;
      },
      error => {
        console.error('Error toggling variant:', error);
        alert('Failed to toggle variant');
      }
    );
  }

  updateTraffic(variant: Variant, weight: number): void {
    this.experimentsService.updateTraffic(variant.variant_id, weight).subscribe(
      () => {
        variant.traffic_weight = weight;
        this.updateCharts();
      },
      error => {
        console.error('Error updating traffic:', error);
        alert('Failed to update traffic weight');
      }
    );
  }

  createVariant(): void {
    if (!this.newVariant.name) {
      alert('Please enter a variant name');
      return;
    }

    this.experimentsService.createVariant(this.newVariant).subscribe(
      () => {
        this.showCreateForm = false;
        this.resetForm();
        this.loadAllData();
      },
      error => {
        console.error('Error creating variant:', error);
        alert('Failed to create variant');
      }
    );
  }

  resetForm(): void {
    this.newVariant = {
      name: '',
      variant_type: 'model',
      config: { model: 'gemini-pro' },
      traffic_weight: 10
    };
  }

  // Feature Flags
  toggleFeatureFlag(flag: FeatureFlag): void {
    const action = flag.enabled
      ? this.experimentsService.disableFeatureFlag(flag.flag_id)
      : this.experimentsService.enableFeatureFlag(flag.flag_id);

    action.subscribe(
      () => {
        flag.enabled = !flag.enabled;
      },
      error => {
        console.error('Error toggling feature flag:', error);
        alert('Failed to toggle feature flag');
      }
    );
  }

  // Rollout
  rolloutVariant(variant: Variant): void {
    const target = prompt('Enter target traffic weight (0-100):', '50');
    if (target === null) return;

    const targetWeight = parseInt(target, 10);
    if (isNaN(targetWeight) || targetWeight < 0 || targetWeight > 100) {
      alert('Invalid traffic weight. Must be between 0 and 100.');
      return;
    }

    this.experimentsService.rolloutVariant(variant.variant_id, targetWeight, 10, 5).subscribe(
      () => {
        alert(`Gradual rollout started. Traffic will increase by 10% every 5 minutes until reaching ${targetWeight}%`);
        this.loadAllData();
      },
      error => {
        console.error('Error starting rollout:', error);
        alert('Failed to start rollout');
      }
    );
  }

  // Helpers
  getVariantStatusClass(variant: Variant): string {
    return variant.is_active ? 'status-active' : 'status-inactive';
  }

  getSuccessRateClass(rate: number): string {
    if (rate >= 0.99) return 'success-high';
    if (rate >= 0.95) return 'success-medium';
    return 'success-low';
  }

  formatDate(date: string | Date): string {
    return new Date(date).toLocaleString();
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat('en-US').format(value);
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(value);
  }

  formatPercent(value: number): string {
    return `${(value * 100).toFixed(2)}%`;
  }
}
