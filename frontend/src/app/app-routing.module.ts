import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login.component';
import { ChatComponent } from './components/chat.component';
import { HistoryComponent } from './components/history.component';
import { AdminComponent } from './components/admin.component';
import { ComplianceComponent } from './components/compliance.component';
import { ComplianceReportComponent } from './components/compliance-report.component';
import { FinopsDashboardComponent } from './components/finops-dashboard/finops-dashboard.component'; // Week 4: FinOps

const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'history', component: HistoryComponent },
  { path: 'admin', component: AdminComponent },
  { path: 'compliance', component: ComplianceComponent },
  { path: 'compliance/report/:id', component: ComplianceReportComponent },
  { path: 'finops', component: FinopsDashboardComponent }, // Week 4: FinOps Dashboard
  { path: '**', redirectTo: '/login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
