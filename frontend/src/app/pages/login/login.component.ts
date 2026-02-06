import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <h1>ChatBot RAG Application</h1>
          <p>Intelligent Document Q&A with AI</p>
        </div>
        
        <div class="login-content">
          <div id="google-signin-button"></div>
          
          <div class="features">
            <h3>Features</h3>
            <ul>
              <li>✓ Secure Google Authentication</li>
              <li>✓ AI-Powered Document Search</li>
              <li>✓ Conversation History</li>
              <li>✓ Real-time Analytics</li>
            </ul>
          </div>
        </div>
        
        <div class="login-footer">
          <p>Powered by Google Cloud & Gemini AI</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }

    .login-card {
      background: white;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      max-width: 450px;
      width: 100%;
      overflow: hidden;
    }

    .login-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 40px 30px;
      text-align: center;
    }

    .login-header h1 {
      margin: 0 0 10px 0;
      font-size: 28px;
      font-weight: 600;
    }

    .login-header p {
      margin: 0;
      opacity: 0.9;
      font-size: 16px;
    }

    .login-content {
      padding: 40px 30px;
    }

    #google-signin-button {
      display: flex;
      justify-content: center;
      margin-bottom: 30px;
    }

    .features {
      margin-top: 30px;
      padding-top: 30px;
      border-top: 1px solid #eee;
    }

    .features h3 {
      margin: 0 0 15px 0;
      font-size: 18px;
      color: #333;
    }

    .features ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .features li {
      padding: 8px 0;
      color: #666;
      font-size: 14px;
    }

    .login-footer {
      background: #f8f9fa;
      padding: 20px;
      text-align: center;
      color: #666;
      font-size: 14px;
    }

    .login-footer p {
      margin: 0;
    }
  `]
})
export class LoginComponent implements OnInit {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Check if already authenticated
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/chat']);
      return;
    }

    // Initialize Google Sign-In
    this.loadGoogleScript().then(() => {
      this.authService.initializeGoogleSignIn().then(() => {
        this.renderGoogleButton();
      });
    });
  }

  private loadGoogleScript(): Promise<void> {
    return new Promise((resolve, reject) => {
      if ((window as any).google) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => reject();
      document.head.appendChild(script);
    });
  }

  private renderGoogleButton(): void {
    const google = (window as any).google;
    if (google) {
      google.accounts.id.renderButton(
        document.getElementById('google-signin-button'),
        {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left'
        }
      );
    }
  }
}
