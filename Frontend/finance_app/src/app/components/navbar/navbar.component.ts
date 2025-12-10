import { Component, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { MatSidenav } from '@angular/material/sidenav';
import { AuthService } from '../../services/auth.service';
import * as AOS from 'aos';

@Component({
  selector: 'app-navbar',
  standalone: false,
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})
export class NavbarComponent implements OnInit {
  isSidenavVisible = false;
  isLoggedIn = false; // Local variable to hold the state

  constructor(private router: Router, private auth: AuthService) {}

  ngOnInit() {
    // 🔥 1. Subscribe to the Auth Service
    // This updates 'isLoggedIn' instantly whenever the user logs in or out anywhere in the app
    this.auth.isLoggedIn$.subscribe(status => {
      this.isLoggedIn = status;
    });

    // 2. Initialize Animations
    AOS.init({ duration: 800, once: true });

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
    // The subscription above will automatically set isLoggedIn = false
  }

  toggleLogin() {
    if (this.isLoggedIn) {
      this.logout();
    } else {
      this.router.navigate(['/login']); // Redirect to login page
    }
  }

  toggleSidenav() {
    this.isSidenavVisible = !this.isSidenavVisible;
  }

  closeSidenav() {
    this.isSidenavVisible = false;
  }
}