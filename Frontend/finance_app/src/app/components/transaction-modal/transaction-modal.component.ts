import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges } from '@angular/core';
import { CategoryColor } from '../../models/api_models';
import { ToastService } from '../../services/toast.service'; // 🔥 Import ToastService

@Component({
  selector: 'app-transaction-modal',
  standalone: false,
  templateUrl: './transaction-modal.component.html',
  styleUrls: ['./transaction-modal.component.css']
})
export class TransactionModalComponent implements OnChanges {
  @Input() visible = false;
  @Input() categories: CategoryColor[] = []; 

  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<any>();

  isEditMode = false;
  isCustomCategory = false;
  
  warningMessage: string | null = null;
  errorMessage: string | null = null;

  transaction = {
    _id: null as string | null,
    title: '',
    amount: null as number | null,
    date: new Date().toISOString().split('T')[0], 
    type: 'expense', 
    category: '', 
    customCategory: '',
    color: '#f59e0b'
  };

  get filteredCategories() {
    return this.categories.filter(c => 
      c.name.toLowerCase() !== 'income' && 
      c.name.toLowerCase() !== 'expense'
    );
  }

  // 🔥 Inject ToastService here
  constructor(private toastService: ToastService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['visible'] && this.visible && !this.isEditMode) {
      this.resetForm();
    }
  }

  @Input() set transactionData(data: any) {
    if (data) {
      this.isEditMode = true;
      this.transaction = { ...data };
      
      if (typeof this.transaction.date === 'string' && this.transaction.date.includes('T')) {
        this.transaction.date = this.transaction.date.split('T')[0];
      }
      this.transaction.amount = Math.abs(this.transaction.amount || 0);

      const knownCat = this.categories.find(c => c.name === this.transaction.category);
      if (!knownCat && this.transaction.category) {
        this.transaction.customCategory = this.transaction.category;
        this.transaction.category = 'new';
        this.isCustomCategory = true;
      }
    } else {
      this.resetForm();
    }
  }

  resetForm() {
    this.isEditMode = false;
    this.warningMessage = null;
    this.errorMessage = null;
    this.isCustomCategory = false;
    
    this.transaction = {
      _id: null,
      title: '',
      amount: null,
      date: new Date().toISOString().split('T')[0],
      type: 'expense',
      category: '', 
      customCategory: '',
      color: '#f59e0b'
    };
  }

  onCategoryChange() {
    this.warningMessage = null;
    this.errorMessage = null;

    if (this.transaction.category === 'new') {
      this.isCustomCategory = true;
      this.transaction.color = '#6b7280'; 
    } else {
      this.isCustomCategory = false;
      const selected = this.categories.find(c => c.name === this.transaction.category);
      if (selected) {
        this.transaction.color = selected.color;
      }
    }
  }

  onColorChange() {
    if (!this.isCustomCategory && this.transaction.category) {
      const original = this.categories.find(c => c.name === this.transaction.category);
      if (original && original.color !== this.transaction.color) {
        this.warningMessage = `Note: This will change the color for "${this.transaction.category}" everywhere.`;
      } else {
        this.warningMessage = null;
      }
    }
  }

  onSubmit() {
    this.errorMessage = null;
    
    // 🔥 VALIDATION CHECK
    if (!this.transaction.title || !this.transaction.amount || !this.transaction.date) {
      this.toastService.show('Please fill in all required fields.', 'error');
      return;
    }

    if (this.transaction.category === '' && !this.isCustomCategory) {
      this.toastService.show('Please select a category.', 'error');
      return;
    }

    if (this.isCustomCategory && !this.transaction.customCategory.trim()) {
      this.toastService.show('Please enter a name for the new category.', 'error');
      return;
    }

    const finalCategory = this.isCustomCategory ? this.transaction.customCategory.trim() : this.transaction.category;

    const lowerCat = finalCategory.toLowerCase();
    if (lowerCat === 'income' || lowerCat === 'expense') {
      this.errorMessage = `"${finalCategory}" is a restricted name.`;
      this.toastService.show(this.errorMessage, 'error'); // Also show as toast
      return; 
    }

    const finalAmount = Math.abs(this.transaction.amount);
    const payload = {
      ...this.transaction,
      amount: finalAmount,
      category: finalCategory,
      color: this.transaction.color 
    };

    this.save.emit(payload);
  }

  closeModal() {
    this.close.emit();
    setTimeout(() => this.resetForm(), 300);
  }
}