/**
 * WhatsApp Authentication Service
 * 
 * Handles WhatsApp Web authentication, QR code generation,
 * session management and connection lifecycle
 */

import { Client, LocalAuth, Events } from 'whatsapp-web.js';
import * as qrcode from 'qrcode-terminal';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { Logger } from '../utils/logger';
import { ConfigManager } from '../config/config-manager';

export interface AuthenticationState {
    isAuthenticated: boolean;
    isReady: boolean;
    qrCode?: string | undefined;
    sessionId: string;
    phoneNumber?: string;
    lastActivity: Date;
    connectionState: 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'AUTHENTICATED';
}

export interface SessionInfo {
    sessionId: string;
    phoneNumber?: string | undefined;
    createdAt: Date;
    lastUsed: Date;
    isActive: boolean;
}

export class WhatsAppAuthService {
    private client: Client | null = null;
    private logger = Logger.getInstance();
    private config: ConfigManager;
    private authState: AuthenticationState;
    private sessionId: string;
    private qrCodeRetries = 0;
    private maxQrRetries = 3;
    private authTimeout: NodeJS.Timeout | null = null;

    constructor(config: ConfigManager, sessionId: string = 'default') {
        this.config = config;
        this.sessionId = sessionId;
        this.maxQrRetries = config.getWhatsAppConfig().qrRetries;
        
        this.authState = {
            isAuthenticated: false,
            isReady: false,
            sessionId: this.sessionId,
            lastActivity: new Date(),
            connectionState: 'DISCONNECTED'
        };
    }

    /**
     * Initialize WhatsApp client with authentication
     */
    async initialize(): Promise<void> {
        try {
            this.logger.info('Inicializando cliente WhatsApp', { sessionId: this.sessionId });
              const whatsappConfig = this.config.getWhatsAppConfig();
            const sessionPath = join(whatsappConfig.sessionPath, this.sessionId);
            
            // Ensure session directory exists
            this.ensureSessionDirectory(sessionPath);
            
            this.client = new Client({
                authStrategy: new LocalAuth({
                    clientId: this.sessionId,
                    dataPath: sessionPath
                }),
                puppeteer: {
                    headless: whatsappConfig.headless,
                    args: whatsappConfig.puppeteerOptions.args
                }
            });

            this.setupEventHandlers();
            await this.client.initialize();
              } catch (error: any) {
            this.logger.error('Erro ao inicializar cliente WhatsApp', { 
                error: error?.message || 'Erro desconhecido', 
                sessionId: this.sessionId 
            });
            throw error;
        }
    }

    /**
     * Setup event handlers for WhatsApp client
     */
    private setupEventHandlers(): void {
        if (!this.client) return;

        this.client.on(Events.QR_RECEIVED, (qr) => {
            this.handleQrReceived(qr);
        });

        this.client.on(Events.AUTHENTICATED, () => {
            this.handleAuthenticated();
        });

        this.client.on(Events.READY, () => {
            this.handleReady();
        });        this.client.on('auth_failure', (message: any) => {
            this.handleAuthFailure(message);
        });

        this.client.on(Events.DISCONNECTED, (reason) => {
            this.handleDisconnected(reason);
        });

        this.client.on(Events.STATE_CHANGED, (state) => {
            this.handleStateChanged(state);
        });
    }

    /**
     * Handle QR code received event
     */
    private handleQrReceived(qr: string): void {
        this.qrCodeRetries++;
        this.logger.info('QR Code recebido', { 
            sessionId: this.sessionId,
            retry: this.qrCodeRetries,
            maxRetries: this.maxQrRetries
        });

        // Display QR code in terminal
        qrcode.generate(qr, { small: true });
        
        this.authState.qrCode = qr;
        this.authState.connectionState = 'CONNECTING';

        // Set authentication timeout
        this.setAuthTimeout();

        if (this.qrCodeRetries >= this.maxQrRetries) {
            this.logger.warn('Número máximo de tentativas de QR atingido', { 
                sessionId: this.sessionId 
            });
            this.handleAuthFailure('Máximo de tentativas de QR excedido');
        }
    }

    /**
     * Handle authenticated event
     */
    private handleAuthenticated(): void {
        this.logger.info('Cliente WhatsApp autenticado com sucesso', { 
            sessionId: this.sessionId 
        });
          this.authState.isAuthenticated = true;
        this.authState.connectionState = 'AUTHENTICATED';
        delete this.authState.qrCode;
        this.qrCodeRetries = 0;
        
        this.clearAuthTimeout();
    }

    /**
     * Handle ready event
     */
    private async handleReady(): Promise<void> {
        try {
            this.logger.info('Cliente WhatsApp pronto para uso', { 
                sessionId: this.sessionId 
            });
            
            this.authState.isReady = true;
            this.authState.connectionState = 'CONNECTED';
            this.authState.lastActivity = new Date();
            
            // Get phone number
            const info = this.client?.info;
            if (info) {
                this.authState.phoneNumber = info.wid.user;
                this.logger.info('Número do telefone obtido', { 
                    sessionId: this.sessionId,
                    phoneNumber: this.authState.phoneNumber
                });
            }

            await this.saveSessionInfo();
              } catch (error: any) {
            this.logger.error('Erro ao processar evento ready', { 
                error: error?.message || 'Erro desconhecido',
                sessionId: this.sessionId 
            });
        }
    }

