import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-navbar',
  template: `
    <mat-toolbar color="primary" *ngIf="authService.currentUser">
      <span class="brand" routerLink="/chat">RAG Chatbot</span>
      
      <button mat-button routerLink="/chat">
        <mat-icon>chat</mat-icon>
        Chat
      </button>
      
      <button mat-button routerLink="/history">
        <mat-icon>history</mat-icon>
        History
      </button>
      
      <button mat-button routerLink="/admin" *ngIf="authService.isAdmin">
        <mat-icon>admin_panel_settings</mat-icon>
        Admin
      </button>
      
      <span class="spacer"></span>
      
      <span class="user-info">
        <mat-icon>account_circle</mat-icon>
        {{ authService.currentUser?.email }}
        <span class="role-badge" [class.admin]="authService.isAdmin">
          {{ authService.currentUser?.role }}
        </span>
      </span>
      
      <button mat-button (click)="logout()">
        <mat-icon>logout</mat-icon>
        Logout
      </button>
    </mat-toolbar>
  `,
  styles: [`
    .brand {
      cursor: pointer;
      font-weight: bold;
      margin-right: 20px;
    }
    .spacer {
      flex: 1 1 auto;
    }
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-right: 16px;
    }
    .role-badge {
      background: rgba(255,255,255,0.2);
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      text-transform: uppercase;
    }
    .role-badge.admin {
      background: #ff9800;
      color: white;
    }
  `]
})
export class NavbarComponent {
  constructor(
    public authService: AuthService,
    private router: Router
  ) {}

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
