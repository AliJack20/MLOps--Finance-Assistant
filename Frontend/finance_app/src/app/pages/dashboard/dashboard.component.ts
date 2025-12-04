import { Component, OnInit } from '@angular/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { CalendarOptions } from '@fullcalendar/core';
import { Chart, registerables } from 'chart.js'; 

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: false,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
showTransactionModal = false; // Control modal visibility
  chartInstance: any = null; // Store chart instance to update it
  categoryChartInstance: any = null;
  // 1. Recent Transactions (For the list view)
  recentTransactions = [
    { title: 'Grocery Store', amount: -120.50, date: new Date(), category: 'Food' },
    { title: 'Freelance Payment', amount: 1500.00, date: new Date(new Date().setDate(new Date().getDate() - 2)), category: 'Income' },
    { title: 'Netflix Subscription', amount: -15.99, date: new Date(new Date().setDate(new Date().getDate() - 5)), category: 'Entertainment' },
    { title: 'Gas Station', amount: -45.00, date: new Date(new Date().setDate(new Date().getDate() - 6)), category: 'Transport' },
  ];

  // 2. All Transactions (Mock DB for Charts & Calendar)
  allTransactions = [
    { date: '2025-10-01', amount: -1200, category: 'Rent' },
    { date: '2025-10-05', amount: -65, category: 'Groceries' },
    { date: '2025-10-05', amount: -35, category: 'Internet' },
    { date: '2025-10-15', amount: 4200, category: 'Salary' },
    { date: '2025-10-20', amount: -120, category: 'Utilities' },
    { date: '2025-10-28', amount: -50, category: 'Dinner' },
    // Added November dates to match your manual example
    { date: '2025-11-23', amount: -1200, category: 'Rent' },
    { date: '2025-11-22', amount: 4200, category: 'Salary' },
    { date: '2025-11-30', amount: -150, category: 'Bill' },
  ];

  // 3. Calendar Config
  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'title',
      center: '',
      right: '' // Hide nav buttons for clean mini view
    },
    height: 350, // Slightly taller to fit text
    
    // 👇 Render Custom Text (Income/Expense Sums)
    eventContent: (arg) => {
      const color = arg.event.backgroundColor; 
      console.log('Event', arg.event.title);
      return {
        html: `<div class="text-[10px] md:text-xs font-bold text-center leading-tight truncate">
                 ${arg.event.title}
               </div>`
      };
    },

    events: [] // Will be populated by generateCalendarEvents()
  };

  constructor() {}

  openAddTransaction() {
    this.showTransactionModal = true;
  }

  // 👇 CLOSE MODAL
  closeTransactionModal() {
    this.showTransactionModal = false;
  }

  // 👇 HANDLE NEW TRANSACTION (The Magic)
  handleNewTransaction(newTx: any) {
    // 1. Add to master list
    this.allTransactions.push(newTx);
    
    // 2. Update Recent List (Sort by date descending first usually, but for now just unshift)
    this.recentTransactions.unshift(newTx);
    
    // 3. Refresh Calendar
    this.generateCalendarEvents(); 
    
    // 4. Refresh Charts (Simple re-init for now, or push data if you want to be fancy)
    // Destroy old charts to prevent "canvas already in use" error
    if(this.chartInstance) this.chartInstance.destroy();
    if(this.categoryChartInstance) this.categoryChartInstance.destroy();
    this.initCharts();

    this.showTransactionModal = false;
  }

  ngOnInit(): void {
    this.initCharts();
    this.generateCalendarEvents();
  }

  // 🔹 Helper: Sums up transactions by date
  generateCalendarEvents() {
    const dailyStats: Record<string, { income: number, expense: number }> = {};

    // 1. Aggregate totals per day
    this.allTransactions.forEach(t => {
      if (!dailyStats[t.date]) dailyStats[t.date] = { income: 0, expense: 0 };
      
      if (t.amount > 0) {
        dailyStats[t.date].income += t.amount;
      } else {
        dailyStats[t.date].expense += Math.abs(t.amount);
      }
    });

    // 2. Create Events
    const events = [];
    for (const [date, stats] of Object.entries(dailyStats)) {
      // Income Event (Green)
      if (stats.income > 0) {
        events.push({
          title: `+ $${stats.income}`,
          date: date,
          backgroundColor: '#4ade80', // Tailwind green-400
          borderColor: 'transparent'
        });
      }
      
      // Expense Event (Red)
      if (stats.expense > 0) {
        events.push({
          title: `- $${stats.expense}`,
          date: date,
          backgroundColor: '#f87171', // Tailwind red-400
          borderColor: 'transparent'
        });
      }
    }

    this.calendarOptions.events = events;
  }

  initCharts() {
    // 1. Cash Flow Chart (Line)
   this.chartInstance = new Chart("cashFlowChart", {
      type: 'line',
      data: {
        labels: ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
        datasets: [
          {
            label: 'Income',
            data: [3000, 3200, 4500, 3100, 4200, 4000],
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.4
          },
          {
            label: 'Expenses',
            data: [2000, 1800, 2500, 2100, 1900, 1850],
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

    // 2. Category Chart (Doughnut)
    this.categoryChartInstance=new Chart("categoryChart", {
      type: 'doughnut',
      data: {
        labels: ['Food', 'Transport', 'Utilities', 'Entertainment', 'Savings'],
        datasets: [{
          data: [35, 15, 20, 10, 20],
          backgroundColor: ['#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#22c55e'],
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
}