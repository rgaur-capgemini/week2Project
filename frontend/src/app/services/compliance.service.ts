import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ComplianceReport {
  report_id: string;
  document_id: string;
  compliance_score: number;
  report_url: string;
  gaps_count: number;
  status: string;
  created_at: string;
}

export interface ComplianceReportDetail {
  report_id: string;
  document_id: string;
  user_id: string;
  compliance_score: number;
  report: string;
  recommendations: string[];
  gaps: any[];
  matched_sections: any[];
  templates_used: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

export interface TemplateUploadResponse {
  template_id: string;
  status: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class ComplianceService {
  private apiUrl = `${environment.apiUrl}/compliance`;

  constructor(private http: HttpClient) {}

  /**
   * Upload document for compliance checking
   */
  uploadDocument(file: File, templateType?: string): Observable<ComplianceReport> {
    const formData = new FormData();
    formData.append('file', file);
    if (templateType) {
      formData.append('template_type', templateType);
    }
    return this.http.post<ComplianceReport>(`${this.apiUrl}/documents/upload`, formData);
  }

  /**
   * Upload compliance template (admin only)
   */
  uploadTemplate(file: File, templateType: string, version: string): Observable<TemplateUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_type', templateType);
    formData.append('version', version);
    return this.http.post<TemplateUploadResponse>(`${this.apiUrl}/templates/upload`, formData);
  }

  /**
   * Get all compliance reports for current user
   */
  getReports(limit: number = 50, offset: number = 0): Observable<ComplianceReport[]> {
    return this.http.get<ComplianceReport[]>(`${this.apiUrl}/reports`, {
      params: { limit: limit.toString(), offset: offset.toString() }
    });
  }

  /**
   * Get detailed compliance report by ID
   */
  getReport(reportId: string): Observable<ComplianceReportDetail> {
    return this.http.get<ComplianceReportDetail>(`${this.apiUrl}/reports/${reportId}`);
  }

  /**
   * Delete compliance report
   */
  deleteReport(reportId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/reports/${reportId}`);
  }
}
