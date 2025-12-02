import { Component } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router'; // 1. Import Router
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  standalone: false
})
export class AppComponent {
  title = 'FinanceBot';
  theme: string = 'dark';
  showNavbar: boolean = true; // 2. Add a flag for visibility

  // 3. Inject Router and listen for changes
  constructor(private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      // If the URL contains '/chat', hide the navbar
      this.showNavbar = !event.url.includes('/chat');
    });
  }
}