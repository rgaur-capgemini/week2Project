import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MarkdownModule } from 'ngx-markdown';
import { AuthService, User } from '../../services/auth.service';
import { ChatService, ChatMessage, ChatSession, QueryRequest } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MarkdownModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  
  currentUser: User | null = null;
  sessions: ChatSession[] = [];
  currentSession: ChatSession | null = null;
  messages: ChatMessage[] = [];
  
  queryText: string = '';
  isLoading: boolean = false;
  sidebarOpen: boolean = true;
  
  constructor(
    private authService: AuthService,
    private chatService: ChatService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });
    
    this.loadSessions();
  }

  loadSessions(): void {
    this.chatService.getSessions(50, 0).subscribe({
      next: (sessions) => {
        this.sessions = sessions;
      },
      error: (error) => {
        console.error('Failed to load sessions', error);
      }
    });
  }

  selectSession(session: ChatSession): void {
    this.currentSession = session;
    this.chatService.getSessionHistory(session.session_id).subscribe({
      next: (response) => {
        this.messages = response.messages;
        this.scrollToBottom();
      },
      error: (error) => {
        console.error('Failed to load session history', error);
      }
    });
  }

  startNewChat(): void {
    this.currentSession = null;
    this.messages = [];
    this.queryText = '';
  }

  sendQuery(): void {
    if (!this.queryText.trim() || this.isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: this.queryText,
      timestamp: new Date().toISOString()
    };

    this.messages.push(userMessage);
    this.isLoading = true;

    const request: QueryRequest = {
      query: this.queryText,
      session_id: this.currentSession?.session_id,
      top_k: 5,
      use_reranking: true
    };

    const queryTextCopy = this.queryText;
    this.queryText = '';
    this.scrollToBottom();

    this.chatService.query(request).subscribe({
      next: (response) => {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.answer,
          timestamp: new Date().toISOString(),
          metadata: response.metadata
        };

        this.messages.push(assistantMessage);
        
        // Update current session if new
        if (!this.currentSession) {
          this.loadSessions();
          // Set current session to the new one
          setTimeout(() => {
            if (this.sessions.length > 0) {
              this.currentSession = this.sessions[0];
            }
          }, 500);
        }

        this.isLoading = false;
        this.scrollToBottom();
      },
      error: (error) => {
        console.error('Query failed', error);
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString()
        };
        this.messages.push(errorMessage);
        this.isLoading = false;
        this.scrollToBottom();
      }
    });
  }

  deleteSession(session: ChatSession, event: Event): void {
    event.stopPropagation();
    
    if (confirm(`Delete chat "${session.title}"?`)) {
      this.chatService.deleteSession(session.session_id).subscribe({
        next: () => {
          this.sessions = this.sessions.filter(s => s.session_id !== session.session_id);
          if (this.currentSession?.session_id === session.session_id) {
            this.startNewChat();
          }
        },
        error: (error) => {
          console.error('Failed to delete session', error);
        }
      });
    }
  }

  logout(): void {
    this.authService.logout();
  }

  goToAdmin(): void {
    this.router.navigate(['/admin']);
  }

  toggleSidebar(): void {
    this.sidebarOpen = !this.sidebarOpen;
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    }, 100);
  }

  get isAdmin(): boolean {
    return this.currentUser?.role === 'admin';
  }
}
