import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface SLO {
  name: string;
  target: number;
  current: number;
  status: string;
  error_budget_remaining: number;
}

export interface ErrorBudget {
  service: string;
  slo_target: number;
  error_budget: number;
  consumed: number;
  remaining: number;
  burn_rate: number;
  status: string;
}

export interface SyntheticCheck {
  endpoint: string;
  status: string;
  latency_ms: number;
  last_check: string;
  uptime_percentage: number;
}

export interface Alert {
  alert_id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
}

@Injectable({
  providedIn: 'root'
})
export class ObservabilityService {
  private baseUrl = `${environment.apiUrl}/api/observability`;

  constructor(private http: HttpClient) {
    console.log('Observability Service initialized with baseUrl:', this.baseUrl);
  }

  getSLOs(): Observable<{ slos: SLO[] }> {
    console.log('Observability API call:', `${this.baseUrl}/slos`);
    return this.http.get<{ slos: SLO[] }>(`${this.baseUrl}/slos`);
  }

  getErrorBudgets(): Observable<{ error_budgets: ErrorBudget[] }> {
    console.log('Observability API call:', `${this.baseUrl}/error-budgets`);
    return this.http.get<{ error_budgets: ErrorBudget[] }>(`${this.baseUrl}/error-budgets`);
  }

  getSyntheticChecks(): Observable<{ synthetic_checks: SyntheticCheck[] }> {
    console.log('Observability API call:', `${this.baseUrl}/synthetic-checks`);
    return this.http.get<{ synthetic_checks: SyntheticCheck[] }>(`${this.baseUrl}/synthetic-checks`);
  }

  getAlerts(severity?: string): Observable<{ alerts: Alert[] }> {
    const url = severity 
      ? `${this.baseUrl}/alerts?severity=${severity}`
      : `${this.baseUrl}/alerts`;
    console.log('Observability API call:', url);
    return this.http.get<{ alerts: Alert[] }>(url);
  }
}
