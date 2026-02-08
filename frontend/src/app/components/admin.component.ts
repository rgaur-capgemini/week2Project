import { Component, OnInit } from '@angular/core';
import { AnalyticsService } from '../services/analytics.service';
import { UsageStats, LatencyStats, SystemOverview, UserActivity } from '../models/models';

@Component({
  selector: 'app-admin',
  template: `
    <div class="admin-container">
      <h1>Admin Dashboard</h1>
      
      <mat-tab-group>
        <mat-tab label="System Overview">
          <div class="tab-content">
            <div *ngIf="systemOverview" class="stats-grid">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Total Requests</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <h2>{{ systemOverview.total_requests | number }}</h2>
                </mat-card-content>
              </mat-card>
              
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Total Users</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <h2>{{ systemOverview.total_users | number }}</h2>
                </mat-card-content>
              </mat-card>
              
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Error Rate</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <h2>{{ (systemOverview.error_rate * 100).toFixed(2) }}%</h2>
                </mat-card-content>
              </mat-card>
              
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Avg Latency</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <h2>{{ systemOverview.avg_latency_ms.toFixed(0) }}ms</h2>
                </mat-card-content>
              </mat-card>
            </div>
            
            <button mat-raised-button color="primary" (click)="loadSystemOverview()">
              <mat-icon>refresh</mat-icon>
              Refresh
            </button>
          </div>
        </mat-tab>
        
        <mat-tab label="Usage Statistics">
          <div class="tab-content">
            <div class="date-filters">
              <mat-form-field>
                <mat-label>Start Date</mat-label>
                <input matInput [matDatepicker]="startPicker" [(ngModel)]="startDate">
                <mat-datepicker-toggle matIconSuffix [for]="startPicker"></mat-datepicker-toggle>
                <mat-datepicker #startPicker></mat-datepicker>
              </mat-form-field>
              
              <mat-form-field>
                <mat-label>End Date</mat-label>
                <input matInput [matDatepicker]="endPicker" [(ngModel)]="endDate">
                <mat-datepicker-toggle matIconSuffix [for]="endPicker"></mat-datepicker-toggle>
                <mat-datepicker #endPicker></mat-datepicker>
              </mat-form-field>
              
              <button mat-raised-button color="primary" (click)="loadUsageStats()">
                Load Stats
              </button>
            </div>
            
            <table mat-table [dataSource]="usageStats" *ngIf="usageStats.length > 0">
              <ng-container matColumnDef="endpoint">
                <th mat-header-cell *matHeaderCellDef>Endpoint</th>
                <td mat-cell *matCellDef="let stat">{{ stat.endpoint }}</td>
              </ng-container>
              
              <ng-container matColumnDef="total_calls">
                <th mat-header-cell *matHeaderCellDef>Total Calls</th>
                <td mat-cell *matCellDef="let stat">{{ stat.total_calls | number }}</td>
              </ng-container>
              
              <ng-container matColumnDef="unique_users">
                <th mat-header-cell *matHeaderCellDef>Unique Users</th>
                <td mat-cell *matCellDef="let stat">{{ stat.unique_users | number }}</td>
              </ng-container>
              
              <ng-container matColumnDef="error_rate">
                <th mat-header-cell *matHeaderCellDef>Error Rate</th>
                <td mat-cell *matCellDef="let stat">{{ (stat.error_rate * 100).toFixed(2) }}%</td>
              </ng-container>
              
              <ng-container matColumnDef="avg_tokens">
                <th mat-header-cell *matHeaderCellDef>Avg Tokens</th>
                <td mat-cell *matCellDef="let stat">{{ stat.avg_tokens.toFixed(0) }}</td>
              </ng-container>
              
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </div>
        </mat-tab>
        
        <mat-tab label="Latency">
          <div class="tab-content">
            <mat-form-field>
              <mat-label>Select Endpoint</mat-label>
              <mat-select [(ngModel)]="selectedEndpoint">
                <mat-option value="/query">Query</mat-option>
                <mat-option value="/ingest">Ingest</mat-option>
                <mat-option value="/evaluate">Evaluate</mat-option>
              </mat-select>
            </mat-form-field>
            
            <button mat-raised-button color="primary" (click)="loadLatencyStats()">
              Load Latency Stats
            </button>
            
            <div *ngIf="latencyStats" class="stats-grid">
              <mat-card>
                <mat-card-header><mat-card-title>P50</mat-card-title></mat-card-header>
                <mat-card-content><h2>{{ latencyStats.p50.toFixed(0) }}ms</h2></mat-card-content>
              </mat-card>
              <mat-card>
                <mat-card-header><mat-card-title>P95</mat-card-title></mat-card-header>
                <mat-card-content><h2>{{ latencyStats.p95.toFixed(0) }}ms</h2></mat-card-content>
              </mat-card>
              <mat-card>
                <mat-card-header><mat-card-title>P99</mat-card-title></mat-card-header>
                <mat-card-content><h2>{{ latencyStats.p99.toFixed(0) }}ms</h2></mat-card-content>
              </mat-card>
              <mat-card>
                <mat-card-header><mat-card-title>Average</mat-card-title></mat-card-header>
                <mat-card-content><h2>{{ latencyStats.avg.toFixed(0) }}ms</h2></mat-card-content>
              </mat-card>
            </div>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .admin-container {
      padding: 20px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .tab-content {
      padding: 20px;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin: 20px 0;
    }
    .stats-grid h2 {
      font-size: 2em;
      margin: 10px 0;
      color: #3f51b5;
    }
    .date-filters {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-bottom: 20px;
    }
    table {
      width: 100%;
      margin-top: 20px;
    }
  `]
})
export class AdminComponent implements OnInit {
  systemOverview: SystemOverview | null = null;
  usageStats: UsageStats[] = [];
  latencyStats: LatencyStats | null = null;
  startDate: Date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  endDate: Date = new Date();
  selectedEndpoint = '/query';
  displayedColumns: string[] = ['endpoint', 'total_calls', 'unique_users', 'error_rate', 'avg_tokens'];

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit(): void {
    this.loadSystemOverview();
  }

  loadSystemOverview(): void {
    this.analyticsService.getSystemOverview().subscribe({
      next: (data) => this.systemOverview = data,
      error: (err) => console.error('Failed to load overview:', err)
    });
  }

  loadUsageStats(): void {
    this.analyticsService.getUsageStats(
      this.startDate.toISOString(),
      this.endDate.toISOString()
    ).subscribe({
      next: (data) => this.usageStats = data,
      error: (err) => console.error('Failed to load usage stats:', err)
    });
  }

  loadLatencyStats(): void {
    this.analyticsService.getLatencyStats(this.selectedEndpoint).subscribe({
      next: (data) => this.latencyStats = data,
      error: (err) => console.error('Failed to load latency stats:', err)
    });
  }
}
