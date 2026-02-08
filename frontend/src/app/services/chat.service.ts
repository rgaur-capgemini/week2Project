import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { QueryRequest, QueryResponse } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  constructor(private http: HttpClient) {}

  query(request: QueryRequest): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${environment.apiUrl}/query`, request);
  }

  ingest(formData: FormData): Observable<any> {
    return this.http.post(`${environment.apiUrl}/ingest`, formData);
  }
}
