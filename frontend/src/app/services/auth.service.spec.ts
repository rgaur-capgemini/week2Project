import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';
import { User } from '../models/models';
import { environment } from '../../environments/environment';

describe('AuthService - Comprehensive Coverage', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    });
    
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  describe('Initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should initialize with no user when localStorage is empty', () => {
      const newService = TestBed.inject(AuthService);
      expect(newService.currentUser).toBeNull();
    });

    it('should initialize with user from localStorage', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user'
      };
      
      localStorage.setItem('user', JSON.stringify(mockUser));
      const newService = new AuthService(TestBed.inject(HttpClient));
      
      expect(newService.currentUser).toEqual(mockUser);
    });

    it('should emit user from currentUser$ observable', (done) => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user'
      };
      
      localStorage.setItem('user', JSON.stringify(mockUser));
      const newService = new AuthService(TestBed.inject(HttpClient));
      
      newService.currentUser$.subscribe(user => {
        expect(user).toEqual(mockUser);
        done();
      });
    });
  });

  describe('isAuthenticated', () => {
    it('should return false when no user is logged in', () => {
      expect(service.isAuthenticated).toBeFalse();
    });

    it('should return true when user is logged in', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user'
      };
      
      (service as any).currentUserSubject.next(mockUser);
      expect(service.isAuthenticated).toBeTrue();
    });
  });

  describe('isAdmin', () => {
    it('should return false when no user is logged in', () => {
      expect(service.isAdmin).toBeFalse();
    });

    it('should return false when user is not admin', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'user@example.com',
        name: 'Regular User',
        role: 'user'
      };
      
      (service as any).currentUserSubject.next(mockUser);
      expect(service.isAdmin).toBeFalse();
    });

    it('should return true when user is admin', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'admin@example.com',
        name: 'Admin User',
        role: 'admin'
      };
      
      (service as any).currentUserSubject.next(mockUser);
      expect(service.isAdmin).toBeTrue();
    });
  });

  describe('loginWithGoogle', () => {
    it('should login successfully with Google token', (done) => {
      const mockResponse = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        picture: 'https://example.com/picture.jpg',
        role: 'user',
        access_token: 'test-token-123'
      };

      service.loginWithGoogle('google-id-token').subscribe(response => {
        expect(response).toEqual(mockResponse);
        
        // Verify user in localStorage
        const storedUser = localStorage.getItem('user');
        expect(storedUser).toBeTruthy();
        
        const user = JSON.parse(storedUser!);
        expect(user.email).toBe('test@example.com');
        expect(user.user_id).toBe('123');
        
        // Verify token in localStorage
        expect(localStorage.getItem('token')).toBe('test-token-123');
        
        // Verify current user updated
        expect(service.currentUser?.email).toBe('test@example.com');
        
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ token: 'google-id-token' });
      req.flush(mockResponse);
    });

    it('should handle Google login error', (done) => {
      service.loginWithGoogle('invalid-token').subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(401);
          expect(localStorage.getItem('user')).toBeNull();
          expect(localStorage.getItem('token')).toBeNull();
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush({ message: 'Invalid token' }, { status: 401, statusText: 'Unauthorized' });
    });

    it('should update currentUser$ observable on Google login', (done) => {
      const mockResponse = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        picture: 'https://example.com/picture.jpg',
        role: 'user',
        access_token: 'test-token'
      };

      let emissionCount = 0;
      service.currentUser$.subscribe(user => {
        emissionCount++;
        if (emissionCount === 2) { // Skip initial null emission
          expect(user?.email).toBe('test@example.com');
          done();
        }
      });

      service.loginWithGoogle('google-token').subscribe();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush(mockResponse);
    });
  });

  describe('login', () => {
    it('should login successfully with email and password', (done) => {
      const mockResponse = {
        user_id: '456',
        email: 'user@example.com',
        name: 'Email User',
        role: 'user',
        access_token: 'email-token-456'
      };

      service.login('user@example.com', 'password123').subscribe(response => {
        expect(response).toEqual(mockResponse);
        
        // Verify user in localStorage
        const storedUser = JSON.parse(localStorage.getItem('user')!);
        expect(storedUser.email).toBe('user@example.com');
        expect(storedUser.user_id).toBe('456');
        
        // Verify token
        expect(localStorage.getItem('token')).toBe('email-token-456');
        
        // Verify current user
        expect(service.currentUser?.email).toBe('user@example.com');
        
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'user@example.com', password: 'password123' });
      req.flush(mockResponse);
    });

    it('should handle login error with wrong credentials', (done) => {
      service.login('user@example.com', 'wrongpassword').subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(401);
          expect(localStorage.getItem('user')).toBeNull();
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush({ message: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });
    });

    it('should handle server error during login', (done) => {
      service.login('user@example.com', 'password').subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(500);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush({ message: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });
    });

    it('should not store user without picture field', (done) => {
      const mockResponse = {
        user_id: '789',
        email: 'nopic@example.com',
        name: 'No Picture User',
        role: 'user',
        access_token: 'token-789'
      };

      service.login('nopic@example.com', 'password').subscribe(() => {
        const storedUser = JSON.parse(localStorage.getItem('user')!);
        expect(storedUser.picture).toBeUndefined();
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush(mockResponse);
    });
  });

  describe('logout', () => {
    it('should clear user from localStorage', () => {
      localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
      localStorage.setItem('token', 'test-token');

      service.logout();

      expect(localStorage.getItem('user')).toBeNull();
      expect(localStorage.getItem('token')).toBeNull();
    });

    it('should clear currentUser', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user'
      };
      
      (service as any).currentUserSubject.next(mockUser);
      expect(service.currentUser).toBeTruthy();

      service.logout();

      expect(service.currentUser).toBeNull();
    });

    it('should emit null from currentUser$ after logout', (done) => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user'
      };
      
      (service as any).currentUserSubject.next(mockUser);

      let emissionCount = 0;
      service.currentUser$.subscribe(user => {
        emissionCount++;
        if (emissionCount === 2) { // After logout
          expect(user).toBeNull();
          done();
        }
      });

      service.logout();
    });

    it('should handle logout when no user is logged in', () => {
      expect(() => service.logout()).not.toThrow();
      expect(service.currentUser).toBeNull();
    });

    it('should update isAuthenticated to false after logout', () => {
      const mockUser: User = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin'
      };
      
      (service as any).currentUserSubject.next(mockUser);
      expect(service.isAuthenticated).toBeTrue();
      expect(service.isAdmin).toBeTrue();

      service.logout();

      expect(service.isAuthenticated).toBeFalse();
      expect(service.isAdmin).toBeFalse();
    });
  });

  describe('getToken', () => {
    it('should return token from localStorage', () => {
      localStorage.setItem('token', 'my-test-token');
      expect(service.getToken()).toBe('my-test-token');
    });

    it('should return null when no token exists', () => {
      expect(service.getToken()).toBeNull();
    });

    it('should return updated token after login', (done) => {
      const mockResponse = {
        user_id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
        access_token: 'new-token-123'
      };

      service.login('test@example.com', 'password').subscribe(() => {
        expect(service.getToken()).toBe('new-token-123');
        done();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush(mockResponse);
    });

    it('should return null after logout', () => {
      localStorage.setItem('token', 'test-token');
      service.logout();
      expect(service.getToken()).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('should handle corrupted user data in localStorage', () => {
      localStorage.setItem('user', 'invalid-json{');
      
      expect(() => {
        new AuthService(TestBed.inject(HttpClient));
      }).toThrow();
    });

    it('should handle empty string email in login', (done) => {
      service.login('', '').subscribe(
        () => fail('should have failed'),
        error => {
          expect(error.status).toBe(400);
          done();
        }
      );

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush({ message: 'Invalid credentials' }, { status: 400, statusText: 'Bad Request' });
    });

    it('should handle multiple rapid logins', (done) => {
      const mockResponse1 = {
        user_id: '1',
        email: 'user1@example.com',
        name: 'User 1',
        role: 'user',
        access_token: 'token1'
      };

      const mockResponse2 = {
        user_id: '2',
        email: 'user2@example.com',
        name: 'User 2',
        role: 'admin',
        access_token: 'token2'
      };

      service.login('user1@example.com', 'pass1').subscribe();
      service.login('user2@example.com', 'pass2').subscribe(() => {
        expect(service.currentUser?.email).toBe('user2@example.com');
        expect(service.isAdmin).toBeTrue();
        done();
      });

      const requests = httpMock.match(`${environment.apiUrl}/auth/login`);
      expect(requests.length).toBe(2);
      requests[0].flush(mockResponse1);
      requests[1].flush(mockResponse2);
    });
  });
});
