export interface User {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  role: 'user' | 'admin';
  permissions?: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface QueryRequest {
  question: string;
  conversation_id?: string;
  top_k?: number;
  temperature?: number;
}

export interface QueryResponse {
  answer: string;
  contexts: string[];
  conversation_id?: string;
  model_used?: string;
  citations?: string[];
}

export interface IngestResponse {
  status: string;
  ingested_chunks: number;
  gcs_uris?: string[];
  answer?: string;
  contexts?: string[];
}

export interface HistoryResponse {
  user_id: string;
  messages: ChatMessage[];
  total_count: number;
  has_more: boolean;
}

export interface UsageStats {
  endpoint: string;
  total_calls: number;
  unique_users: number;
  error_rate: number;
  avg_tokens: number;
}

export interface LatencyStats {
  endpoint: string;
  p50: number;
  p95: number;
  p99: number;
  avg: number;
}

export interface SystemOverview {
  total_requests: number;
  total_users: number;
  error_rate: number;
  avg_latency_ms: number;
}

export interface UserActivity {
  user_id: string;
  total_queries: number;
  total_tokens: number;
  daily_stats: {
    [date: string]: {
      calls: number;
      tokens: number;
      cost_usd: number;
    };
  };
}

export interface AppConfig {
  googleClientId: string;
  projectId: string;
  region: string;
  environment: string;
}
