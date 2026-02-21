import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ComplianceService, ComplianceReportDetail } from '../services/compliance.service';
import { interval } from 'rxjs';

@Component({
  selector: 'app-compliance-report',
  template: `
    <div class="report-container">
      <button mat-icon-button (click)="goBack()" class="back-button">
        <mat-icon>arrow_back</mat-icon>
      </button>
      
      <div *ngIf="loading" class="loading">
        <mat-spinner diameter="60"></mat-spinner>
        <p>Loading report...</p>
      </div>
      
      <div *ngIf="report && report.status === 'processing'" class="processing">
        <mat-spinner diameter="40"></mat-spinner>
        <h3>Processing Document...</h3>
        <p>Your compliance report is being generated. This may take a few minutes.</p>
        <p>The page will automatically refresh when the report is ready.</p>
      </div>
      
      <div *ngIf="report && report.status === 'completed'" class="report-content">
        <!-- Header -->
        <mat-card class="header-card">
          <div class="report-header">
            <div>
              <h1>Compliance Report</h1>
              <p class="document-id">Document ID: {{ report.document_id }}</p>
            </div>
            <div class="score-badge" [class]="getScoreClass(report.compliance_score)">
              <div class="score-value">{{ report.compliance_score.toFixed(1) }}%</div>
              <div class="score-label">Compliance Score</div>
            </div>
          </div>
          
          <div class="report-meta">
            <div><strong>Report ID:</strong> {{ report.report_id }}</div>
            <div><strong>Created:</strong> {{ report.created_at | date:'medium' }}</div>
            <div><strong>Completed:</strong> {{ report.completed_at | date:'medium' }}</div>
            <div><strong>Templates Used:</strong> {{ report.templates_used }}</div>
            <div><strong>Gaps Found:</strong> {{ report.gaps.length }}</div>
          </div>
        </mat-card>
        
        <!-- Recommendations -->
        <mat-card *ngIf="report.recommendations.length > 0" class="recommendations-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>lightbulb</mat-icon>
              Key Recommendations
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <ol class="recommendations-list">
              <li *ngFor="let rec of report.recommendations.slice(0, 10)">{{ rec }}</li>
            </ol>
          </mat-card-content>
        </mat-card>
        
        <!-- Gaps Summary -->
        <mat-card class="gaps-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>warning</mat-icon>
              Identified Gaps ({{ report.gaps.length }})
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <mat-accordion>
              <mat-expansion-panel *ngFor="let gap of report.gaps" [class]="'gap-' + gap.severity">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-chip [color]="getSeverityColor(gap.severity)" class="severity-chip">
                      {{ gap.severity?.toUpperCase() }}
                    </mat-chip>
                    {{ gap.requirement.substring(0, 100) }}...
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <div class="gap-details">
                  <p><strong>Requirement ID:</strong> {{ gap.requirement_id }}</p>
                  <p><strong>Category:</strong> {{ gap.category }}</p>
                  <p><strong>Gap Type:</strong> {{ gap.gap_type }}</p>
                  <p><strong>Requirement:</strong></p>
                  <blockquote>{{ gap.requirement }}</blockquote>
                  <p *ngIf="gap.matched_section"><strong>Matched Section:</strong></p>
                  <blockquote *ngIf="gap.matched_section">{{ gap.matched_section }}</blockquote>
                  <p *ngIf="gap.similarity_score !== undefined">
                    <strong>Similarity Score:</strong> {{ (gap.similarity_score * 100).toFixed(1) }}%
                  </p>
                  <p><strong>Recommendation:</strong></p>
                  <div class="recommendation">{{ gap.recommendation }}</div>
                </div>
              </mat-expansion-panel>
            </mat-accordion>
          </mat-card-content>
        </mat-card>
        
        <!-- Full Report (Markdown) -->
        <mat-card class="full-report-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>description</mat-icon>
              Detailed Report
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="markdown-content" [innerHTML]="getMarkdownHtml()"></div>
          </mat-card-content>
        </mat-card>
        
        <!-- Actions -->
        <div class="actions">
          <button mat-raised-button color="primary" (click)="downloadReport()">
            <mat-icon>download</mat-icon>
            Download Report
          </button>
          <button mat-raised-button (click)="goBack()">
            <mat-icon>arrow_back</mat-icon>
            Back to Reports
          </button>
        </div>
      </div>
      
      <div *ngIf="report && report.status === 'failed'" class="error">
        <mat-icon>error</mat-icon>
        <h3>Report Generation Failed</h3>
        <p>There was an error processing your document.</p>
        <button mat-raised-button color="primary" (click)="goBack()">Back to Reports</button>
      </div>
    </div>
  `,
  styles: [`
    .report-container {
      padding: 20px;
      max-width: 1000px;
      margin: 0 auto;
    }
    
    .back-button {
      margin-bottom: 10px;
    }
    
    .loading, .processing, .error {
      text-align: center;
      padding: 60px 20px;
    }
    
    .header-card {
      margin-bottom: 20px;
    }
    
    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    
    .document-id {
      color: #666;
      font-size: 14px;
    }
    
    .score-badge {
      text-align: center;
      padding: 20px;
      border-radius: 8px;
      min-width: 120px;
    }
    
    .score-badge.excellent { background-color: #4CAF50; color: white; }
    .score-badge.good { background-color: #8BC34A; color: white; }
    .score-badge.fair { background-color: #FFC107; color: white; }
    .score-badge.poor { background-color: #f44336; color: white; }
    
    .score-value {
      font-size: 32px;
      font-weight: bold;
    }
    
    .score-label {
      font-size: 12px;
      text-transform: uppercase;
    }
    
    .report-meta {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      padding: 15px;
      background-color: #f5f5f5;
      border-radius: 4px;
    }
    
    .recommendations-card, .gaps-card, .full-report-card {
      margin-bottom: 20px;
    }
    
    .recommendations-list {
      padding-left: 20px;
    }
    
    .recommendations-list li {
      margin-bottom: 10px;
    }
    
    .severity-chip {
      margin-right: 10px;
    }
    
    .gap-details {
      padding: 15px;
    }
    
    .gap-details blockquote {
      background-color: #f5f5f5;
      padding: 10px;
      border-left: 4px solid #ddd;
      margin: 10px 0;
    }
    
    .recommendation {
      background-color: #e3f2fd;
      padding: 10px;
      border-radius: 4px;
      border-left: 4px solid #2196F3;
    }
    
    .markdown-content {
      line-height: 1.6;
    }
    
    .markdown-content h1, .markdown-content h2, .markdown-content h3 {
      margin-top: 20px;
      margin-bottom: 10px;
    }
    
    .markdown-content ul, .markdown-content ol {
      padding-left: 30px;
    }
    
    .markdown-content blockquote {
      border-left: 4px solid #ddd;
      padding-left: 15px;
      color: #666;
    }
    
    .actions {
      display: flex;
      gap: 10px;
      justify-content: center;
      margin-top: 20px;
    }
    
    .gap-high { border-left: 4px solid #f44336; }
    .gap-medium { border-left: 4px solid #FFC107; }
    .gap-low { border-left: 4px solid #8BC34A; }
  `]
})
export class ComplianceReportComponent implements OnInit {
  report: ComplianceReportDetail | null = null;
  loading = false;
  private pollingInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private complianceService: ComplianceService
  ) {}

  ngOnInit(): void {
    const reportId = this.route.snapshot.paramMap.get('id');
    if (reportId) {
      this.loadReport(reportId);
    }
  }

  ngOnDestroy(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  }

  loadReport(reportId: string): void {
    this.loading = true;
    this.complianceService.getReport(reportId).subscribe({
      next: (data) => {
        this.report = data;
        this.loading = false;
        
        // If still processing, poll for updates
        if (data.status === 'processing') {
          this.startPolling(reportId);
        }
      },
      error: (err) => {
        console.error('Failed to load report:', err);
        this.loading = false;
        alert('Failed to load report: ' + (err.error?.detail || err.message));
      }
    });
  }

  startPolling(reportId: string): void {
    // Poll every 5 seconds
    this.pollingInterval = setInterval(() => {
      this.complianceService.getReport(reportId).subscribe({
        next: (data) => {
          this.report = data;
          // Stop polling if completed or failed
          if (data.status !== 'processing') {
            clearInterval(this.pollingInterval);
          }
        },
        error: (err) => {
          console.error('Polling error:', err);
        }
      });
    }, 5000);
  }

  getScoreClass(score: number): string {
    if (score >= 90) return 'excellent';
    if (score >= 75) return 'good';
    if (score >= 60) return 'fair';
    return 'poor';
  }

  getSeverityColor(severity: string): string {
    switch (severity?.toLowerCase()) {
      case 'high': return 'warn';
      case 'medium': return 'accent';
      case 'low': return 'primary';
      default: return '';
    }
  }

  getMarkdownHtml(): string {
    if (!this.report?.report) return '';
    
    // Simple markdown to HTML conversion (in production, use a proper library like marked.js)
    let html = this.report.report
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/<li>/gim, '<ul><li>')
      .replace(/<\/li>(?![\s]*<li>)/gim, '</li></ul>');
    
    return '<p>' + html + '</p>';
  }

  downloadReport(): void {
    if (!this.report) return;
    
    const blob = new Blob([this.report.report], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance-report-${this.report.report_id}.md`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  goBack(): void {
    this.router.navigate(['/compliance']);
  }
}
