import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { UserAPIService } from './user-api.service';
import { LoginRequest, RegisterRequest, User } from '../models/api_models';
import { BehaviorSubject, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private loggedIn = new BehaviorSubject<boolean>(this.hasToken());
  isLoggedIn$ = this.loggedIn.asObservable();
  currentUser: User | null = null;

  constructor(
    private userApi: UserAPIService, 
    private router: Router
  ) { 
    if (this.hasToken()) {
      this.loadUserFromStorage();
    }
  }

  // --- API Calls ---

  register(data: RegisterRequest) {
    return this.userApi.register(data).pipe(
      tap(response => this.saveSession(response))
    );
  }

  login(data: LoginRequest) {
    return this.userApi.login(data).pipe(
      tap(response => this.saveSession(response))
    );
  }

  // --- Session Logic ---

  private saveSession(user: User) {
    if (user.token) {
      localStorage.setItem('token', user.token);
      localStorage.setItem('user', JSON.stringify(user));
      this.currentUser = user;
      this.loggedIn.next(true);
    }
  }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.currentUser = null;
    this.loggedIn.next(false);
    this.router.navigate(['/login']);
  }

  // --- Helpers ---

  getUserId(): string | null {
    return this.currentUser ? this.currentUser._id : null;
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  private hasToken(): boolean {
    return !!localStorage.getItem('token');
  }

  private loadUserFromStorage() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      this.currentUser = JSON.parse(userStr);
    }
  }
}