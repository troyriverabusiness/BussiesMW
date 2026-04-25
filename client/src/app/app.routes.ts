import { Routes } from '@angular/router';

import { CaseWorkspaceComponent } from './case-workspace/case-workspace';
import { DashboardComponent } from './dashboard/dashboard';
import { LandingComponent } from './landing/landing';

export const routes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'cases/:id', component: CaseWorkspaceComponent },
  { path: '**', redirectTo: '' },
];
