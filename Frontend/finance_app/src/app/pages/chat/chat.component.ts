import { Component, ViewChild, ElementRef, AfterViewChecked, OnInit } from '@angular/core';
import { ChatAPIService } from '../../services/chat-api.service';
import { ToastService } from '../../services/toast.service';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  timestamp: Date;
}

@Component({
  selector: 'app-chat',
  standalone: false,
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  messages: ChatMessage[] = [
    { 
      sender: 'bot', 
      text: "Hello! I’m FinanceBot. Tell me to 'Add 50 for lunch' or ask 'How much did I spend on rent?'", 
      timestamp: new Date() 
    }
  ];

  input: string = "";
  loading: boolean = false;

  constructor(
    private chatService: ChatAPIService,
    private toastService: ToastService
  ) {}

  ngOnInit() {
    this.scrollToBottom();
  }

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

    const userText = this.input.trim();
    
    // 1. Add User Message immediately
    this.messages.push({
      sender: 'user',
      text: userText,
      timestamp: new Date()
    });

    this.input = "";
    this.loading = true;

    // 2. Call the Real API
    this.chatService.sendMessage(userText).subscribe({
      next: (res) => {
        
        // 3. Check for Actions (Did the bot create data?)
        if (res.created) {
          this.toastService.show('✅ New Record added', 'success');
          // Ideally, you'd emit a global event here to refresh the dashboard if they were side-by-side
        }

        // 4. Format and Add Bot Response
        const formattedText = this.formatMessage(res.response);
        
        this.messages.push({
          sender: 'bot',
          text: formattedText,
          timestamp: new Date()
        });
        
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.toastService.show('Failed to connect to FinanceBot.', 'error');
        this.messages.push({
          sender: 'bot',
          text: "I'm having trouble reaching my brain right now. Please check the server connection.",
          timestamp: new Date()
        });
        this.loading = false;
      }
    });
  }

  // 🔥 Helper: Converts Markdown to HTML for the chat bubble
  private formatMessage(raw: string): string {
    if (!raw) return '';
    let formatted = raw;

    // Bold: **text** -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Newlines: \n -> <br>
    formatted = formatted.replace(/\n/g, '<br>');

    // Bullet points: - item -> • item
    formatted = formatted.replace(/^- /gm, '• ');

    return formatted;
  }
}