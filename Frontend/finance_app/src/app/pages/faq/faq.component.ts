import { Component } from '@angular/core';

@Component({
  selector: 'app-faq',
  standalone: false,
  templateUrl: './faq.component.html',
  styleUrls: ['./faq.component.css']
})
export class FaqComponent {
  // Generic Financial Bot Data
  faqs = [
    {
      question: "Is my financial data secure?",
      answer: "Security is our top priority. We use industry-standard AES-256 encryption to store your data and never share your personal information with third parties.",
      open: true // First one open by default
    },
    {
      question: "Can I connect multiple bank accounts?",
      answer: "Yes! You can link unlimited checking, savings, and credit card accounts to get a complete view of your net worth in one dashboard.",
      open: false
    },
    {
      question: "How accurate is the AI bot?",
      answer: "Our AI is trained on vast financial datasets to categorize transactions and provide insights. While highly accurate, we always recommend reviewing your data periodically.",
      open: false
    },
    {
      question: "Is there a mobile app?",
      answer: "Currently, we offer a fully responsive web application that works perfectly on mobile browsers. A dedicated native app is coming in Q4.",
      open: false
    },
    {
      question: "How do I reset my password?",
      answer: "Go to the login page and click 'Forgot Password'. We will send a secure link to your email address to reset it.",
      open: false
    }
  ];

  toggle(index: number) {
    // Toggle the clicked item
    this.faqs[index].open = !this.faqs[index].open;
    
    // Optional: Close all others when one opens (Accordian style)
    // this.faqs.forEach((item, i) => {
    //   if (i !== index) item.open = false;
    // });
  }
}