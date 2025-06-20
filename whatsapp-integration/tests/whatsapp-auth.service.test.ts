/**
 * Tests for WhatsApp Authentication Service
 */

import { WhatsAppAuthService } from '../src/services/whatsapp-auth.service';
import { ConfigManager } from '../src/config/config-manager';
import { Logger } from '../src/utils/logger';

// Mock external dependencies
jest.mock('whatsapp-web.js');
jest.mock('qrcode-terminal');
jest.mock('fs');
jest.mock('../src/utils/logger');

const mockFs = require('fs');
const mockWhatsApp = require('whatsapp-web.js');

describe('WhatsAppAuthService', () => {
    let authService: WhatsAppAuthService;
    let configManager: ConfigManager;
    let mockClient: any;

    beforeEach(() => {
        jest.clearAllMocks();
        
        // Setup mock config
        configManager = new ConfigManager();
        jest.spyOn(configManager, 'getWhatsAppConfig').mockReturnValue({
            sessionPath: './test-sessions',
            headless: true,
            puppeteerOptions: { args: [] },
            qrRetries: 3,
            authTimeoutMs: 60000
        });

        // Setup mock client
        mockClient = {
            initialize: jest.fn(),
            on: jest.fn(),
            info: { wid: { user: '5511999999999' } },
            logout: jest.fn(),
            destroy: jest.fn()
        };

        mockWhatsApp.Client = jest.fn().mockReturnValue(mockClient);
        mockWhatsApp.LocalAuth = jest.fn();
        mockWhatsApp.Events = {
            QR_RECEIVED: 'qr',
            AUTHENTICATED: 'authenticated',
            READY: 'ready',
            DISCONNECTED: 'disconnected',
            STATE_CHANGED: 'state_changed'
        };

        // Setup filesystem mocks
        mockFs.existsSync = jest.fn().mockReturnValue(false);
        mockFs.mkdirSync = jest.fn();
        mockFs.writeFileSync = jest.fn();
        mockFs.readFileSync = jest.fn();

        authService = new WhatsAppAuthService(configManager, 'test-session');
    });

    describe('Constructor', () => {
        it('should initialize with correct default values', () => {
            expect(authService).toBeInstanceOf(WhatsAppAuthService);
            
            const authState = authService.getAuthState();
            expect(authState.sessionId).toBe('test-session');
            expect(authState.isAuthenticated).toBe(false);
            expect(authState.isReady).toBe(false);
            expect(authState.connectionState).toBe('DISCONNECTED');
        });

        it('should use default session id when not provided', () => {
            const defaultAuthService = new WhatsAppAuthService(configManager);
            const authState = defaultAuthService.getAuthState();
            expect(authState.sessionId).toBe('default');
        });
    });

    describe('initialize', () => {
        it('should initialize WhatsApp client successfully', async () => {
            mockClient.initialize.mockResolvedValue(undefined);

            await authService.initialize();

            expect(mockWhatsApp.Client).toHaveBeenCalledWith(
                expect.objectContaining({
                    authStrategy: expect.any(Object),
                    puppeteer: expect.objectContaining({
                        headless: true,
                        args: []
                    })
                })
            );
            expect(mockClient.initialize).toHaveBeenCalled();
        });

        it('should create session directory if it does not exist', async () => {
            mockFs.existsSync.mockReturnValue(false);
            mockClient.initialize.mockResolvedValue(undefined);

            await authService.initialize();

            expect(mockFs.mkdirSync).toHaveBeenCalledWith(
                expect.stringContaining('test-session'),
                { recursive: true }
            );
        });

        it('should throw error if initialization fails', async () => {
            const error = new Error('Initialization failed');
            mockClient.initialize.mockRejectedValue(error);

            await expect(authService.initialize()).rejects.toThrow('Initialization failed');
        });
    });

    describe('Event Handlers', () => {
        beforeEach(async () => {
            mockClient.initialize.mockResolvedValue(undefined);
            await authService.initialize();
        });

        it('should setup all event handlers', () => {
            expect(mockClient.on).toHaveBeenCalledWith('qr', expect.any(Function));
            expect(mockClient.on).toHaveBeenCalledWith('authenticated', expect.any(Function));
            expect(mockClient.on).toHaveBeenCalledWith('ready', expect.any(Function));
            expect(mockClient.on).toHaveBeenCalledWith('auth_failure', expect.any(Function));
            expect(mockClient.on).toHaveBeenCalledWith('disconnected', expect.any(Function));
            expect(mockClient.on).toHaveBeenCalledWith('state_changed', expect.any(Function));
        });

        it('should handle QR code received event', () => {
            const qrHandler = mockClient.on.mock.calls.find(call => call[0] === 'qr')[1];
            const testQR = 'test-qr-code';

            qrHandler(testQR);

            const authState = authService.getAuthState();
            expect(authState.qrCode).toBe(testQR);
            expect(authState.connectionState).toBe('CONNECTING');
        });

        it('should handle authenticated event', () => {
            const authHandler = mockClient.on.mock.calls.find(call => call[0] === 'authenticated')[1];

            authHandler();

            const authState = authService.getAuthState();
            expect(authState.isAuthenticated).toBe(true);
            expect(authState.connectionState).toBe('AUTHENTICATED');
            expect(authState.qrCode).toBeUndefined();
        });

        it('should handle ready event', async () => {
            const readyHandler = mockClient.on.mock.calls.find(call => call[0] === 'ready')[1];
            mockFs.writeFileSync.mockImplementation(() => {});

            await readyHandler();

            const authState = authService.getAuthState();
            expect(authState.isReady).toBe(true);
            expect(authState.connectionState).toBe('CONNECTED');
            expect(authState.phoneNumber).toBe('5511999999999');
        });

        it('should handle disconnected event', () => {
            const disconnectedHandler = mockClient.on.mock.calls.find(call => call[0] === 'disconnected')[1];

            disconnectedHandler('Connection lost');

            const authState = authService.getAuthState();
            expect(authState.isAuthenticated).toBe(false);
            expect(authState.isReady).toBe(false);
            expect(authState.connectionState).toBe('DISCONNECTED');
        });

        it('should handle auth failure event', () => {
            const authFailureHandler = mockClient.on.mock.calls.find(call => call[0] === 'auth_failure')[1];

            authFailureHandler('Authentication failed');

            const authState = authService.getAuthState();
            expect(authState.isAuthenticated).toBe(false);
            expect(authState.isReady).toBe(false);
            expect(authState.connectionState).toBe('DISCONNECTED');
        });
    });

    describe('getSessionInfo', () => {
        it('should return null if session info file does not exist', async () => {
            mockFs.existsSync.mockReturnValue(false);

            const sessionInfo = await authService.getSessionInfo();

            expect(sessionInfo).toBeNull();
        });

        it('should return session info if file exists', async () => {
            const mockSessionInfo = {
                sessionId: 'test-session',
                phoneNumber: '5511999999999',
                createdAt: new Date().toISOString(),
                lastUsed: new Date().toISOString(),
                isActive: true
            };

            mockFs.existsSync.mockReturnValue(true);
            mockFs.readFileSync.mockReturnValue(JSON.stringify(mockSessionInfo));

            const sessionInfo = await authService.getSessionInfo();

            expect(sessionInfo).toEqual(mockSessionInfo);
        });

        it('should return null if there is an error reading session info', async () => {
            mockFs.existsSync.mockReturnValue(true);
            mockFs.readFileSync.mockImplementation(() => {
                throw new Error('Read error');
            });

            const sessionInfo = await authService.getSessionInfo();

            expect(sessionInfo).toBeNull();
        });
    });

    describe('isReady', () => {
        it('should return false when not authenticated', () => {
            expect(authService.isReady()).toBe(false);
        });

        it('should return false when authenticated but not ready', () => {
            // Simulate authenticated state
            const authState = authService.getAuthState();
            authState.isAuthenticated = true;
            authState.isReady = false;

            expect(authService.isReady()).toBe(false);
        });

        it('should return true when both authenticated and ready', () => {
            // We need to access the private authState to modify it for testing
            const authState = authService.getAuthState();
            authState.isAuthenticated = true;
            authState.isReady = true;

            expect(authService.isReady()).toBe(true);
        });
    });

    describe('getClient', () => {
        it('should return null before initialization', () => {
            expect(authService.getClient()).toBeNull();
        });

        it('should return client after initialization', async () => {
            mockClient.initialize.mockResolvedValue(undefined);
            await authService.initialize();

            expect(authService.getClient()).toBe(mockClient);
        });
    });

    describe('logout', () => {
        beforeEach(async () => {
            mockClient.initialize.mockResolvedValue(undefined);
            await authService.initialize();
        });

        it('should logout and destroy client successfully', async () => {
            mockClient.logout.mockResolvedValue(undefined);
            mockClient.destroy.mockResolvedValue(undefined);

            await authService.logout();

            expect(mockClient.logout).toHaveBeenCalled();
            expect(mockClient.destroy).toHaveBeenCalled();
            expect(authService.getClient()).toBeNull();

            const authState = authService.getAuthState();
            expect(authState.isAuthenticated).toBe(false);
            expect(authState.isReady).toBe(false);
            expect(authState.connectionState).toBe('DISCONNECTED');
        });

        it('should handle logout errors gracefully', async () => {
            mockClient.logout.mockRejectedValue(new Error('Logout failed'));

            // Should not throw
            await authService.logout();

            const authState = authService.getAuthState();
            expect(authState.isAuthenticated).toBe(false);
            expect(authState.isReady).toBe(false);
            expect(authState.connectionState).toBe('DISCONNECTED');
        });
    });

    describe('restart', () => {
        beforeEach(async () => {
            mockClient.initialize.mockResolvedValue(undefined);
            await authService.initialize();
        });

        it('should restart authentication process', async () => {
            mockClient.logout.mockResolvedValue(undefined);
            mockClient.destroy.mockResolvedValue(undefined);

            await authService.restart();

            // Should logout first
            expect(mockClient.logout).toHaveBeenCalled();
            expect(mockClient.destroy).toHaveBeenCalled();

            // Should initialize again
            expect(mockClient.initialize).toHaveBeenCalledTimes(2); // Once in beforeEach, once in restart
        });
    });

    describe('QR Code Retry Logic', () => {
        beforeEach(async () => {
            mockClient.initialize.mockResolvedValue(undefined);
            await authService.initialize();
        });

        it('should handle multiple QR codes within retry limit', () => {
            const qrHandler = mockClient.on.mock.calls.find(call => call[0] === 'qr')[1];

            // First QR
            qrHandler('qr-1');
            let authState = authService.getAuthState();
            expect(authState.connectionState).toBe('CONNECTING');

            // Second QR
            qrHandler('qr-2');
            authState = authService.getAuthState();
            expect(authState.connectionState).toBe('CONNECTING');

            // Third QR (at limit)
            qrHandler('qr-3');
            authState = authService.getAuthState();
            expect(authState.connectionState).toBe('CONNECTING');
        });
    });
});
