import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CostData {
  total_cost: number;
  service_breakdown: { service: string; cost: number }[];
  period: string;
  currency: string;
}

export interface CostForecast {
  current_month_cost: number;
  forecasted_cost: number;
  days_remaining: number;
  daily_average: number;
  trend: string;
}

export interface CostAnomaly {
  date: string;
  service: string;
  cost: number;
  expected_cost: number;
  deviation_percent: number;
  severity: string;
}

export interface TokenUsage {
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
  request_count: number;
  period: string;
}

export interface UserTokenUsage {
  user_id: string;
  total_tokens: number;
  total_cost: number;
  request_count: number;
}

export interface Budget {
  budget_id: string;
  name: string;
  amount: number;
  spent: number;
  remaining: number;
  period: string;
  thresholds: number[];
  alerts_sent: string[];
  status: string;
}

export interface Alert {
  alert_id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
  metadata: any;
}

export interface FinOpsDashboard {
  costs: CostData;
  forecast: CostForecast;
  anomalies: CostAnomaly[];
  tokens: TokenUsage;
  budgets: Budget[];
  alerts: Alert[];
}

@Injectable({
  providedIn: 'root'
})
export class FinopsService {
  private baseUrl = `${environment.apiUrl}/finops`;

  constructor(private http: HttpClient) {
    console.log('FinOps Service initialized with baseUrl:', this.baseUrl);
  }

  // Cost APIs
  getCurrentMonthCosts(): Observable<CostData> {
    const url = `${this.baseUrl}/costs/current-month`;
    console.log('FinOps API call:', url);
    return this.http.get<CostData>(url);
  }

  getCostsByService(): Observable<{ services: { service: string; cost: number }[] }> {
    return this.http.get<{ services: { service: string; cost: number }[] }>(
      `${this.baseUrl}/costs/by-service`
    );
  }

  getCostForecast(): Observable<CostForecast> {
    return this.http.get<CostForecast>(`${this.baseUrl}/costs/forecast`);
  }

  getCostAnomalies(days: number = 7): Observable<{ anomalies: CostAnomaly[] }> {
    return this.http.get<{ anomalies: CostAnomaly[] }>(
      `${this.baseUrl}/costs/anomalies?days=${days}`
    );
  }

  // Token Usage APIs
  getVertexAITokens(period: string = 'current_month'): Observable<TokenUsage> {
    return this.http.get<TokenUsage>(`${this.baseUrl}/tokens/vertex-ai?period=${period}`);
  }

  getUserTokenUsage(limit: number = 10): Observable<{ users: UserTokenUsage[] }> {
    return this.http.get<{ users: UserTokenUsage[] }>(
      `${this.baseUrl}/tokens/user-usage?limit=${limit}`
    );
  }

  getTopUsers(limit: number = 10): Observable<{ top_users: UserTokenUsage[] }> {
    return this.http.get<{ top_users: UserTokenUsage[] }>(
      `${this.baseUrl}/tokens/top-users?limit=${limit}`
    );
  }

  estimateCost(model: string, input_tokens: number, output_tokens: number): Observable<any> {
    return this.http.get(
      `${this.baseUrl}/tokens/estimate-cost?model=${model}&input_tokens=${input_tokens}&output_tokens=${output_tokens}`
    );
  }

  // Budget APIs
  getBudgets(): Observable<{ budgets: Budget[] }> {
    return this.http.get<{ budgets: Budget[] }>(`${this.baseUrl}/budgets`);
  }

  createBudget(budget: { name: string; amount: number; scope: string; thresholds: number[] }): Observable<any> {
    return this.http.post(`${this.baseUrl}/budgets`, budget);
  }

  // Alerts APIs
  getAlerts(severity?: string): Observable<{ alerts: Alert[] }> {
    const url = severity 
      ? `${this.baseUrl}/alerts?severity=${severity}`
      : `${this.baseUrl}/alerts`;
    return this.http.get<{ alerts: Alert[] }>(url);
  }

  // Dashboard API
  getDashboard(): Observable<FinOpsDashboard> {
    return this.http.get<FinOpsDashboard>(`${this.baseUrl}/dashboard`);
  }
}
