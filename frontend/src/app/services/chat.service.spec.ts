import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ChatService } from './chat.service';
import { QueryRequest, QueryResponse } from '../models/models';
import { environment } from '../../environments/environment';

describe('ChatService - Comprehensive Coverage', () => {
  let service: ChatService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ChatService]
    });
    
    service = TestBed.inject(ChatService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });
  });

  describe('query', () => {
    it('should send query request successfully', (done) => {
      const mockRequest: QueryRequest = {
        question: 'What is RAG?',
        session_id: 'session-123'
      };

      const mockResponse: QueryResponse = {
        response: 'RAG stands for Retrieval-Augmented Generation...',
        session_id: 'session-123',
        sources: [
          { source: 'doc1.pdf', page: 1, relevance_score: 0.95 }
        ]
      };

      service.query(mockRequest).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(response.response).toContain('RAG');
        expect(response.session_id).toBe('session-123');
        expect(response.sources?.length).toBe(1);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(mockRequest);
      req.flush(mockResponse);
    });

    it('should send query without session_id', (done) => {
      const mockRequest: QueryRequest = {
        question: 'Tell me about machine learning'
      };

      const mockResponse: QueryResponse = {
        response: 'Machine learning is...',
        session_id: 'new-session-456'
      };

      service.query(mockRequest).subscribe(response => {
        expect(response.session_id).toBe('new-session-456');
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      expect(req.request.body.session_id).toBeUndefined();
      req.flush(mockResponse);
    });

    it('should handle query with context', (done) => {
      const mockRequest: QueryRequest = {
        question: 'What did I just ask?',
        session_id: 'session-123',
        use_history: true
      };

      const mockResponse: QueryResponse = {
        response: 'You asked about RAG...',
        session_id: 'session-123'
      };

      service.query(mockRequest).subscribe(response => {
        expect(response).toEqual(mockResponse);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      expect(req.request.body.use_history).toBeTrue();
      req.flush(mockResponse);
    });

    it('should handle query with sources', (done) => {
      const mockResponse: QueryResponse = {
        response: 'Based on the documents...',
        session_id: 'session-789',
        sources: [
          { source: 'doc1.pdf', page: 1, relevance_score: 0.95 },
          { source: 'doc2.pdf', page: 3, relevance_score: 0.87 },
          { source: 'doc3.pdf', page: 5, relevance_score: 0.82 }
        ]
      };

      service.query({ question: 'Test query' }).subscribe(response => {
        expect(response.sources).toBeDefined();
        expect(response.sources?.length).toBe(3);
        expect(response.sources![0].relevance_score).toBeGreaterThan(response.sources![1].relevance_score);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush(mockResponse);
    });

    it('should handle empty response', (done) => {
      const mockResponse: QueryResponse = {
        response: '',
        session_id: 'session-empty'
      };

      service.query({ question: 'Test' }).subscribe(response => {
        expect(response.response).toBe('');
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush(mockResponse);
    });

    it('should handle API error', (done) => {
      service.query({ question: 'Test' }).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(500);
          expect(error.error.message).toBe('Internal server error');
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush({ message: 'Internal server error' }, { status: 500, statusText: 'Server Error' });
    });

    it('should handle timeout error', (done) => {
      service.query({ question: 'Long query' }).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(504);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush({ message: 'Gateway timeout' }, { status: 504, statusText: 'Gateway Timeout' });
    });

    it('should handle unauthorized error', (done) => {
      service.query({ question: 'Test' }).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(401);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush({ message: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    });

    it('should handle very long question', (done) => {
      const longQuestion = 'A'.repeat(10000);
      const mockResponse: QueryResponse = {
        response: 'Response to long question',
        session_id: 'session-long'
      };

      service.query({ question: longQuestion }).subscribe(response => {
        expect(response).toEqual(mockResponse);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      expect(req.request.body.question.length).toBe(10000);
      req.flush(mockResponse);
    });

    it('should handle special characters in question', (done) => {
      const specialQuestion = 'What is "RAG" & <ML>?';
      const mockResponse: QueryResponse = {
        response: 'Answer with special chars',
        session_id: 'session-special'
      };

      service.query({ question: specialQuestion }).subscribe(response => {
        expect(response).toEqual(mockResponse);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      expect(req.request.body.question).toBe(specialQuestion);
      req.flush(mockResponse);
    });
  });

  describe('ingest', () => {
    it('should ingest document successfully', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['test content']), 'test.pdf');

      const mockResponse = {
        message: 'Document ingested successfully',
        doc_id: 'doc-123',
        chunks_created: 10
      };

      service.ingest(formData).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(response.doc_id).toBe('doc-123');
        expect(response.chunks_created).toBe(10);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(formData);
      req.flush(mockResponse);
    });

    it('should ingest multiple files', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['content1']), 'doc1.pdf');
      formData.append('file', new Blob(['content2']), 'doc2.pdf');

      const mockResponse = {
        message: 'Documents ingested',
        docs_processed: 2
      };

      service.ingest(formData).subscribe(response => {
        expect(response.docs_processed).toBe(2);
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush(mockResponse);
    });

    it('should handle ingest error - invalid file type', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['content']), 'test.exe');

      service.ingest(formData).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(400);
          expect(error.error.message).toBe('Invalid file type');
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush({ message: 'Invalid file type' }, { status: 400, statusText: 'Bad Request' });
    });

    it('should handle ingest error - file too large', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['x'.repeat(100000000)]), 'large.pdf');

      service.ingest(formData).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(413);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush({ message: 'File too large' }, { status: 413, statusText: 'Payload Too Large' });
    });

    it('should handle ingest server error', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['content']), 'test.pdf');

      service.ingest(formData).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(500);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush({ message: 'Processing failed' }, { status: 500, statusText: 'Server Error' });
    });

    it('should handle empty form data', (done) => {
      const formData = new FormData();

      service.ingest(formData).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(400);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush({ message: 'No file provided' }, { status: 400, statusText: 'Bad Request' });
    });

    it('should include metadata in ingest', (done) => {
      const formData = new FormData();
      formData.append('file', new Blob(['content']), 'test.pdf');
      formData.append('metadata', JSON.stringify({ author: 'Test Author', category: 'Technical' }));

      const mockResponse = {
        message: 'Document ingested with metadata',
        doc_id: 'doc-456'
      };

      service.ingest(formData).subscribe(response => {
        expect(response.doc_id).toBe('doc-456');
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/ingest`);
      req.flush(mockResponse);
    });
  });

  describe('Edge Cases', () => {
    it('should handle concurrent queries', (done) => {
      const mockResponse1: QueryResponse = {
        response: 'Response 1',
        session_id: 'session-1'
      };

      const mockResponse2: QueryResponse = {
        response: 'Response 2',
        session_id: 'session-2'
      };

      let completed = 0;

      service.query({ question: 'Query 1' }).subscribe(response => {
        expect(response.response).toBe('Response 1');
        completed++;
        if (completed === 2) done();
      });

      service.query({ question: 'Query 2' }).subscribe(response => {
        expect(response.response).toBe('Response 2');
        completed++;
        if (completed === 2) done();
      });

      const requests = httpMock.match(`${environment.apiUrl}/query`);
      expect(requests.length).toBe(2);
      requests[0].flush(mockResponse1);
      requests[1].flush(mockResponse2);
    });

    it('should handle network error', (done) => {
      service.query({ question: 'Test' }).subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.error).toBeTruthy();
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.error(new ErrorEvent('Network error'));
    });

    it('should handle null response', (done) => {
      service.query({ question: 'Test' }).subscribe(response => {
        expect(response).toBeNull();
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/query`);
      req.flush(null);
    });
  });
});
