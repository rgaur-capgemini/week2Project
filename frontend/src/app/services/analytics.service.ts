import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UsageStats, LatencyStats, SystemOverview, UserActivity } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  constructor(private http: HttpClient) {}

  getSystemOverview(): Observable<SystemOverview> {
    return this.http.get<SystemOverview>(`${environment.apiUrl}/analytics/overview`);
  }

  getUsageStats(startDate: string, endDate: string): Observable<UsageStats[]> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);
    return this.http.get<UsageStats[]>(`${environment.apiUrl}/analytics/usage`, { params });
  }

  getLatencyStats(endpoint: string): Observable<LatencyStats> {
    const params = new HttpParams().set('endpoint', endpoint);
    return this.http.get<LatencyStats>(`${environment.apiUrl}/analytics/latency`, { params });
  }

  getUserActivity(userId: string): Observable<UserActivity> {
    return this.http.get<UserActivity>(`${environment.apiUrl}/analytics/user/${userId}`);
  }
}
