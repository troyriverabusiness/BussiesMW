import { Routes } from '@angular/router';

import { DashboardComponent } from './dashboard/dashboard';
import { LandingComponent } from './landing/landing';

export const routes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: '**', redirectTo: '' },
];
