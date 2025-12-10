import { Component, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-landing',
  standalone: false,
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit {
  loading = false;
  error: string | null = null;

  // Local Toast State (for custom HTML positioning if needed)
  toast = { message: '', type: 'success' as 'success' | 'error', visible: false };

  constructor(
    private auth: AuthService,
    private router: Router,
    private toastService: ToastService 
  ) {}

  // 🔥 NEW: Check login status when page loads
  ngOnInit() {
    if (this.auth.getToken()) {
      this.router.navigate(['/dashboard']);
    }
  }

  private showToast(message: string, type: 'success' | 'error') {
    this.toast = { message, type, visible: true };
    setTimeout(() => (this.toast.visible = false), 3000);
  }
 
  onSubmit(form: NgForm) {
    if (form.invalid) return;
    
    this.loading = true;
    this.error = null;

    // 🔥 Call the AuthService
    this.auth.register(form.value).subscribe({
      next: (user) => {
        // Use Global Toast for success
        this.toastService.show(`Welcome, ${user.name}!`, 'success');
        
        // Short delay to let the user see the success message
        setTimeout(() => {
          this.router.navigate(['/dashboard']);
        }, 1000);
      },
      error: (err) => {
        // Backend returns error in err.error.error usually
        this.error = err.error?.error || 'Registration failed. Try again.';
        
        // Use Local Toast for error (to show near form)
        this.showToast('❌ Registration Failed', 'error');
        this.loading = false;
      },
      complete: () => {
        this.loading = false;
      }
    });
  }
}