    /**
     * Handle authentication failure
     */
    private handleAuthFailure(message: string): void {
        this.logger.error('Falha na autenticação WhatsApp', { 
            message,
            sessionId: this.sessionId 
        });
        
        this.authState.isAuthenticated = false;
        this.authState.isReady = false;
        this.authState.connectionState = 'DISCONNECTED';
        
        this.clearAuthTimeout();
    }

    /**
     * Handle disconnection
     */
    private handleDisconnected(reason: string): void {
        this.logger.warn('Cliente WhatsApp desconectado', { 
            reason,
            sessionId: this.sessionId 
        });
        
        this.authState.isAuthenticated = false;
        this.authState.isReady = false;
        this.authState.connectionState = 'DISCONNECTED';
    }

    /**
     * Handle state changes
     */
    private handleStateChanged(state: any): void {
        this.logger.debug('Estado do cliente alterado', { 
            state,
            sessionId: this.sessionId 
        });
        
        this.authState.lastActivity = new Date();
    }

    /**
     * Set authentication timeout
     */
    private setAuthTimeout(): void {
        this.clearAuthTimeout();
        
        const timeoutMs = this.config.getWhatsAppConfig().authTimeoutMs;
        this.authTimeout = setTimeout(() => {
            this.logger.warn('Timeout de autenticação atingido', { 
                sessionId: this.sessionId 
            });
            this.handleAuthFailure('Timeout de autenticação');
        }, timeoutMs);
    }

    /**
     * Clear authentication timeout
     */
    private clearAuthTimeout(): void {
        if (this.authTimeout) {
            clearTimeout(this.authTimeout);
            this.authTimeout = null;
        }
    }

    /**
     * Ensure session directory exists
     */
    private ensureSessionDirectory(sessionPath: string): void {        if (!existsSync(sessionPath)) {
            mkdirSync(sessionPath, { recursive: true });
            this.logger.info('Diretório de sessão criado', { 
                sessionPath,
                sessionId: this.sessionId 
            });
        }
    }

    /**
     * Save session information
     */
    private async saveSessionInfo(): Promise<void> {
        try {
            const sessionInfo: SessionInfo = {
                sessionId: this.sessionId,
                phoneNumber: this.authState.phoneNumber,
                createdAt: new Date(),
                lastUsed: new Date(),
                isActive: true
            };            const whatsappConfig = this.config.getWhatsAppConfig();
            const sessionPath = join(whatsappConfig.sessionPath, this.sessionId);
            const infoPath = join(sessionPath, 'session-info.json');
            
            writeFileSync(infoPath, JSON.stringify(sessionInfo, null, 2));
            
            this.logger.info('Informações da sessão salvas', { 
                sessionId: this.sessionId,
                infoPath 
            });
              } catch (error: any) {
            this.logger.error('Erro ao salvar informações da sessão', { 
                error: error?.message || 'Erro desconhecido',
                sessionId: this.sessionId 
            });
        }
    }

    /**
     * Get current authentication state
     */
    getAuthState(): AuthenticationState {
        return { ...this.authState };
    }

    /**
     * Get session information
     */
    async getSessionInfo(): Promise<SessionInfo | null> {
        try {            const whatsappConfig = this.config.getWhatsAppConfig();
            const sessionPath = join(whatsappConfig.sessionPath, this.sessionId);
            const infoPath = join(sessionPath, 'session-info.json');
            
            if (!existsSync(infoPath)) {
                return null;
            }
            
            const data = readFileSync(infoPath, 'utf8');
            return JSON.parse(data);
              } catch (error: any) {
            this.logger.error('Erro ao obter informações da sessão', { 
                error: error?.message || 'Erro desconhecido',
                sessionId: this.sessionId 
            });
            return null;
        }
    }

    /**
     * Check if session is authenticated and ready
     */
    isReady(): boolean {
        return this.authState.isAuthenticated && this.authState.isReady;
    }

    /**
     * Get WhatsApp client instance
     */
    getClient(): Client | null {
        return this.client;
    }

    /**
     * Logout and destroy session
     */
    async logout(): Promise<void> {
        try {
            this.logger.info('Fazendo logout da sessão WhatsApp', { 
                sessionId: this.sessionId 
            });
            
            if (this.client) {
                await this.client.logout();
                await this.client.destroy();
                this.client = null;
            }
            
            this.authState.isAuthenticated = false;
            this.authState.isReady = false;
            this.authState.connectionState = 'DISCONNECTED';
            
            this.clearAuthTimeout();
              } catch (error: any) {
            this.logger.error('Erro ao fazer logout', { 
                error: error?.message || 'Erro desconhecido',
                sessionId: this.sessionId 
            });
        }
    }

    /**
     * Restart authentication process
     */
    async restart(): Promise<void> {
        await this.logout();
        this.qrCodeRetries = 0;
        await this.initialize();
    }
}
