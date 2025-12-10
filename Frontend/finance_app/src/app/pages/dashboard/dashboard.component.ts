import { Component, OnInit } from '@angular/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { CalendarOptions } from '@fullcalendar/core';
import { Chart, registerables } from 'chart.js'; 
import { FinancialAPIService } from '../../services/finance-api.service';
import { AuthService } from '../../services/auth.service';
import { Financial, DashboardStats, CategoryColor } from '../../models/api_models';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: false,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  showTransactionModal = false; 
  chartInstance: any = null; 
  categoryChartInstance: any = null;

  // Real Data Containers
  recentTransactions: Financial[] = [];
  allTransactions: Financial[] = [];
  stats: DashboardStats | null = null;
  
  // 🔥 This list is now built dynamically from your DB data
  categories: CategoryColor[] = []; 

  // Calendar Config
  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    headerToolbar: { left: 'title', center: '', right: '' },
    height: 350,
    eventContent: (arg) => {
      return {
        html: `<div class="text-[10px] md:text-xs font-bold text-center leading-tight truncate">
                 ${arg.event.title}
               </div>`
      };
    },
    events: []
  };

  constructor(
    private financialService: FinancialAPIService,
    private auth: AuthService
  ) {}

  ngOnInit(): void {
    this.fetchData();
  }

  fetchData() {
    const userId = this.auth.getUserId();
    if (!userId) return;

    // 1. Get Summary Stats (Cards, Doughnut)
    this.financialService.getStats(userId).subscribe(data => {
      this.stats = data;
      this.recentTransactions = data.recentTransactions;
      this.initCategoryChart(data.categoryStats);
    });

    // 2. Get All Transactions (For Line Chart, Calendar, and Modal Categories)
    this.financialService.getAllByUser(userId).subscribe((res: any) => {
      this.allTransactions = res.financials || [];
      
      // 🔥 RE-ADDED: Extract categories from the data we just fetched
      this.extractCategories();
      
      this.generateCalendarEvents();
      this.initLineChart(); 
    });
  }

  // --- HELPER: Build Unique Category List with Colors ---
  extractCategories() {
    const catMap = new Map<string, string>();
    
    // 1. Seed with some defaults (so new users aren't empty)
    catMap.set('Rent', '#dc2626');
    catMap.set('Groceries', '#f59e0b');
    catMap.set('Salary', '#16a34a');
    catMap.set('Utilities', '#3b82f6');
    catMap.set('Entertainment', '#8b5cf6');

    // 2. Overwrite/Add from actual DB transactions
    // This ensures if you changed "Rent" to Blue in the DB, the dropdown shows Blue.
    this.allTransactions.forEach(t => {
      if (t.category) {
        catMap.set(t.category, t.color || '#cccccc');
      }
    });

    // 3. Convert Map to Array for the Modal
    this.categories = Array.from(catMap.entries())
      .map(([name, color]) => ({ name, color }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  // --- ACTIONS ---
  openAddTransaction() {
    this.showTransactionModal = true;
  }

  closeTransactionModal() {
    this.showTransactionModal = false;
  }

  handleNewTransaction(newTx: Financial) {
    const userId = this.auth.getUserId();
    if (!userId) return;
    
    this.financialService.create({ ...newTx, user: userId }).subscribe(() => {
      this.showTransactionModal = false;
      this.fetchData(); // Refresh everything
    });
  }

  // --- CALENDAR LOGIC ---
  generateCalendarEvents() {
    const dailyStats: Record<string, { income: number, expense: number }> = {};

    this.allTransactions.forEach(t => {
      const dStr = new Date(t.date).toISOString().split('T')[0];
      
      if (!dailyStats[dStr]) dailyStats[dStr] = { income: 0, expense: 0 };
      
      if (t.type === 'income') dailyStats[dStr].income += t.amount;
      else dailyStats[dStr].expense += Math.abs(t.amount);
    });

    const events = [];
    for (const [date, stats] of Object.entries(dailyStats)) {
      if (stats.income > 0) {
        events.push({ title: `+ $${stats.income}`, date: date, backgroundColor: '#4ade80', borderColor: 'transparent' });
      }
      if (stats.expense > 0) {
        events.push({ title: `- $${stats.expense}`, date: date, backgroundColor: '#f87171', borderColor: 'transparent' });
      }
    }
    this.calendarOptions.events = events;
  }

  // --- CHARTS ---
  initCategoryChart(categoryStats: { _id: string, total: number, color: string }[]) {
    if (this.categoryChartInstance) this.categoryChartInstance.destroy();
    if (!categoryStats || categoryStats.length === 0) return;

    this.categoryChartInstance = new Chart("categoryChart", {
      type: 'doughnut',
      data: {
        labels: categoryStats.map(c => c._id),
        datasets: [{
          data: categoryStats.map(c => c.total),
          backgroundColor: categoryStats.map(c => c.color || '#cccccc'),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#9ca3af' } } }
      }
    });
  }

  initLineChart() {
    if (this.chartInstance) this.chartInstance.destroy();

    const monthLabels: string[] = [];
    const incomeData: number[] = [];
    const expenseData: number[] = [];
    const today = new Date();
    
    for (let i = 5; i >= 0; i--) {
      const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
      const monthName = d.toLocaleString('default', { month: 'short' });
      monthLabels.push(monthName);

      const monthTx = this.allTransactions.filter(t => {
        const tDate = new Date(t.date);
        return tDate.getMonth() === d.getMonth() && tDate.getFullYear() === d.getFullYear();
      });

      const inc = monthTx.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0);
      const exp = monthTx.filter(t => t.type === 'expense').reduce((sum, t) => sum + Math.abs(t.amount), 0);

      incomeData.push(inc);
      expenseData.push(exp);
    }

    this.chartInstance = new Chart("cashFlowChart", {
      type: 'line',
      data: {
        labels: monthLabels,
        datasets: [
          {
            label: 'Income',
            data: incomeData,
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.4
          },
          {
            label: 'Expenses',
            data: expenseData,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#9ca3af' } } },
        scales: {
          y: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
          x: { ticks: { color: '#9ca3af' }, grid: { display: false } }
        }
      }
    });
  }
}