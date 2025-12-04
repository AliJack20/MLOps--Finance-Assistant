import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// Import your components
import { LandingComponent } from './pages/landing/landing.component';
import { LoginComponent } from './pages/login/login.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { CalendarComponent } from './pages/calendar/calendar.component';
import { ChatComponent } from './pages/chat/chat.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { UpdatesComponent } from './pages/updates/updates.component';
import { FaqComponent } from './pages/faq/faq.component';
import { TransactionsComponent } from './pages/transactions/transactions.component';

const routes: Routes = [
  // Public Routes
  { path: '', component: LandingComponent },
  { path: 'login', component: LoginComponent },
  { path: 'updates', component: UpdatesComponent },
  { path: 'faq', component: FaqComponent },

  // Private Routes (We will add AuthGuard later)
  { path: 'dashboard', component: DashboardComponent },
  { path: 'calendar', component: CalendarComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'profile', component: ProfileComponent },
  { path: 'transactions', component: TransactionsComponent },


  // Fallback
  { path: '**', redirectTo: '' } 
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }