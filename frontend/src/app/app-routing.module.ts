import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login.component';
import { ChatComponent } from './components/chat.component';
import { HistoryComponent } from './components/history.component';
import { AdminComponent } from './components/admin.component';
import { ComplianceComponent } from './components/compliance.component';
import { ComplianceReportComponent } from './components/compliance-report.component';
import { FinopsDashboardComponent } from './components/finops-dashboard/finops-dashboard.component'; // Week 4: FinOps
import { AuthGuard } from './guards/auth.guard';
import { AdminGuard } from './guards/admin.guard';

const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },

  // All routes below require authentication
  { path: 'chat',       component: ChatComponent,       canActivate: [AuthGuard] },
  { path: 'history',    component: HistoryComponent,    canActivate: [AuthGuard] },
  { path: 'compliance', component: ComplianceComponent, canActivate: [AuthGuard] },
  { path: 'compliance/report/:id', component: ComplianceReportComponent, canActivate: [AuthGuard] },

  // Admin-only routes — raman.gaur@capgemini.com only
  { path: 'admin',  component: AdminComponent,         canActivate: [AdminGuard] },
  { path: 'finops', component: FinopsDashboardComponent, canActivate: [AdminGuard] }, // Week 4: FinOps Dashboard

  { path: '**', redirectTo: '/login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
