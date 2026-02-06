import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { AdminService, UsageStats, ModelStats } from '../../services/admin.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  activeTab: 'usage' | 'users' | 'models' = 'usage';
  
  usageStats: UsageStats | null = null;
  topUsers: any[] = [];
  modelStats: ModelStats | null = null;
  hourlyDistribution: { [hour: number]: number } = {};
  allUsers: { [email: string]: string } = {};
  
  selectedDays: number = 7;
  isLoading: boolean = false;

  constructor(
    private adminService: AdminService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading = true;
    
    // Load usage stats
    this.adminService.getUsageAnalytics(this.selectedDays).subscribe({
      next: (stats) => {
        this.usageStats = stats;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Failed to load usage stats', error);
        this.isLoading = false;
      }
    });

    // Load top users
    this.adminService.getUserAnalytics(this.selectedDays).subscribe({
      next: (response) => {
        this.topUsers = response.top_users;
      },
      error: (error) => {
        console.error('Failed to load user analytics', error);
      }
    });

    // Load model stats
    this.adminService.getModelAnalytics(this.selectedDays).subscribe({
      next: (response) => {
        this.modelStats = response.models;
      },
      error: (error) => {
        console.error('Failed to load model analytics', error);
      }
    });

    // Load hourly distribution
    this.adminService.getHourlyDistribution(this.selectedDays).subscribe({
      next: (response) => {
        this.hourlyDistribution = response.hourly_distribution;
      },
      error: (error) => {
        console.error('Failed to load hourly distribution', error);
      }
    });

    // Load all users
    this.adminService.listUsers().subscribe({
      next: (response) => {
        this.allUsers = response.users;
      },
      error: (error) => {
        console.error('Failed to load users', error);
      }
    });
  }

  onDaysChange(): void {
    this.loadData();
  }

  goToChat(): void {
    this.router.navigate(['/chat']);
  }

  logout(): void {
    this.authService.logout();
  }

  assignRole(userEmail: string, newRole: string): void {
    if (confirm(`Assign role "${newRole}" to ${userEmail}?`)) {
      this.adminService.assignRole(userEmail, newRole).subscribe({
        next: () => {
          alert('Role assigned successfully');
          this.loadData();
        },
        error: (error) => {
          alert('Failed to assign role: ' + error.message);
        }
      });
    }
  }

  get modelStatsArray(): Array<{ name: string; stats: any }> {
    if (!this.modelStats) return [];
    return Object.entries(this.modelStats).map(([name, stats]) => ({
      name,
      stats
    }));
  }

  get hourlyDistributionArray(): Array<{ hour: number; count: number }> {
    return Object.entries(this.hourlyDistribution).map(([hour, count]) => ({
      hour: parseInt(hour),
      count: count as number
    }));
  }

  getHourLabel(hour: number): string {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}${period}`;
  }

  get maxHourlyCount(): number {
    return Math.max(...Object.values(this.hourlyDistribution), 1);
  }
}
