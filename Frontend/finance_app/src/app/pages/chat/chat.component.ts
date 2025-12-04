import { Component, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  timestamp: Date; // Added timestamp for realism
}

@Component({
  selector: 'app-chat',
  standalone: false,
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css'
})
export class ChatComponent implements AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  messages: ChatMessage[] = [
    { sender: 'bot', text: "Hello! I’m FinanceBot. How can I help you today?", timestamp: new Date() }
  ];

  input: string = "";
  loading: boolean = false;

  // Auto-scroll logic
  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }

  sendMessage() {
    if (!this.input.trim()) return;

    const userMessage: ChatMessage = {
      sender: 'user',
      text: this.input.trim(),
      timestamp: new Date()
    };

    this.messages.push(userMessage);
    this.input = "";
    this.loading = true;

    // Simulate bot API
    setTimeout(() => {
      const botReply: ChatMessage = {
        sender: 'bot',
        text: this.generateMockReply(userMessage.text),
        timestamp: new Date()
      };
      this.messages.push(botReply);
      this.loading = false;
    }, 1200);
  }

  generateMockReply(text: string): string {
    return `You asked: "${text}". I’ll analyze your transactions soon!`;
  }
}