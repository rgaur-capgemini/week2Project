import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { HistoryResponse } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class HistoryService {
  constructor(private http: HttpClient) {}

  getHistory(limit: number = 50, offset: number = 0, conversationId?: string): Observable<HistoryResponse> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    
    if (conversationId) {
      params = params.set('conversation_id', conversationId);
    }

    return this.http.get<HistoryResponse>(`${environment.apiUrl}/history/`, { params });
  }

  deleteConversation(conversationId: string): Observable<any> {
    return this.http.delete(`${environment.apiUrl}/history/${conversationId}`);
  }
}
