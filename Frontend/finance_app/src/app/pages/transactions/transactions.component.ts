import { Component, OnInit } from '@angular/core';
import { ToastService } from '../../services/toast.service';
import { FinancialAPIService } from '../../services/finance-api.service'; // Check file name matches your folder
import { AuthService } from '../../services/auth.service';
import { Financial, FilterResponse, CategoryColor } from '../../models/api_models';

@Component({
  selector: 'app-transactions',
  standalone: false,
  templateUrl: './transactions.component.html',
  styleUrls: ['./transactions.component.css']
})
export class TransactionsComponent implements OnInit {

  // 1. Data Containers
  allTransactions: Financial[] = [];
  filteredTransactions: Financial[] = [];
  loading = false;
  
  // 2. Dynamic Filters
  categories: CategoryColor[] = []; // Stores {name, color}
  years: string[] = ['All'];

  // 3. Filter State
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

  // 4. Modal States
  showModal = false;
  selectedTransaction: Financial | null = null;
  
  // 5. Delete State
  showDeleteModal = false;
  transactionToDeleteId: string | null = null;

  constructor(
    private toastService: ToastService,
    private financialService: FinancialAPIService,
    private auth: AuthService
  ) {}

  ngOnInit(): void {
    const userId = this.auth.getUserId();
    if (userId) {
      this.loadFilters(userId);
      this.fetchTransactions(userId);
    }
  }

  // --- API: Load Data ---
  fetchTransactions(userId: string) {
    this.loading = true;
    this.financialService.getAllByUser(userId).subscribe({
      next: (res: any) => {
        // Backend returns object with 'financials' array
        this.allTransactions = res.financials || []; 
        this.applyFilters();
        this.loading = false;
      },
      error: () => {
        this.toastService.show('Failed to load transactions', 'error');
        this.loading = false;
      }
    });
  }

  loadFilters(userId: string) {
    this.financialService.getFilters(userId).subscribe({
      next: (data: FilterResponse) => {
        // 1. Setup default colors
        const catMap = new Map<string, string>();
        catMap.set('Food', '#f97316');
        catMap.set('Rent', '#dc2626');
        catMap.set('Income', '#16a34a');
        catMap.set('Utilities', '#3b82f6');

        // 2. Merge from current data (so DB colors persist)
        this.allTransactions.forEach(t => {
            if (t.category) {
                catMap.set(t.category, t.color || '#cccccc');
            }
        });

        // 3. Convert to Array for the Modal
        this.categories = Array.from(catMap.entries())
                               .map(([name, color]) => ({ name, color }))
                               .sort((a, b) => a.name.localeCompare(b.name));
        
        // 4. Set Years
        this.years = ['All', ...data.years];
      }
    });
  }

  // --- ACTIONS ---

  openAddModal() {
    this.selectedTransaction = null; 
    this.showModal = true;
  }

  editTransaction(transaction: Financial) {
    this.selectedTransaction = { ...transaction }; 
    this.showModal = true;
  }

  handleSaveTransaction(data: Financial) {
    const userId = this.auth.getUserId();
    if (!userId) return;

    const payload = { ...data, user: userId };

    if (data._id) {
      // UPDATE
      this.financialService.updateRecord(userId, data._id, payload).subscribe({
        next: (updatedTx) => {
          // Update local list instantly
          const index = this.allTransactions.findIndex(t => t._id === updatedTx._id);
          if (index !== -1) this.allTransactions[index] = updatedTx;
          
          this.toastService.show('Transaction updated successfully!', 'success');
          this.applyFilters();
          this.showModal = false;
        },
        error: () => this.toastService.show('Update failed', 'error')
      });
    } else {
      // CREATE
      this.financialService.create(payload).subscribe({
        next: (newTx) => {
          this.allTransactions.unshift(newTx); // Add to top
          this.toastService.show('Transaction added successfully!', 'success');
          this.applyFilters(); 
          this.loadFilters(userId); // Refresh categories
          this.showModal = false;
        },
        error: () => this.toastService.show('Creation failed', 'error')
      });
    }
  }

  deleteTransaction(id: string) {
    if(!id) return;
    this.transactionToDeleteId = id;
    this.showDeleteModal = true;
  }

  confirmDelete() {
    const userId = this.auth.getUserId();
    if (this.transactionToDeleteId && userId) {
      this.financialService.deleteRecord(userId, this.transactionToDeleteId).subscribe({
        next: () => {
          this.allTransactions = this.allTransactions.filter(t => t._id !== this.transactionToDeleteId);
          this.applyFilters();
          this.toastService.show('Transaction deleted!', 'error');
          this.showDeleteModal = false;
        },
        error: () => this.toastService.show('Delete failed', 'error')
      });
    }
  }

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
      
      // 🔥 Category Match Logic
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