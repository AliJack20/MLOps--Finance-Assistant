import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BaseApiService } from './api.service';
import { environment } from '../../environments/environment.development';
import { Chat } from '../models/api_models';

@Injectable({
  providedIn: 'root'
})
export class ChatAPIService extends BaseApiService<Chat> {
  protected baseUrl = `${environment.apiUrl}/chat`;

  constructor(http: HttpClient) {
    super(http);
  }

  sendMessage(message: string) {
    return this.http.post<Chat>(`${this.baseUrl}/ask`, { 
      message 
    });
  }
}