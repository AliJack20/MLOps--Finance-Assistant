import { Component, OnInit } from '@angular/core';
import { ToastService } from '../../services/toast.service';

interface Transaction {
  id: number;
  title: string;
  amount: number;
  date: string; // ISO format 'YYYY-MM-DD'
  category: string;
  type: 'income' | 'expense';
  backgroundColor?: string;
}

@Component({
  selector: 'app-transactions',
  standalone: false,
  templateUrl: './transactions.component.html',
  styleUrls: ['./transactions.component.css']
})
export class TransactionsComponent implements OnInit {

  // 1. Data
  allTransactions: Transaction[] = [
    { id: 1, title: 'Rent', amount: -1200, date: '2025-10-01', category: 'Rent', type: 'expense' },
    { id: 2, title: 'Freelance Project', amount: 1500, date: '2025-10-03', category: 'Income', type: 'income' },
    { id: 3, title: 'Groceries', amount: -85.50, date: '2025-10-05', category: 'Groceries', type: 'expense' },
    { id: 4, title: 'Netflix', amount: -15.99, date: '2025-10-07', category: 'Entertainment', type: 'expense' },
    { id: 5, title: 'Salary', amount: 4200, date: '2025-10-15', category: 'Income', type: 'income' },
  ];

  filteredTransactions: Transaction[] = [];

  // 2. Filters
  filters = {
    searchText: '',
    category: 'All',
    type: 'All',
    startDate: null as Date | null, 
    endDate: null as Date | null,
    minPrice: null as number | null,
    maxPrice: null as number | null,
    year: 'All'
  };

  categories = ['All', 'Rent', 'Groceries', 'Entertainment', 'Income', 'Health', 'Food'];
  years = ['All', '2024', '2025'];

  // 3. Modal States
  showModal = false;
  selectedTransaction: Transaction | null = null; // Data to pass to modal

  // 4. Delete Confirmation State
  showDeleteModal = false;
  transactionToDeleteId: number | null = null;

  constructor(private toastService: ToastService) {}

  ngOnInit(): void {
    this.applyFilters();
  }

  // --- ACTIONS ---

  // Open Modal for Creating
  openAddModal() {
    this.selectedTransaction = null; // Clear data
    this.showModal = true;
  }

  // Open Modal for Editing
  editTransaction(transaction: Transaction) {
    this.selectedTransaction = { ...transaction }; // Clone to avoid direct mutation
    this.showModal = true;
  }

  // Handle Save (Add or Update)
  handleSaveTransaction(data: any) {
    if (data.id) {
      // UPDATE Existing
      const index = this.allTransactions.findIndex(t => t.id === data.id);
      if (index !== -1) {
        this.allTransactions[index] = data;
        this.toastService.show('Transaction updated successfully!', 'success', 3000);
      }
    } else {
      // CREATE New
      const newId = Math.max(...this.allTransactions.map(t => t.id), 0) + 1;
      this.allTransactions.push({ ...data, id: newId });
      this.toastService.show('Transaction added successfully!', 'success', 3000);
    }
    
    this.applyFilters();
    this.showModal = false;
  }

  // Open Delete Confirmation
  deleteTransaction(id: number) {
    this.transactionToDeleteId = id;
    this.showDeleteModal = true;
  }

  // Confirm Delete Action
  confirmDelete() {
    if (this.transactionToDeleteId !== null) {
      this.allTransactions = this.allTransactions.filter(t => t.id !== this.transactionToDeleteId);
      this.applyFilters();
      this.toastService.show('Transaction deleted successfully!', 'error', 3000); // Using 'error' type for red toast
      
      // Reset
      this.showDeleteModal = false;
      this.transactionToDeleteId = null;
    }
  }

  // Cancel Delete
  cancelDelete() {
    this.showDeleteModal = false;
    this.transactionToDeleteId = null;
  }


  // --- FILTERING LOGIC ---
  applyFilters() {
    this.filteredTransactions = this.allTransactions.filter(t => {
      const tDate = new Date(t.date);
      const amount = Math.abs(t.amount);

      const matchesText = t.title.toLowerCase().includes(this.filters.searchText.toLowerCase());
      const matchesCategory = this.filters.category === 'All' || t.category === this.filters.category;
      const matchesType = this.filters.type === 'All' || t.type === this.filters.type;
      const matchesYear = this.filters.year === 'All' || tDate.getFullYear().toString() === this.filters.year;

      let matchesStartDate = true;
      if (this.filters.startDate) {
        const start = new Date(this.filters.startDate);
        start.setHours(0, 0, 0, 0);
        matchesStartDate = tDate >= start;
      }

      let matchesEndDate = true;
      if (this.filters.endDate) {
        const end = new Date(this.filters.endDate);
        end.setHours(23, 59, 59, 999);
        matchesEndDate = tDate <= end;
      }

      const matchesMinPrice = this.filters.minPrice === null || amount >= this.filters.minPrice;
      const matchesMaxPrice = this.filters.maxPrice === null || amount <= this.filters.maxPrice;

      return matchesText && matchesCategory && matchesType && matchesYear && 
             matchesStartDate && matchesEndDate && matchesMinPrice && matchesMaxPrice;
    });

    // Sort Newest First
    this.filteredTransactions.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }

  resetFilters() {
    this.filters = {
      searchText: '',
      category: 'All',
      type: 'All',
      startDate: null,
      endDate: null,
      minPrice: null,
      maxPrice: null,
      year: 'All'
    };
    this.applyFilters();
  }
}