import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Variant {
  variant_id: string;
  name: string;
  variant_type: string;
  config: any;
  traffic_weight: number;
  is_active: boolean;
  created_at: string;
  total_requests?: number;
  success_rate?: number;
  avg_latency?: number;
  avg_cost?: number;
}

export interface VariantResult {
  variant_id: string;
  name: string;
  requests: number;
  success_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  avg_cost: number;
  total_cost: number;
}

export interface FeatureFlag {
  flag_id: string;
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ExperimentsService {
  private baseUrl = `${environment.apiUrl}/experiments`;

  constructor(private http: HttpClient) {}

  // Variant Management
  getVariants(): Observable<{ variants: Variant[] }> {
    return this.http.get<{ variants: Variant[] }>(`${this.baseUrl}/variants`);
  }

  createVariant(variant: {
    name: string;
    variant_type: string;
    config: any;
    traffic_weight: number;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/variants`, variant);
  }

  activateVariant(variantId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/variants/${variantId}/activate`, {});
  }

  deactivateVariant(variantId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/variants/${variantId}/deactivate`, {});
  }

  updateTraffic(variantId: string, weight: number): Observable<any> {
    return this.http.put(`${this.baseUrl}/variants/${variantId}/traffic`, { weight });
  }

  // Results & Comparison
  getResults(days: number = 7): Observable<{ results: VariantResult[] }> {
    return this.http.get<{ results: VariantResult[] }>(
      `${this.baseUrl}/results?days=${days}`
    );
  }

  // Gradual Rollout
  rolloutVariant(variantId: string, targetWeight: number, increment: number, intervalMinutes: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/variants/${variantId}/rollout`, {
      target_weight: targetWeight,
      increment,
      interval_minutes: intervalMinutes
    });
  }

  checkRollback(variantId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/variants/${variantId}/check-rollback`, {});
  }

  // Feature Flags
  getFeatureFlags(): Observable<{ flags: FeatureFlag[] }> {
    return this.http.get<{ flags: FeatureFlag[] }>(`${this.baseUrl}/feature-flags`);
  }

  checkFeatureFlag(flagName: string, userId: string): Observable<{ enabled: boolean }> {
    return this.http.get<{ enabled: boolean }>(
      `${this.baseUrl}/feature-flags/${flagName}/check?user_id=${userId}`
    );
  }

  enableFeatureFlag(flagId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/feature-flags/${flagId}/enable`, {});
  }

  disableFeatureFlag(flagId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/feature-flags/${flagId}/disable`, {});
  }
}
