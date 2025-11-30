import { AuthService } from './../../services/auth.service';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent implements OnInit, OnDestroy {

  loading = false;
  error: string | null = null;
  toast = { message: '', type: 'success' as 'success' | 'error', visible: false };

  constructor(private router: Router,private toastService: ToastService,private auth: AuthService ) {}

  ngOnInit() {
    // document.body.style.overflow = 'hidden'; 
  }

  ngOnDestroy() {
    document.body.style.overflow = '';
  }

  
 
  onSubmit(form: NgForm) {
    if (form.invalid) return; // Keeps the 'required' validation
    
    this.loading = true;
    this.error = null;

    console.log('Mock Login Data:', form.value);

    // Simulate network delay
    setTimeout(() => {
      // 1. Show Toast
      this.toastService.show('✅ Welcome Back!', 'success', 3000);
      this.auth.login();
      // 2. Navigate immediately
      this.router.navigate(['/dashboard']);
      
      this.loading = false;
    }, 1000); 
  }
}