import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * HTTP Interceptor that automatically adds JWT token to all outgoing requests.
 * 
 * Reads the token from localStorage and adds it as an Authorization Bearer header.
 * This ensures all authenticated API calls include the JWT token.
 */
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Get JWT token from localStorage
    const token = localStorage.getItem('token');
    
    // If token exists, clone the request and add Authorization header
    if (token) {
      req = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    }
    
    // Pass the modified request to the next handler
    return next.handle(req);
  }
}
