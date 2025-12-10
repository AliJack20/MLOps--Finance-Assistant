import { Component, OnInit } from '@angular/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { CalendarOptions, EventClickArg, EventInput } from '@fullcalendar/core';
import { FinancialAPIService } from '../../services/finance-api.service';
import { AuthService } from '../../services/auth.service';
import { Financial, CategoryColor } from '../../models/api_models';

@Component({
  selector: 'app-calendar',
  standalone: false,
  templateUrl: './calendar.component.html',
  styleUrls: ['./calendar.component.css']
})
export class CalendarComponent implements OnInit {
  
  // 🔹 Modal State
  showDayModal = false;
  showAddModal = false;
  
  // 🔹 Selection Data
  selectedDateStr: string = ''; // Display string (e.g. "Wed, Dec 3")
  currentDateKey: string = '';  // Logic key (e.g. "2025-12-03")
  
  selectedDayTransactions: Financial[] = [];
  dailyNet: number = 0;

  // 🔹 Master Data
  allTransactions: Financial[] = [];
  categories: CategoryColor[] = [];

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
    allDayText: 'Total',
    dayMaxEvents: 20, 
    slotEventOverlap: false,
    height: 'auto',

    // 1️⃣ Handle Date Click (Empty Cell)
    dateClick: (info) => {
      // info.dateStr is "YYYY-MM-DD" (Stable)
      this.openDayLog(info.dateStr); 
    },

    // 2️⃣ Handle Event Click (Existing Bar)
    eventClick: (info: EventClickArg) => {
      if (info.event.start) {
        // Extract YYYY-MM-DD from the event start date manually to avoid timezone shifts
        // info.event.startStr is ISO8601 (e.g. 2025-12-03T00:00:00)
        const dateStr = info.event.startStr.split('T')[0];
        this.openDayLog(dateStr);
      }
    },

    // 3️⃣ Custom Render
    eventContent: (arg) => {
      const isSummary = arg.event.extendedProps['viewType'] === 'summary';
      let classes = 'px-2 py-0.5 rounded text-[11px] font-bold w-full truncate text-center transition hover:scale-105 cursor-pointer shadow-sm ';
      let style = '';

      if (isSummary) {
        const isIncome = arg.event.extendedProps['type'] === 'income';
        if (isIncome) classes += 'bg-green-500/20 text-green-400 border border-green-500/50';
        else classes += 'bg-red-500/20 text-red-400 border border-red-500/50';
      } else {
        const catColor = arg.event.backgroundColor || '#6b7280';
        classes += 'text-white border border-white/10';
        style = `background-color: ${catColor};`;
      }

      return {
        html: `<div class="${classes}" style="${style}">${arg.event.title}</div>`
      };
    },

    events: [] 
  };

  constructor(
    private financialService: FinancialAPIService,
    private auth: AuthService
  ) {}

  ngOnInit() {
    this.fetchData();
  }

  fetchData() {
    const userId = this.auth.getUserId();
    if (!userId) return;

    // 1. Fetch Transactions
    this.financialService.getAllByUser(userId).subscribe((res: any) => {
      this.allTransactions = res.financials || [];
      
      // 2. Extract Categories (for the modal)
      this.extractCategories();
      
      // 3. Map to Calendar
      this.updateCalendarEvents();
    });
  }

  extractCategories() {
    const catMap = new Map<string, string>();
    // Defaults
    catMap.set('Food', '#f97316');
    catMap.set('Rent', '#dc2626');
    
    this.allTransactions.forEach(t => {
        if (t.category) catMap.set(t.category, t.color || '#cccccc');
    });
    
    this.categories = Array.from(catMap.entries())
                           .map(([name, color]) => ({ name, color }))
                           .sort((a, b) => a.name.localeCompare(b.name));
  }

  // 🔥 HELPER: Get Date String without Timezone conversion
  private getDateKey(dateInput: Date | string): string {
    if (!dateInput) return '';
    // If it's a string (from DB), just take the first 10 chars "2025-12-03"
    if (typeof dateInput === 'string') {
        return dateInput.substring(0, 10);
    }
    // If it's a Date object, convert to ISO string and take first 10
    return dateInput.toISOString().split('T')[0];
  }

  updateCalendarEvents() {
    const events: EventInput[] = [];
    const dailyMap = new Map<string, { income: number, expense: number }>();

    this.allTransactions.forEach(t => {
      // 🔥 FIX: Use String slicing instead of Date object manipulation
      const dateKey = this.getDateKey(t.date);
      
      if (!dailyMap.has(dateKey)) dailyMap.set(dateKey, { income: 0, expense: 0 });
      const stats = dailyMap.get(dateKey)!;

      if (t.type === 'income') stats.income += t.amount;
      else stats.expense += Math.abs(t.amount);
    });

    // A. Summary Events (The Totals)
    dailyMap.forEach((stats, dateStr) => {
      const net = stats.income - stats.expense;
      if (net !== 0) {
        events.push({
          title: `${net > 0 ? '+' : '-'}$${Math.abs(net)}`,
          start: dateStr, // "2025-12-03"
          allDay: true,   // 🔥 Puts it in the top row for Week View
          classNames: [], 
          backgroundColor: 'transparent', 
          borderColor: 'transparent',
          extendedProps: { type: net > 0 ? 'income' : 'expense', viewType: 'summary' }
        });
      }
    });

    // B. Detail Events (The individual items)
    this.allTransactions.forEach(t => {
      const dateKey = this.getDateKey(t.date);

      events.push({
        title: `${t.title} ($${Math.abs(t.amount)})`,
        start: dateKey, // Force string date
        allDay: false,
        classNames: ['week-view-only'], // Hide in Month view via CSS
        backgroundColor: t.color || '#6b7280', 
        borderColor: 'transparent',
        extendedProps: { type: t.type, viewType: 'detail' }
      });
    });

    this.calendarOptions.events = events;
  }

  // --- Day Detail Modal ---
  openDayLog(dateStr: string) {
    // dateStr is "YYYY-MM-DD" passed directly from FullCalendar
    this.currentDateKey = dateStr; 

    // Create a visual date object (Force Local Time for correct formatting)
    // appending T00:00:00 ensures the browser treats it as local time, not UTC
    const visualDate = new Date(dateStr + 'T00:00:00');
    this.selectedDateStr = visualDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

    // 🔥 Filter using string comparison to avoid timezone shifts
    this.selectedDayTransactions = this.allTransactions.filter(t => {
       return this.getDateKey(t.date) === this.currentDateKey;
    });

    const income = this.selectedDayTransactions.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0);
    const expense = this.selectedDayTransactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + t.amount, 0);
    this.dailyNet = income - expense;

    this.showDayModal = true;
  }

  closeDayModal() {
    this.showDayModal = false;
  }

  // --- Add Transaction Logic ---
  openAddModal() {
    this.showDayModal = false; // Close detail modal first
    this.showAddModal = true;  // Open add modal
  }

  closeAddModal() {
    this.showAddModal = false;
  }

  handleNewTransaction(newTx: Financial) {
    const userId = this.auth.getUserId();
    if (!userId) return;

    this.financialService.create({ ...newTx, user: userId }).subscribe(() => {
      this.showAddModal = false;
      this.fetchData(); // Refresh calendar data
      // Re-open the day log to show the new item
      if (this.currentDateKey) this.openDayLog(this.currentDateKey);
    });
  }

  getAmountColor(amount: number): string {
    return amount >= 0 ? 'text-green-400' : 'text-red-400';
  }
}