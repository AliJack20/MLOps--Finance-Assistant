import { Component } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service'; // Ensure correct path
import { ToastService } from '../../services/toast.service'; // Ensure correct path

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  loading = false;
  error: string | null = null;

  constructor(
    private auth: AuthService,       // 1. Inject the real AuthService
    private router: Router,
    private toastService: ToastService
  ) {}

  onSubmit(form: NgForm) {
    if (form.invalid) return;
    
    this.loading = true;
    this.error = null;

    // 2. Call the REAL API method
    // form.value contains { email: "...", password: "..." }
    this.auth.login(form.value).subscribe({
      next: (user) => {
        // ✅ Success: Token is already saved by AuthService
        this.toastService.show(`Welcome back, ${user.name}!`, 'success');
        
        // Navigate to Dashboard
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        // ❌ Error: Handle backend failure
        // Backend usually sends error in err.error.error
        this.error = err.error?.error || 'Invalid email or password.';
        this.toastService.show(this.error || 'Login Failed', 'error');
        this.loading = false;
      },
      complete: () => {
        this.loading = false;
      }
    });
  }
}