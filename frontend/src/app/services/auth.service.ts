import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { User } from '../models/models';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const user = localStorage.getItem('user');
    if (user) {
      this.currentUserSubject.next(JSON.parse(user));
    }
  }

  get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  get isAuthenticated(): boolean {
    return !!this.currentUser;
  }

  get isAdmin(): boolean {
    return this.currentUser?.role === 'admin';
  }

  loginWithGoogle(idToken: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/auth/login`, { token: idToken }).pipe(
      tap((response: any) => {
        const user: User = {
          user_id: response.user_id,
          email: response.email,
          name: response.name,
          picture: response.picture,
          role: response.role
        };
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('token', response.access_token);
        this.currentUserSubject.next(user);
      })
    );
  }

  login(email: string, password: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/auth/login`, { email, password }).pipe(
      tap((response: any) => {
        const user: User = {
          user_id: response.user_id,
          email: response.email,
          name: response.name,
          role: response.role
        };
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('token', response.access_token);
        this.currentUserSubject.next(user);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    this.currentUserSubject.next(null);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }
}
