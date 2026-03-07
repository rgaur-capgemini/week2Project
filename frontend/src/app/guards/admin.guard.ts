import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * AdminGuard — allows only users with role === 'admin'.
 * Applied to /admin and /finops routes.
 * Only raman.gaur@capgemini.com has the admin role.
 */
@Injectable({
  providedIn: 'root'
})
export class AdminGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    if (!this.authService.isAuthenticated) {
      this.router.navigate(['/login']);
      return false;
    }

    if (this.authService.isAdmin) {
      return true;
    }

    // Non-admin authenticated users are sent back to chat
    this.router.navigate(['/chat']);
    return false;
  }
}
