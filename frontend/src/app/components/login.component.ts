import { Component, OnInit, AfterViewInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ConfigService } from '../services/config.service';

declare const google: any;

@Component({
  selector: 'app-login',
  template: `
    <div class="login-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>RAG Chatbot Login</mat-card-title>
          <mat-card-subtitle>Sign in with your Google account</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <div *ngIf="!googleClientId" class="loading">
            <mat-spinner diameter="40"></mat-spinner>
            <p>Loading...</p>
          </div>
          <div id="google-signin-button" class="google-button" *ngIf="googleClientId"></div>
          <div *ngIf="error" class="error">
            <mat-icon>error</mat-icon>
            {{ error }}
          </div>
          <div *ngIf="loading" class="loading">
            <mat-spinner diameter="40"></mat-spinner>
            <p>Signing in...</p>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      padding: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    mat-card {
      width: 100%;
      max-width: 450px;
      padding: 20px;
    }
    mat-card-header {
      margin-bottom: 24px;
    }
    .google-button {
      display: flex;
      justify-content: center;
      margin: 20px 0;
    }
    .error {
      color: #f44336;
      margin-top: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: #ffebee;
      border-radius: 4px;
    }
    .loading {
      text-align: center;
      padding: 20px;
    }
    .loading p {
      margin-top: 10px;
      color: #666;
    }
  `]
})
export class LoginComponent implements OnInit, AfterViewInit {
  loading = false;
  error = '';
  googleClientId = '';

  constructor(
    private authService: AuthService,
    private configService: ConfigService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.authService.isAuthenticated) {
      this.router.navigate(['/chat']);
      return;
    }

    // Load config to get Google Client ID
    this.configService.loadConfig().subscribe({
      next: (config) => {
        this.googleClientId = config.googleClientId;
        // Load Google script after we have the client ID
        setTimeout(() => this.loadGoogleSignIn(), 100);
      },
      error: (err) => {
        this.error = 'Failed to load configuration. Please refresh the page.';
        console.error('Config load error:', err);
      }
    });
  }

  ngAfterViewInit(): void {
    // Google sign-in will be loaded after config is fetched
  }

  loadGoogleSignIn(): void {
    // Load Google Identity Services script
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => this.initializeGoogleSignIn();
    document.head.appendChild(script);
  }

  initializeGoogleSignIn(): void {
    if (typeof google !== 'undefined' && this.googleClientId) {
      google.accounts.id.initialize({
        client_id: this.googleClientId,
        callback: (response: any) => this.handleGoogleSignIn(response)
      });

      google.accounts.id.renderButton(
        document.getElementById('google-signin-button'),
        {
          theme: 'outline',
          size: 'large',
          width: 350,
          text: 'signin_with'
        }
      );
    } else {
      this.error = 'Google Sign-In initialization failed. Client ID not found.';
    }
  }

  handleGoogleSignIn(response: any): void {
    this.loading = true;
    this.error = '';

    // Send ID token to backend
    this.authService.loginWithGoogle(response.credential).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.error = err.error?.message || 'Google sign-in failed. Please try again.';
        this.loading = false;
      }
    });
  }
}
