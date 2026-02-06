import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UsageStats {
  period: {
    start: string;
    end: string;
  };
  queries: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
  tokens: {
    total: number;
    average_per_query: number;
  };
  cost: {
    total_usd: number;
    average_per_query_usd: number;
  };
  latency: {
    average_ms: number;
    median_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
  users: {
    unique_users: number;
    users_list: string[];
  };
}

export interface ModelStats {
  [model: string]: {
    query_count: number;
    total_tokens: number;
    total_cost: number;
    avg_latency_ms: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private apiUrl = `${environment.apiUrl}/api/v1/admin`;

  constructor(private http: HttpClient) {}

  /**
   * Get usage analytics
   */
  getUsageAnalytics(days: number = 7): Observable<UsageStats> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<UsageStats>(`${this.apiUrl}/analytics/usage`, { params });
  }

  /**
   * Get per-user analytics
   */
  getUserAnalytics(days: number = 30): Observable<{ top_users: any[] }> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<{ top_users: any[] }>(`${this.apiUrl}/analytics/users`, { params });
  }

  /**
   * Get model usage analytics
   */
  getModelAnalytics(days: number = 30): Observable<{ models: ModelStats }> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<{ models: ModelStats }>(`${this.apiUrl}/analytics/models`, { params });
  }

  /**
   * Get hourly distribution
   */
  getHourlyDistribution(days: number = 7): Observable<{ hourly_distribution: { [hour: number]: number } }> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<{ hourly_distribution: { [hour: number]: number } }>(
      `${this.apiUrl}/analytics/hourly`,
      { params }
    );
  }

  /**
   * List all users
   */
  listUsers(): Observable<{ users: { [email: string]: string } }> {
    return this.http.get<{ users: { [email: string]: string } }>(`${this.apiUrl}/users`);
  }

  /**
   * Assign role to user
   */
  assignRole(userEmail: string, role: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/assign-role`, {
      user_email: userEmail,
      role: role
    });
  }
}
