import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: any;
}

export interface ChatSession {
  session_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface QueryRequest {
  query: string;
  session_id?: string;
  top_k?: number;
  use_reranking?: boolean;
}

export interface QueryResponse {
  answer: string;
  session_id: string;
  contexts: any[];
  metadata: {
    response_time_ms: number;
    token_usage: {
      input_tokens: number;
      output_tokens: number;
      total_tokens: number;
    };
  };
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {}

  /**
   * Send a chat query
   */
  query(request: QueryRequest): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.apiUrl}/chat/query`, request);
  }

  /**
   * Get all chat sessions for current user
   */
  getSessions(limit: number = 50, offset: number = 0): Observable<ChatSession[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    
    return this.http.get<ChatSession[]>(`${this.apiUrl}/chat/sessions`, { params });
  }

  /**
   * Get message history for a session
   */
  getSessionHistory(sessionId: string): Observable<{ session_id: string; messages: ChatMessage[] }> {
    return this.http.get<{ session_id: string; messages: ChatMessage[] }>(
      `${this.apiUrl}/chat/sessions/${sessionId}/history`
    );
  }

  /**
   * Delete a chat session
   */
  deleteSession(sessionId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/chat/sessions/${sessionId}`);
  }

  /**
   * Get user statistics
   */
  getUserStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/user/stats`);
  }
}
