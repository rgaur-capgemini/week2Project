import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const RoleGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const requiredRole = route.data['requiredRole'] as string;

  if (authService.hasRole(requiredRole)) {
    return true;
  }

  router.navigate(['/chat']);
  return false;
};
