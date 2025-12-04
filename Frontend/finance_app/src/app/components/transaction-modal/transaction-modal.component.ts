import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-transaction-modal',
  standalone: false,
  templateUrl: './transaction-modal.component.html',
  styleUrls: ['./transaction-modal.component.css']
})
export class TransactionModalComponent {
  @Input() visible = false;
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<any>();

  // Input to pre-fill form for editing
  @Input() set transactionData(data: any) {
    if (data) {
      this.isEditMode = true;
      this.transaction = { ...data };
      // Ensure date is YYYY-MM-DD
      if (this.transaction.date.includes('T')) {
        this.transaction.date = this.transaction.date.split('T')[0];
      }
      this.transaction.amount = Math.abs(this.transaction.amount || 0);
      
      // Handle custom categories logic if needed
      const isStandard = this.categories.some(c => c.name === this.transaction.category);
      if (!isStandard) {
        this.transaction.category = 'new';
        this.transaction.customCategory = data.category;
        this.isCustomCategory = true;
      }
    } else {
      this.resetForm();
    }
  }

  isEditMode = false;

  // Default Categories with preset colors
  categories = [
    { name: 'Rent', color: '#dc2626' },      // Red
    { name: 'Groceries', color: '#f59e0b' }, // Amber
    { name: 'Salary', color: '#16a34a' },    // Green
    { name: 'Utilities', color: '#3b82f6' }, // Blue
    { name: 'Entertainment', color: '#8b5cf6' }, // Purple
    { name: 'Health', color: '#ec4899' },    // Pink
    { name: 'Food', color: '#f97316' }       // Orange
  ];

  // Form Model
  transaction = {
    id: null as number | null, // Added ID to track edits
    title: '',
    amount: null as number | null,
    date: new Date().toISOString().split('T')[0], 
    type: 'expense', 
    category: 'Groceries',
    customCategory: '',
    color: '#f59e0b'
  };

  isCustomCategory = false;

  resetForm() {
    this.isEditMode = false;
    this.transaction = {
      id: null,
      title: '',
      amount: null,
      date: new Date().toISOString().split('T')[0],
      type: 'expense',
      category: 'Groceries',
      customCategory: '',
      color: '#f59e0b'
    };
    this.isCustomCategory = false;
  }

  onCategoryChange() {
    if (this.transaction.category === 'new') {
      this.isCustomCategory = true;
      this.transaction.color = '#6b7280'; 
    } else {
      this.isCustomCategory = false;
      const selected = this.categories.find(c => c.name === this.transaction.category);
      if (selected) this.transaction.color = selected.color;
    }
  }

  onSubmit() {
    if (!this.transaction.title || !this.transaction.amount) return;

    // Final Data Prep
    const finalAmount = this.transaction.type === 'expense' 
      ? -Math.abs(this.transaction.amount) 
      : Math.abs(this.transaction.amount);

    const finalCategory = this.isCustomCategory ? this.transaction.customCategory : this.transaction.category;

    const transactionPayload = {
      ...this.transaction, // Keep ID if exists
      amount: finalAmount,
      category: finalCategory,
      backgroundColor: this.transaction.color
    };

    this.save.emit(transactionPayload);
    this.closeModal();
  }

  closeModal() {
    this.close.emit();
    setTimeout(() => this.resetForm(), 300); // Reset after animation
  }
}