import { Component, OnInit } from '@angular/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { CalendarOptions, EventClickArg, EventInput } from '@fullcalendar/core';

// 🔹 Transaction Interface
export interface Transaction {
  id: string;
  title: string;
  amount: number;
  date: Date; // Javascript Date object
  category: string;
  type: 'income' | 'expense';
}

@Component({
  selector: 'app-calendar',
  standalone: false,
  templateUrl: './calendar.component.html',
  styleUrls: ['./calendar.component.css']
})
export class CalendarComponent implements OnInit {
  
  // 🔹 Modal State
  showModal = false;
  selectedDate: Date | null = null;
  selectedDateStr: string = '';
  
  // 🔹 Data State
  selectedDayTransactions: Transaction[] = [];
  dailyNet: number = 0;

  // 🔹 Master Data (Mock Database)
  allTransactions: Transaction[] = [];

  // 🔹 Category Color Map
  categoryColors: Record<string, string> = {
    'Housing': '#ef4444',      // Red
    'Income': '#22c55e',       // Green
    'Food': '#f59e0b',         // Orange/Amber
    'Transport': '#3b82f6',    // Blue
    'Entertainment': '#8b5cf6',// Purple
    'Utilities': '#64748b',    // Slate
    'Business': '#0ea5e9',     // Sky
    'default': '#6b7280'       // Gray
  };

  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek'
    },
    editable: false, 
    selectable: true,
    
    // ⚡ FIX 1: Rename "all-day" to "Total"
    allDayText: 'Total',

    // ⚡ FIX 2: Max Events & Overlap
    dayMaxEvents: 20, 
    slotEventOverlap: false,
    slotDuration: '00:30:00',
    height: 'auto',

    // 1️⃣ Handle Date Click (Empty Cell) -> Show Log
    dateClick: (info) => {
      this.openDayLog(new Date(info.dateStr));
    },

    // 2️⃣ Handle Event Click (Existing Bar) -> Show Log
    eventClick: (info: EventClickArg) => {
      if (info.event.start) {
        this.openDayLog(info.event.start);
      }
    },

    // 3️⃣ Custom Render
    eventContent: (arg) => {
      const isSummary = arg.event.extendedProps['viewType'] === 'summary';
      const isIncome = arg.event.extendedProps['type'] === 'income';
      const isExpense = arg.event.extendedProps['type'] === 'expense';
      
      // Base classes
      let classes = 'px-2 py-0.5 rounded text-[11px] font-bold w-full truncate text-center transition hover:scale-105 cursor-pointer shadow-sm ';
      let style = '';

      if (isSummary) {
        // --- MONTH VIEW & WEEK HEADER (Net Total) ---
        // We use Tailwind classes for the translucent look
        if (isIncome) classes += 'bg-green-500/20 text-green-400 border border-green-500/50';
        else if (isExpense) classes += 'bg-red-500/20 text-red-400 border border-red-500/50';
      } else {
        // --- WEEK VIEW BODY (Detailed) ---
        // We use the specific Category Color for the background
        const catColor = arg.event.backgroundColor || '#6b7280';
        classes += 'text-white border border-white/10';
        style = `background-color: ${catColor};`;
      }

      return {
        html: `<div class="${classes}" style="${style}">${arg.event.title}</div>`
      };
    },

    events: [] // Populated in ngOnInit
  };

  constructor() {}

  ngOnInit() {
    this.generateDummyData();
    this.updateCalendarEvents();
  }

  // 🔹 1. Generate Dummy Data (Current Month & Week)
  generateDummyData() {
    const today = new Date();
    const currYear = today.getFullYear();
    const currMonth = today.getMonth();

    const transactions: Transaction[] = [
      // -- Past Days --
      { id: '1', title: 'Rent Payment', amount: -1200, date: new Date(currYear, currMonth, 1, 9, 0), category: 'Housing', type: 'expense' },
      { id: '2', title: 'Freelance Gig', amount: 800, date: new Date(currYear, currMonth, 5, 14, 30), category: 'Income', type: 'income' },
      { id: '3', title: 'Grocery Run', amount: -150, date: new Date(currYear, currMonth, 5, 18, 0), category: 'Food', type: 'expense' },
      
      // -- This Week (Around Today) --
      { id: '4', title: 'Client Deposit', amount: 2500, date: new Date(currYear, currMonth, today.getDate(), 10, 0), category: 'Business', type: 'income' },
      { id: '5', title: 'Lunch', amount: -25, date: new Date(currYear, currMonth, today.getDate(), 12, 30), category: 'Food', type: 'expense' },
      { id: '6', title: 'Uber', amount: -45, date: new Date(currYear, currMonth, today.getDate(), 13, 0), category: 'Transport', type: 'expense' },
      
      // -- Tomorrow --
      { id: '7', title: 'Netflix', amount: -15, date: new Date(currYear, currMonth, today.getDate() + 1, 9, 0), category: 'Entertainment', type: 'expense' },
      
      // -- End of Month --
      { id: '8', title: 'Internet Bill', amount: -80, date: new Date(currYear, currMonth, 28, 10, 0), category: 'Utilities', type: 'expense' },
    ];

    this.allTransactions = transactions;
  }

  // 🔹 2. Map Transactions to Calendar Events
  updateCalendarEvents() {
    const events: EventInput[] = [];

    // A. AGGREGATE LOGIC (For Month View & Week Total Row)
    // We sum up Income and Expense per day
    const dailyMap = new Map<string, { income: number, expense: number }>();

    this.allTransactions.forEach(t => {
      const dateKey = t.date.toISOString().split('T')[0]; // YYYY-MM-DD
      if (!dailyMap.has(dateKey)) dailyMap.set(dateKey, { income: 0, expense: 0 });
      
      const stats = dailyMap.get(dateKey)!;
      if (t.type === 'income') stats.income += t.amount;
      else stats.expense += Math.abs(t.amount);
    });

    // Create Summary Events
    dailyMap.forEach((stats, dateStr) => {
      const net = stats.income - stats.expense;

      // Only show if there is activity
      if (net !== 0) {
        events.push({
          title: `${net > 0 ? '+' : '-'}$${Math.abs(net)}`, // E.g. "+$500"
          start: dateStr,
          allDay: true, // 👈 Puts it in the "Total" row in Week View
          // 👇 CHANGED: Removed 'month-view-only' so it shows in Week View "Total" row too
          classNames: [], 
          backgroundColor: 'transparent', 
          borderColor: 'transparent',
          extendedProps: { 
            type: net > 0 ? 'income' : 'expense',
            viewType: 'summary'
          }
        });
      }
    });

    // B. DETAIL LOGIC (For Week View Body)
    // We create an event for EVERY single transaction
    this.allTransactions.forEach(t => {
      events.push({
        title: `${t.title} ($${Math.abs(t.amount)})`,
        start: t.date, // Exact time
        allDay: false,
        classNames: ['week-view-only'], // 👈 CSS Hides this in Month View
        // Use Category Color
        backgroundColor: this.categoryColors[t.category] || this.categoryColors['default'],
        borderColor: 'transparent',
        extendedProps: { 
          type: t.type,
          viewType: 'detail'
        }
      });
    });

    this.calendarOptions.events = events;
  }

  // 🔹 3. Open Logic
  openDayLog(date: Date) {
    this.selectedDate = date;
    this.selectedDateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

    // Filter transactions for this specific day
    this.selectedDayTransactions = this.allTransactions.filter(t => 
      t.date.toDateString() === date.toDateString()
    );

    // Calculate Net for the header
    const income = this.selectedDayTransactions
      .filter(t => t.type === 'income')
      .reduce((sum, t) => sum + t.amount, 0);
    const expense = this.selectedDayTransactions
      .filter(t => t.type === 'expense')
      .reduce((sum, t) => sum + t.amount, 0);
    
    this.dailyNet = income + expense; // Expense is negative in data
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
  }

  // Helper for modal colors
  getAmountColor(amount: number): string {
    return amount >= 0 ? 'text-green-400' : 'text-red-400';
  }
}