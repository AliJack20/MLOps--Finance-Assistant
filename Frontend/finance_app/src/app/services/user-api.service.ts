import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BaseApiService } from './api.service';
import { User, LoginRequest, RegisterRequest } from '../models/api_models';
import { environment } from '../../environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class UserAPIService extends BaseApiService<User> {
  protected baseUrl = `${environment.apiUrl}/users`;

  constructor(http: HttpClient) {
    super(http);
  }

  register(data: RegisterRequest) {
    return this.http.post<User>(`${this.baseUrl}/register`, data);
  }

  login(data: LoginRequest) {
    return this.http.post<User>(`${this.baseUrl}/login`, data);
  }
}