import { AuthService } from './../../services/auth.service';
import { NavigationEnd, Router } from '@angular/router';
import { Component, ViewChild } from '@angular/core';
import { MatSidenav } from '@angular/material/sidenav';
// import { AuthService } from '../auth-service.service';
import * as AOS from 'aos';

@Component({
  selector: 'app-navbar',
  standalone: false,
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})

export class NavbarComponent {
  isSidenavVisible = false;
  constructor(private router:Router,private auth: AuthService) {}
  get isLoggedIn(): boolean {
    return this.auth.isLoggedIn;
  }
  ngOnInit() {
    // this.auth.isLoggedIn$.subscribe(val => this.isLoggedIn = val);
    // this.auth.checkLogin();
    AOS.init({ duration: 800, once: true }); // 👈 initial setup

     this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        setTimeout(() => {
          AOS.refreshHard();
        }, 50);
      }
    });
  }
  logout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }

  toggleSidenav() {
    this.isSidenavVisible = !this.isSidenavVisible;
  }

  closeSidenav() {
    this.isSidenavVisible = false;
  }
 // FIX: Update toggle to use the service methods instead of local state
  toggleLogin() {
    if (this.isLoggedIn) {
      this.logout();
    } else {
      this.auth.login();
    }
  }
}
