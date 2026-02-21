import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ComplianceService, ComplianceReport } from '../services/compliance.service';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-compliance',
  template: `
    <div class="compliance-container">
      <h2>Compliance Checker</h2>
      
      <!-- Upload Section -->
      <mat-card class="upload-card">
        <mat-card-header>
          <mat-card-title>Upload Document for Compliance Check</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="upload-form">
            <input 
              type="file" 
              #fileInput 
              (change)="onFileSelected($event)" 
              accept=".pdf,.docx,.txt"
              style="display: none">
            <button mat-raised-button color="primary" (click)="fileInput.click()">
              <mat-icon>upload_file</mat-icon>
              Select Document
            </button>
            <span *ngIf="selectedFile" class="file-name">{{ selectedFile?.name }}</span>
            
            <mat-form-field appearance="outline" class="template-type-field">
              <mat-label>Template Type (Optional)</mat-label>
              <mat-select [(ngModel)]="templateType">
                <mat-option value="">All Templates</mat-option>
                <mat-option value="ISO27001">ISO 27001</mat-option>
                <mat-option value="GDPR">GDPR</mat-option>
                <mat-option value="HIPAA">HIPAA</mat-option>
                <mat-option value="SOC2">SOC 2</mat-option>
                <mat-option value="PCI-DSS">PCI-DSS</mat-option>
              </mat-select>
            </mat-form-field>
            
            <button 
              mat-raised-button 
              color="accent" 
              (click)="uploadDocument()" 
              [disabled]="!selectedFile || uploading">
              <mat-icon>check_circle</mat-icon>
              {{ uploading ? 'Processing...' : 'Check Compliance' }}
            </button>
          </div>
          
          <mat-progress-bar *ngIf="uploading" mode="indeterminate"></mat-progress-bar>
        </mat-card-content>
      </mat-card>
      
      <!-- Reports List -->
      <mat-card class="reports-card">
        <mat-card-header>
          <mat-card-title>Compliance Reports</mat-card-title>
          <button mat-icon-button (click)="loadReports()" [disabled]="loading">
            <mat-icon>refresh</mat-icon>
          </button>
        </mat-card-header>
        <mat-card-content>
          <div *ngIf="loading" class="loading-spinner">
            <mat-spinner diameter="50"></mat-spinner>
          </div>
          
          <table mat-table [dataSource]="reports" *ngIf="!loading" class="reports-table">
            <!-- Document ID Column -->
            <ng-container matColumnDef="document_id">
              <th mat-header-cell *matHeaderCellDef>Document ID</th>
              <td mat-cell *matCellDef="let report">{{ report.document_id.substring(0, 8) }}...</td>
            </ng-container>
            
            <!-- Compliance Score Column -->
            <ng-container matColumnDef="compliance_score">
              <th mat-header-cell *matHeaderCellDef>Score</th>
              <td mat-cell *matCellDef="let report">
                <span [class]="getScoreClass(report.compliance_score)">
                  {{ report.compliance_score.toFixed(1) }}%
                </span>
              </td>
            </ng-container>
            
            <!-- Gaps Column -->
            <ng-container matColumnDef="gaps_count">
              <th mat-header-cell *matHeaderCellDef>Gaps</th>
              <td mat-cell *matCellDef="let report">{{ report.gaps_count }}</td>
            </ng-container>
            
            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let report">
                <mat-chip [color]="getStatusColor(report.status)">{{ report.status }}</mat-chip>
              </td>
            </ng-container>
            
            <!-- Created Date Column -->
            <ng-container matColumnDef="created_at">
              <th mat-header-cell *matHeaderCellDef>Created</th>
              <td mat-cell *matCellDef="let report">{{ report.created_at | date:'short' }}</td>
            </ng-container>
            
            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let report">
                <button mat-icon-button (click)="viewReport(report.report_id)" matTooltip="View Report">
                  <mat-icon>visibility</mat-icon>
                </button>
                <button mat-icon-button (click)="deleteReport(report.report_id)" matTooltip="Delete">
                  <mat-icon>delete</mat-icon>
                </button>
              </td>
            </ng-container>
            
            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
          
          <div *ngIf="!loading && reports.length === 0" class="no-reports">
            <p>No compliance reports yet. Upload a document to get started.</p>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .compliance-container {
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    
    .upload-card, .reports-card {
      margin-bottom: 20px;
    }
    
    .upload-form {
      display: flex;
      gap: 15px;
      align-items: center;
      flex-wrap: wrap;
    }
    
    .file-name {
      font-size: 14px;
      color: #666;
    }
    
    .template-type-field {
      min-width: 200px;
    }
    
    .reports-table {
      width: 100%;
    }
    
    .score-excellent { color: #4CAF50; font-weight: bold; }
    .score-good { color: #8BC34A; font-weight: bold; }
    .score-fair { color: #FFC107; font-weight: bold; }
    .score-poor { color: #f44336; font-weight: bold; }
    
    .loading-spinner {
      display: flex;
      justify-content: center;
      padding: 40px;
    }
    
    .no-reports {
      text-align: center;
      padding: 40px;
      color: #999;
    }
  `]
})
export class ComplianceComponent implements OnInit {
  reports: ComplianceReport[] = [];
  selectedFile: File | null = null;
  templateType: string = '';
  uploading = false;
  loading = false;
  displayedColumns: string[] = ['document_id', 'compliance_score', 'gaps_count', 'status', 'created_at', 'actions'];

  constructor(
    private complianceService: ComplianceService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadReports();
  }

  onFileSelected(event: any): void {
    this.selectedFile = event.target.files[0];
  }

  uploadDocument(): void {
    if (!this.selectedFile) return;

    this.uploading = true;
    this.complianceService.uploadDocument(this.selectedFile, this.templateType || undefined)
      .subscribe({
        next: (response) => {
          console.log('Document uploaded:', response);
          this.uploading = false;
          this.selectedFile = null;
          this.loadReports();
          // Navigate to report view
          this.router.navigate(['/compliance/report', response.report_id]);
        },
        error: (err) => {
          console.error('Upload failed:', err);
          this.uploading = false;
          alert('Upload failed: ' + (err.error?.detail || err.message));
        }
      });
  }

  loadReports(): void {
    this.loading = true;
    this.complianceService.getReports().subscribe({
      next: (data) => {
        this.reports = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load reports:', err);
        this.loading = false;
      }
    });
  }

  viewReport(reportId: string): void {
    this.router.navigate(['/compliance/report', reportId]);
  }

  deleteReport(reportId: string): void {
    if (confirm('Are you sure you want to delete this report?')) {
      this.complianceService.deleteReport(reportId).subscribe({
        next: () => {
          this.loadReports();
        },
        error: (err) => {
          console.error('Delete failed:', err);
          alert('Delete failed: ' + (err.error?.detail || err.message));
        }
      });
    }
  }

  getScoreClass(score: number): string {
    if (score >= 90) return 'score-excellent';
    if (score >= 75) return 'score-good';
    if (score >= 60) return 'score-fair';
    return 'score-poor';
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'processing': return 'accent';
      case 'failed': return 'warn';
      default: return '';
    }
  }
}
