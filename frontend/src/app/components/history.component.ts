import { Component, OnInit } from '@angular/core';
import { HistoryService } from '../services/history.service';
import { ChatMessage } from '../models/models';

@Component({
  selector: 'app-history',
  template: `
    <div class="history-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Chat History</mat-card-title>
        </mat-card-header>
        
        <mat-card-content>
          <div *ngIf="loading" class="loading">
            <mat-spinner></mat-spinner>
          </div>
          
          <div *ngIf="!loading && messages.length === 0" class="empty">
            <mat-icon>history</mat-icon>
            <p>No chat history yet</p>
          </div>
          
          <div class="messages-list" *ngIf="!loading && messages.length > 0">
            <mat-card *ngFor="let msg of messages" class="message-card">
              <mat-card-header>
                <mat-card-title>
                  <mat-icon>{{ msg.role === 'user' ? 'person' : 'smart_toy' }}</mat-icon>
                  {{ msg.role === 'user' ? 'You' : 'Assistant' }}
                </mat-card-title>
                <mat-card-subtitle>{{ msg.timestamp | date:'medium' }}</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <p>{{ msg.content }}</p>
              </mat-card-content>
            </mat-card>
          </div>
          
          <div class="pagination" *ngIf="totalCount > limit">
            <button mat-button [disabled]="offset === 0" (click)="previousPage()">
              <mat-icon>chevron_left</mat-icon>
              Previous
            </button>
            <span>{{ offset + 1 }} - {{ Math.min(offset + limit, totalCount) }} of {{ totalCount }}</span>
            <button mat-button [disabled]="offset + limit >= totalCount" (click)="nextPage()">
              Next
              <mat-icon>chevron_right</mat-icon>
            </button>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .history-container {
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .loading {
      text-align: center;
      padding: 40px;
    }
    .empty {
      text-align: center;
      padding: 40px;
      color: #999;
    }
    .empty mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
    }
    .messages-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-height: 70vh;
      overflow-y: auto;
    }
    .message-card mat-card-header {
      margin-bottom: 8px;
    }
    .message-card mat-icon {
      vertical-align: middle;
      margin-right: 8px;
    }
    .pagination {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 16px;
      margin-top: 20px;
    }
  `]
})
export class HistoryComponent implements OnInit {
  messages: ChatMessage[] = [];
  loading = false;
  limit = 50;
  offset = 0;
  totalCount = 0;
  Math = Math;

  constructor(private historyService: HistoryService) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading = true;
    this.historyService.getHistory(this.limit, this.offset).subscribe({
      next: (response) => {
        this.messages = response.messages;
        this.totalCount = response.total_count;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load history:', err);
        this.loading = false;
      }
    });
  }

  nextPage(): void {
    if (this.offset + this.limit < this.totalCount) {
      this.offset += this.limit;
      this.loadHistory();
    }
  }

  previousPage(): void {
    if (this.offset > 0) {
      this.offset = Math.max(0, this.offset - this.limit);
      this.loadHistory();
    }
  }
}
