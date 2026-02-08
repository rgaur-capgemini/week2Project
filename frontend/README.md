# RAG Chatbot Frontend

Production-grade Angular 17 frontend for the LLM + RAG Chatbot application on Google Cloud Platform.

## 📋 Overview

Modern, responsive web interface with three core screens:
- **Login**: Google OAuth 2.0 authentication
- **Chat**: AI-powered conversation with RAG context and document upload
- **History**: Conversation management and search
- **Admin**: Analytics dashboard (admin-only)

## 🛠️ Technology Stack

- **Framework**: Angular 17
- **UI Library**: Angular Material 17
- **Authentication**: Google Identity Services (OAuth 2.0)
- **State Management**: RxJS (BehaviorSubject)
- **Markdown**: ngx-markdown
- **HTTP Client**: Angular HttpClient
- **Deployment**: Nginx on GKE

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── login/          # Google OAuth login
│   │   │   ├── chat/           # Main chat interface
│   │   │   ├── history/        # Conversation history
│   │   │   ├── admin/          # Analytics dashboard
│   │   │   └── navbar/         # Navigation bar
│   │   ├── services/
│   │   │   ├── auth.service.ts        # Authentication logic
│   │   │   ├── chat.service.ts        # Chat/query API
│   │   │   ├── history.service.ts     # History management
│   │   │   └── analytics.service.ts   # Analytics data
│   │   ├── interceptors/
│   │   │   ├── auth.interceptor.ts    # JWT token injection
│   │   │   └── error.interceptor.ts   # Global error handling
│   │   ├── guards/
│   │   │   ├── auth.guard.ts          # Route protection
│   │   │   └── admin.guard.ts         # Admin-only routes
│   │   ├── models/
│   │   │   └── models.ts              # TypeScript interfaces
│   │   ├── app.module.ts
│   │   ├── app-routing.module.ts
│   │   └── app.component.ts
│   ├── environments/
│   │   ├── environment.ts             # Development config
│   │   └── environment.prod.ts        # Production config
│   ├── assets/                        # Static files
│   ├── index.html                     # Main HTML + Google SDK
│   ├── styles.css                     # Global styles
│   └── main.ts                        # Bootstrap
├── Dockerfile                         # Multi-stage build
├── nginx.conf                         # Nginx configuration
├── angular.json                       # Angular CLI config
├── package.json                       # Dependencies
└── tsconfig.json                      # TypeScript config
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Angular CLI: `npm install -g @angular/cli`
- Google OAuth 2.0 Client ID (from GCP Console)

### Installation

```bash
cd frontend
npm install
```

### Configuration

1. **Update environment files**:

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080',
  googleClientId: 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'
};

// src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://your-backend-url',
  googleClientId: 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'
};
```

2. **Add OAuth Client ID to index.html** (already configured in template)

### Development Server

```bash
npm start
# or
ng serve

# Navigate to http://localhost:4200
```

The app will automatically reload if you change any source files.

### Build

```bash
# Development build
npm run build

# Production build
npm run build -- --configuration=production
```

Build artifacts will be stored in `dist/rag-chatbot/`.

### Running Tests

```bash
# Unit tests
npm test

# E2E tests
npm run e2e

# Code coverage
npm test -- --code-coverage
```

## 🐳 Docker Build

```bash
# Build Docker image
docker build -t chatbot-frontend:latest .

# Run container
docker run -p 8080:8080 chatbot-frontend:latest

# Navigate to http://localhost:8080
```

## 🔐 Authentication Flow

1. User clicks "Sign in with Google" button
2. Google OAuth popup appears
3. User selects Google account and grants permissions
4. Frontend receives ID token from Google
5. Frontend sends token to backend `/auth/login` endpoint
6. Backend validates token with Google OAuth servers
7. Backend returns JWT access token + refresh token
8. Frontend stores tokens in localStorage
9. AuthInterceptor adds JWT to all subsequent API requests
10. Token auto-refreshes before expiration

## 📡 API Integration

### Base URL
- Development: `http://localhost:8080`
- Production: Configure in `environment.prod.ts`

### Endpoints Used

#### Authentication
- `POST /auth/login` - Exchange Google token for JWT
- `GET /auth/me` - Get current user info
- `POST /auth/refresh` - Refresh access token

#### Chat
- `POST /query` - Send chat query
- `POST /ingest` - Upload documents

#### History
- `GET /history/` - Get chat history (paginated)
- `GET /history/conversations` - List conversations
- `DELETE /history/` - Delete history
- `GET /history/search?q=query` - Search messages

#### Analytics (Admin Only)
- `GET /analytics/usage` - Usage statistics
- `GET /analytics/latency/{endpoint}` - Latency metrics
- `GET /analytics/overview` - System overview
- `GET /analytics/user/{user_id}/activity` - User activity

## 🎨 Features

### Login Screen
- Google Sign-In button
- Responsive design
- Feature highlights
- Loading states

