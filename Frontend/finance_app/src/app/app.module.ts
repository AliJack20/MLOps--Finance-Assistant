import { NgModule } from '@angular/core';
import { BrowserModule, provideClientHydration, withEventReplay } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http'; // <--- NEW: Import HttpClientModule
import { MatIconModule } from '@angular/material/icon';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

// Pages
import { LandingComponent } from './pages/landing/landing.component';
import { LoginComponent } from './pages/login/login.component';
import { UpdatesComponent } from './pages/updates/updates.component';
import { FaqComponent } from './pages/faq/faq.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { ChatComponent } from './pages/chat/chat.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { CalendarComponent } from './pages/calendar/calendar.component';
import { TransactionsComponent } from './pages/transactions/transactions.component';

// Components
import { TransactionModalComponent } from './components/transaction-modal/transaction-modal.component';
import { NavbarComponent } from './components/navbar/navbar.component';
import { ToastComponent } from './components/toast/toast.component';
import { LoaderComponent } from './components/loader/loader.component';

// Modules
import { MatSidenavModule } from '@angular/material/sidenav';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule, provideNativeDateAdapter } from '@angular/material/core';
import { FullCalendarModule } from '@fullcalendar/angular';

// Interceptors
import { AuthInterceptor } from './services/auth.interceptor'; // <--- NEW: Import Interceptor

@NgModule({
  declarations: [
    AppComponent,
    LandingComponent,
    LoginComponent,
    UpdatesComponent,
    FaqComponent,
    DashboardComponent,
    CalendarComponent,
    ChatComponent,
    ProfileComponent,
    TransactionModalComponent,
    NavbarComponent,
    ToastComponent,
    LoaderComponent,
    TransactionsComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule, // <--- NEW: Must be here for Services to work
    MatSidenavModule,
    MatIconModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,      // Added Input Module just in case
    MatDatepickerModule,
    MatNativeDateModule, // Added Native Date Module
    FullCalendarModule
  ],
  providers: [
    provideNativeDateAdapter(),
    provideClientHydration(withEventReplay()),
    // <--- NEW: Register the Auth Interceptor
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}