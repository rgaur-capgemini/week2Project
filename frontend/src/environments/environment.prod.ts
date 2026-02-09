// Production environment configuration
export const environment = {
  production: true,
  apiUrl: '',  // Empty string = relative path, nginx will proxy to backend
  // OAuth Client ID - fetched from backend /api/config endpoint
  // Backend retrieves this from GCP Secret Manager
  googleClientId: '',  // Leave empty - fetched at runtime
  appTitle: 'RAG Chatbot'
};
