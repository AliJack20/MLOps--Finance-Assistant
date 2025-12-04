import { Component } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
@Component({
  selector: 'app-landing',
  standalone: false,
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent {
 loading = false;
  error: string | null = null;

  constructor(
    // private userService: UserService,
    // private auth: AuthService,
    private router: Router
  ) {}
toast = { message: '', type: 'success' as 'success' | 'error', visible: false };
private showToast(message: string, type: 'success' | 'error') {
  this.toast = { message, type, visible: true };
  setTimeout(() => (this.toast.visible = false), 3000);
}
 
  onSubmit(form: NgForm) {
    if (form.invalid) return;
    this.loading = true;
    this.error = null;

    // this.userService.register(form.value).subscribe({
    //   next: (res: any) => {
    //     this.auth.login(res.token);
    //     this.showToast('✅ Registration Successful!', 'success');
    //     this.router.navigate(['/dashboard']);
    //   },
    //   error: (err) => {
    //     this.error = err.error?.error || 'Registration failed';
    //     this.showToast('❌ Login Failed!', 'error');
    //     this.loading = false;
    //   },
    //   complete: () => (this.loading = false)
    // });
  }
}

