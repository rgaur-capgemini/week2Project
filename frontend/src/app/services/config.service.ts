import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AppConfig } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private config: AppConfig | null = null;

  constructor(private http: HttpClient) {}

  loadConfig(): Observable<AppConfig> {
    return this.http.get<AppConfig>(`${environment.apiUrl}/api/config`).pipe(
      tap(config => {
        this.config = config;
      })
    );
  }

  getConfig(): AppConfig | null {
    return this.config;
  }

  getGoogleClientId(): string {
    return this.config?.googleClientId || '';
  }
}
