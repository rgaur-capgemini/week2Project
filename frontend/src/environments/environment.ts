// Angular configuration for LOCAL DEVELOPMENT
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080',
  // OAuth Client ID - will be fetched from backend /api/config endpoint
  // Backend retrieves this from GCP Secret Manager
  googleClientId: '',  // Leave empty - fetched at runtime
  appTitle: 'RAG Chatbot'
};
