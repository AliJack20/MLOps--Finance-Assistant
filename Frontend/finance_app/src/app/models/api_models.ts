// src/app/models/api-models.ts

// The User object we get back from Login/Register
export interface User {
  _id: string;
  name: string;
  email: string;
  token?: string; // We receive this on login
}

// Payload for Login
export interface LoginRequest {
  email: string;
  password?: string;
}

// Payload for Register
export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

// The Financial Record (matches your Mongoose model)
export interface Financial {
  _id?: string; // Optional because new records don't have an ID yet
  user: string;
  title: string;
  amount: number;
  type: 'income' | 'expense';
  date: Date | string;
  category: string;
  color: string;
}
export interface FilterResponse {
  categories: string[];
  years: string[];
}


// The Dashboard Stats (matches your dashboard.controller.js)
export interface DashboardStats {
  balance: number;
  monthlyIncome: number;
  monthlyExpense: number;
  categoryStats: { _id: string; total: number; color: string }[];
  recentTransactions: Financial[];
  prediction?: { 
    prediction_next_week: number;
    input: any; 
  };
}
export interface CategoryColor {
  name: string;
  color: string;
}
export interface Chat{
   response: string
    created?: boolean

}