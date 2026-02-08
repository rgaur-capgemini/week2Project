// Production environment configuration
export const environment = {
  production: true,
  apiUrl: 'https://YOUR-GKE-LOADBALANCER-IP',  // Update after GKE deployment
  // OAuth Client ID - fetched from backend /api/config endpoint
  // Backend retrieves this from GCP Secret Manager
  googleClientId: '',  // Leave empty - fetched at runtime
  appTitle: 'RAG Chatbot'
};
