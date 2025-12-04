import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BaseApiService } from './api.service';
import { FilterResponse, Financial } from '../models/api_models';
import { environment } from '../../environments/environment.development';
import { DashboardStats } from '../models/api_models';
@Injectable({
  providedIn: 'root'
})
export class FinancialAPIService extends BaseApiService<Financial> {
  // Base URL: http://localhost:3000/financial
  protected baseUrl = `${environment.apiUrl}/financial`;

  constructor(http: HttpClient) {
    super(http);
  }

  // --- 1. Custom Create (Matches: POST /Addfinancials) ---
  override create(data: Financial) {
    return this.http.post<Financial>(`${this.baseUrl}/Addfinancials`, data);
  }

  // --- 2. Bulk Create (Matches: POST /BulkAddfinancials) ---
  bulkCreate(financials: Financial[], userId: string) {
    return this.http.post(`${this.baseUrl}/BulkAddfinancials`, {
      user: userId,
      financials: financials
    });
  }

  // --- 3. Custom Get All (Matches: GET /GetAllfinancials/:userId) ---
  getAllByUser(userId: string) {
    return this.http.get<any>(`${this.baseUrl}/GetAllfinancials/${userId}`);
  }

  // --- 4. Custom Get Single (Matches: GET /:userId/Getfinancials/:recordId) ---
  getSingle(userId: string, recordId: string) {
    return this.http.get<Financial>(`${this.baseUrl}/${userId}/Getfinancials/${recordId}`);
  }

  // --- 5. Custom Update (Matches: PUT /:userId/Updatefinancials/:recordId) ---
  updateRecord(userId: string, recordId: string, data: Partial<Financial>) {
    return this.http.put<Financial>(`${this.baseUrl}/${userId}/Updatefinancials/${recordId}`, data);
  }

  // --- 6. Custom Delete (Matches: DELETE /:userId/Deletefinancials/:recordId) ---
  deleteRecord(userId: string, recordId: string) {
    return this.http.delete(`${this.baseUrl}/${userId}/Deletefinancials/${recordId}`);
  }
  getStats(userId: string) {
    return this.http.get<DashboardStats>(`${this.baseUrl}/dashboard/${userId}`);
  }
  getFilters(userId: string) {
    return this.http.get<FilterResponse>(`${this.baseUrl}/filters/${userId}`);
  }
}