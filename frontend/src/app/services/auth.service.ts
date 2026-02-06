import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

declare const google: any;

export interface User {
  sub: string;
  email: string;
  name: string;
  picture: string;
  role: string;
  permissions: string[];
}

export interface AuthResponse {
  user: User;
  role: string;
  permissions: string[];
  authenticated: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  
  private tokenKey = 'auth_token';

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.loadStoredUser();
  }

  /**
   * Initialize Google Sign-In
   */
  initializeGoogleSignIn(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (typeof google === 'undefined') {
        reject('Google SDK not loaded');
        return;
      }

      google.accounts.id.initialize({
        client_id: environment.googleClientId,
        callback: (response: any) => this.handleGoogleCallback(response)
      });

      resolve();
    });
  }

  /**
   * Handle Google Sign-In callback
   */
  private handleGoogleCallback(response: any): void {
    const idToken = response.credential;
    this.loginWithToken(idToken).subscribe({
      next: () => {
        this.router.navigate(['/chat']);
      },
      error: (error) => {
        console.error('Login failed', error);
      }
    });
  }

  /**
   * Login with Google ID token
   */
  loginWithToken(idToken: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/api/v1/auth/login`, {
      id_token: idToken
    }).pipe(
      tap(response => {
        this.setToken(idToken);
        this.currentUserSubject.next(response.user);
        localStorage.setItem('user', JSON.stringify(response.user));
      })
    );
  }

  /**
   * Get current user info from server
   */
  getCurrentUser(): Observable<any> {
    return this.http.get(`${environment.apiUrl}/api/v1/auth/me`).pipe(
      tap(response => {
        if (response && (response as any).user) {
          this.currentUserSubject.next((response as any).user);
          localStorage.setItem('user', JSON.stringify((response as any).user));
        }
      })
    );
  }

  /**
   * Logout
   */
  logout(): void {
    this.clearToken();
    this.currentUserSubject.next(null);
    localStorage.removeItem('user');
    this.router.navigate(['/login']);
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Check if user has specific role
   */
  hasRole(role: string): boolean {
    const user = this.currentUserSubject.value;
    return user?.role === role;
  }

  /**
   * Check if user has permission
   */
  hasPermission(permission: string): boolean {
    const user = this.currentUserSubject.value;
    return user?.permissions?.includes(permission) || false;
  }

  /**
   * Get auth token
   */
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Set auth token
   */
  private setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  /**
   * Clear auth token
   */
  private clearToken(): void {
    localStorage.removeItem(this.tokenKey);
  }

  /**
   * Load user from localStorage
   */
  private loadStoredUser(): void {
    const userJson = localStorage.getItem('user');
    if (userJson) {
      try {
        const user = JSON.parse(userJson);
        this.currentUserSubject.next(user);
      } catch (e) {
        console.error('Failed to parse stored user', e);
      }
    }
  }

  /**
   * Get current user value (synchronous)
   */
  get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }
}
