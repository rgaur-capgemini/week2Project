import { Component } from '@angular/core';
import { ChatService } from '../services/chat.service';
import { ChatMessage } from '../models/models';

@Component({
  selector: 'app-chat',
  template: `
    <div class="chat-container">
      <mat-card class="chat-card">
        <mat-card-header>
          <mat-card-title>RAG Chat</mat-card-title>
        </mat-card-header>
        
        <mat-card-content class="messages-container">
          <div *ngFor="let msg of messages" class="message" [class.user]="msg.role === 'user'">
            <strong>{{ msg.role === 'user' ? 'You' : 'Assistant' }}:</strong>
            <p>{{ msg.content }}</p>
          </div>
          <div *ngIf="loading" class="loading">
            <mat-spinner diameter="30"></mat-spinner>
          </div>
        </mat-card-content>
        
        <mat-card-actions class="input-container">
          <mat-form-field class="full-width">
            <textarea matInput placeholder="Ask a question..." [(ngModel)]="question" 
                      (keyup.enter)="!loading && sendMessage()" rows="3"></textarea>
          </mat-form-field>
          <button mat-raised-button color="primary" (click)="sendMessage()" [disabled]="loading || !question.trim()">
            <mat-icon>send</mat-icon>
            Send
          </button>
        </mat-card-actions>
      </mat-card>
      
      <mat-card class="upload-card">
        <mat-card-header>
          <mat-card-title>Upload Documents</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <input type="file" #fileInput (change)="onFileSelected($event)" multiple accept=".pdf,.txt,.docx">
          <button mat-raised-button color="accent" (click)="uploadFiles()" [disabled]="!selectedFiles || uploading">
            <mat-icon>upload</mat-icon>
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .chat-container {
      display: flex;
      gap: 20px;
      padding: 20px;
      height: calc(100vh - 100px);
    }
    .chat-card {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .upload-card {
      width: 300px;
    }
    .messages-container {
      flex: 1;
      overflow-y: auto;
      max-height: 60vh;
    }
    .message {
      margin: 10px 0;
      padding: 10px;
      border-radius: 8px;
      background: #f5f5f5;
    }
    .message.user {
      background: #e3f2fd;
      text-align: right;
    }
    .input-container {
      display: flex;
      gap: 10px;
      align-items: flex-end;
    }
    .full-width {
      flex: 1;
    }
    .loading {
      text-align: center;
      padding: 20px;
    }
  `]
})
export class ChatComponent {
  messages: ChatMessage[] = [];
  question = '';
  loading = false;
  uploading = false;
  selectedFiles: FileList | null = null;
  conversationId: string = '';

  constructor(private chatService: ChatService) {}

  sendMessage(): void {
    if (!this.question.trim() || this.loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: this.question,
      timestamp: Date.now()
    };
    this.messages.push(userMessage);

    const request = {
      question: this.question,
      conversation_id: this.conversationId
    };

    this.question = '';
    this.loading = true;

    this.chatService.query(request).subscribe({
      next: (response) => {
        this.conversationId = response.conversation_id || this.conversationId;
        this.messages.push({
          id: Date.now().toString(),
          role: 'assistant',
          content: response.answer,
          timestamp: Date.now()
        });
        this.loading = false;
      },
      error: (err) => {
        this.messages.push({
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Error: ' + (err.error?.message || 'Failed to get response'),
          timestamp: Date.now()
        });
        this.loading = false;
      }
    });
  }

  onFileSelected(event: any): void {
    this.selectedFiles = event.target.files;
  }

  uploadFiles(): void {
    if (!this.selectedFiles) return;

    const formData = new FormData();
    for (let i = 0; i < this.selectedFiles.length; i++) {
      formData.append('files', this.selectedFiles[i]);
    }

    this.uploading = true;
    this.chatService.ingest(formData).subscribe({
      next: () => {
        alert('Files uploaded successfully!');
        this.uploading = false;
        this.selectedFiles = null;
      },
      error: (err) => {
        alert('Upload failed: ' + (err.error?.message || 'Unknown error'));
        this.uploading = false;
      }
    });
  }
}