### Chat Screen
- **Real-time messaging** with AI assistant
- **Document upload** (PDF, TXT, MD, DOC/DOCX)
- **Markdown rendering** for responses
- **Citations/sources** display
- **Conversation history** sidebar
- **Advanced options**:
  - Top K results (1-20)
  - Temperature (0-1)
  - Max output tokens (256-8192)
  - Prompt compression toggle
- **Message actions**: Copy, view metadata
- **Conversation management**: New conversation, load previous
- **File upload progress** indicator

### History Screen
- **Conversation table** with search
- **Pagination** support
- **Conversation details** view
- **Export** conversations as JSON
- **Delete** conversations
- **Continue chat** from history
- **Search** across all messages

### Admin Dashboard
- **System Overview Cards**:
  - Total API calls
  - Active users
  - Error rate
  - Average latency
  - Total tokens
  - Total cost
  - Storage used
  - System health
- **Usage Statistics** (date range filter)
- **Latency Analysis** (per endpoint)
- **User Activity** tracking
- **Recommendations** based on metrics
- **Export** data as JSON

### Navigation Bar
- Logo and branding
- Chat / History / Admin links
- User menu with email and role badge
- Logout functionality
- Responsive mobile design

## 🎯 Production Optimizations

### Build Optimizations
- **AOT Compilation**: Ahead-of-time compilation for faster rendering
- **Tree Shaking**: Removes unused code
- **Lazy Loading**: Route-based code splitting
- **Minification**: CSS and JS minification
- **Gzip Compression**: Nginx gzip for assets
- **Cache Headers**: Static assets cached for 1 year

### Performance
- **Bundle Budgets**: Enforced in angular.json (2MB initial, 5MB max)
- **Image Optimization**: WebP support, lazy loading
- **HTTP Caching**: Service worker for offline support (optional)
- **CDN Integration**: Ready for Cloud CDN

### Security
- **CSP Headers**: Content Security Policy in nginx.conf
- **X-Frame-Options**: Prevent clickjacking
- **X-Content-Type-Options**: Prevent MIME sniffing
- **XSS Protection**: X-XSS-Protection header
- **HTTPS Only**: Force secure connections in production
- **JWT Storage**: localStorage with XSS protection
- **Input Sanitization**: Angular's built-in sanitizer

## 🚢 Deployment

### GKE Deployment

1. **Build and push Docker image**:
```bash
export PROJECT_ID=btoproject-486405-486604
export IMAGE_TAG=$(git rev-parse --short HEAD)

docker build -t gcr.io/$PROJECT_ID/chatbot-frontend:$IMAGE_TAG .
docker push gcr.io/$PROJECT_ID/chatbot-frontend:$IMAGE_TAG
```

2. **Update Kubernetes deployment**:
```bash
kubectl set image deployment/chatbot-frontend \
  frontend=gcr.io/$PROJECT_ID/chatbot-frontend:$IMAGE_TAG
```

3. **Verify deployment**:
```bash
kubectl rollout status deployment/chatbot-frontend
kubectl get pods -l app=chatbot-frontend
```

### CI/CD with Cloud Build

Automated deployment is configured in `cloudbuild-gke.yaml`:
```bash
gcloud builds submit --config=cloudbuild-gke.yaml
```

## 📊 Monitoring

### Application Metrics
- Page load time
- API response times
- Error rates
- User sessions

### Infrastructure Metrics (via GKE)
- Pod health
- CPU/Memory usage
- Request rate
- Latency percentiles

## 🐛 Troubleshooting

### Common Issues

**Google Sign-In not working**:
- Verify `googleClientId` in environment files
- Check authorized JavaScript origins in GCP Console
- Ensure Google Identity Services SDK is loaded

**API calls failing**:
- Check `apiUrl` in environment
- Verify CORS settings on backend
- Check browser console for errors
- Verify JWT token in localStorage

**Build errors**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Angular cache
rm -rf .angular
```

**Docker build fails**:
- Increase Docker memory limit
- Check Dockerfile paths
- Verify nginx.conf syntax

## 📚 Development Guidelines

### Code Style
- Follow Angular style guide
- Use TypeScript strict mode
- ESLint for linting
- Prettier for formatting

### Component Structure
```typescript
@Component({
  selector: 'app-example',
  templateUrl: './example.component.html',
  styleUrls: ['./example.component.css']
})
export class ExampleComponent implements OnInit, OnDestroy {
  // Public properties
  // Private properties
  // Constructor with DI
  // Lifecycle hooks
  // Public methods
  // Private methods
}
```

### Service Pattern
```typescript
@Injectable({
  providedIn: 'root'
})
export class ExampleService {
  // Use HttpClient for API calls
  // Return Observables
  // Handle errors with catchError
  // Use RxJS operators
}
```

## 📝 License

Proprietary - Internal use only

## 👥 Contributors

- Development Team
- SRE Team
- Security Team

## 📧 Support

For issues or questions:
- Slack: #chatbot-support
- Email: support@example.com
- Jira: CHATBOT project
