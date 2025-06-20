/**
 * WhatsApp Session Manager
 * 
 * Manages multiple WhatsApp sessions, handles session lifecycle,
 * and provides session discovery and management capabilities
 */

import { WhatsAppAuthService, AuthenticationState, SessionInfo } from './whatsapp-auth.service';
import { ConfigManager } from '../config/config-manager';
import { Logger } from '../utils/logger';
import { existsSync, readdirSync } from 'fs';

export interface SessionManagerStats {
    totalSessions: number;
    activeSessions: number;
    connectedSessions: number;
    authenticatedSessions: number;
}

export class WhatsAppSessionManager {
    private sessions: Map<string, WhatsAppAuthService> = new Map();
    private logger = Logger.getInstance();
    private config: ConfigManager;

    constructor(config: ConfigManager) {
        this.config = config;
    }

    /**
     * Initialize session manager
     */
    async initialize(): Promise<void> {
        this.logger.info('Inicializando gerenciador de sessões WhatsApp');
        
        try {
            await this.discoverExistingSessions();
            this.logger.info('Gerenciador de sessões inicializado com sucesso', {
                totalSessions: this.sessions.size
            });
        } catch (error: any) {
            this.logger.error('Erro ao inicializar gerenciador de sessões', {
                error: error?.message || 'Erro desconhecido'
            });
            throw error;
        }
    }

    /**
     * Discover existing sessions from filesystem
     */
    private async discoverExistingSessions(): Promise<void> {
        const whatsappConfig = this.config.getWhatsAppConfig();
        const sessionsPath = whatsappConfig.sessionPath;

        if (!existsSync(sessionsPath)) {
            this.logger.info('Diretório de sessões não existe, será criado quando necessário', {
                sessionsPath
            });
            return;
        }

        try {
            const sessionDirs = readdirSync(sessionsPath, { withFileTypes: true })
                .filter(dirent => dirent.isDirectory())
                .map(dirent => dirent.name);

            this.logger.info('Sessões descobertas no filesystem', {
                sessionCount: sessionDirs.length,
                sessions: sessionDirs
            });

            for (const sessionId of sessionDirs) {
                await this.loadSession(sessionId);
            }
        } catch (error: any) {
            this.logger.error('Erro ao descobrir sessões existentes', {
                error: error?.message || 'Erro desconhecido',
                sessionsPath
            });
        }
    }

    /**
     * Load a session without initializing the connection
     */
    private async loadSession(sessionId: string): Promise<void> {
        if (this.sessions.has(sessionId)) {
            this.logger.warn('Sessão já carregada', { sessionId });
            return;
        }

        try {
            const authService = new WhatsAppAuthService(this.config, sessionId);
            this.sessions.set(sessionId, authService);

            this.logger.info('Sessão carregada', { sessionId });
        } catch (error: any) {
            this.logger.error('Erro ao carregar sessão', {
                error: error?.message || 'Erro desconhecido',
                sessionId
            });
        }
    }

    /**
     * Create a new session
     */
    async createSession(sessionId?: string): Promise<string> {
        // Generate session ID if not provided
        if (!sessionId) {
            sessionId = this.generateSessionId();
        }

        if (this.sessions.has(sessionId)) {
            throw new Error(`Sessão com ID '${sessionId}' já existe`);
        }

        this.logger.info('Criando nova sessão', { sessionId });

        try {
            const authService = new WhatsAppAuthService(this.config, sessionId);
            this.sessions.set(sessionId, authService);

            this.logger.info('Nova sessão criada', { sessionId });
            return sessionId;
        } catch (error: any) {
            this.logger.error('Erro ao criar nova sessão', {
                error: error?.message || 'Erro desconhecido',
                sessionId
            });
            throw error;
        }
    }

    /**
     * Initialize a session connection
     */
    async initializeSession(sessionId: string): Promise<void> {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            throw new Error(`Sessão '${sessionId}' não encontrada`);
        }

        this.logger.info('Inicializando sessão', { sessionId });

        try {
            await authService.initialize();
            this.logger.info('Sessão inicializada com sucesso', { sessionId });
        } catch (error: any) {
            this.logger.error('Erro ao inicializar sessão', {
                error: error?.message || 'Erro desconhecido',
                sessionId
            });
            throw error;
        }
    }

    /**
     * Get session authentication state
     */
    getSessionState(sessionId: string): AuthenticationState | null {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            return null;
        }

        return authService.getAuthState();
    }

    /**
     * Get session info
     */
    async getSessionInfo(sessionId: string): Promise<SessionInfo | null> {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            return null;
        }

        return await authService.getSessionInfo();
    }

    /**
     * Get WhatsApp client for session
     */
    getSessionClient(sessionId: string) {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            return null;
        }

        return authService.getClient();
    }

    /**
     * Check if session is ready
     */
    isSessionReady(sessionId: string): boolean {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            return false;
        }

        return authService.isReady();
    }

    /**
     * List all sessions with their states
     */
    async listSessions(): Promise<Array<{sessionId: string, state: AuthenticationState, info: SessionInfo | null}>> {
        const sessions = [];

        for (const [sessionId, authService] of this.sessions) {
            const state = authService.getAuthState();
            const info = await authService.getSessionInfo();
            
            sessions.push({
                sessionId,
                state,
                info
            });
        }

        return sessions;
    }

    /**
     * Get ready sessions (authenticated and connected)
     */
    getReadySessions(): string[] {
        const readySessions = [];
        
        for (const [sessionId, authService] of this.sessions) {
            if (authService.isReady()) {
                readySessions.push(sessionId);
            }
        }

        return readySessions;
    }

    /**
     * Logout and destroy session
     */
    async destroySession(sessionId: string): Promise<void> {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            throw new Error(`Sessão '${sessionId}' não encontrada`);
        }

        this.logger.info('Destruindo sessão', { sessionId });

        try {
            await authService.logout();
            this.sessions.delete(sessionId);
            
            this.logger.info('Sessão destruída com sucesso', { sessionId });
        } catch (error: any) {
            this.logger.error('Erro ao destruir sessão', {
                error: error?.message || 'Erro desconhecido',
                sessionId
            });
            throw error;
        }
    }

    /**
     * Restart session
     */
    async restartSession(sessionId: string): Promise<void> {
        const authService = this.sessions.get(sessionId);
        if (!authService) {
            throw new Error(`Sessão '${sessionId}' não encontrada`);
        }

        this.logger.info('Reiniciando sessão', { sessionId });

        try {
            await authService.restart();
            this.logger.info('Sessão reiniciada com sucesso', { sessionId });
        } catch (error: any) {
            this.logger.error('Erro ao reiniciar sessão', {
                error: error?.message || 'Erro desconhecido',
                sessionId
            });
            throw error;
        }
    }

    /**
     * Get session manager statistics
     */
    getStats(): SessionManagerStats {
        let activeSessions = 0;
        let connectedSessions = 0;
        let authenticatedSessions = 0;

        for (const [, authService] of this.sessions) {
            const state = authService.getAuthState();
            
            if (state.connectionState !== 'DISCONNECTED') {
                activeSessions++;
            }
            
            if (state.connectionState === 'CONNECTED') {
                connectedSessions++;
            }
            
            if (state.isAuthenticated) {
                authenticatedSessions++;
            }
        }

        return {
            totalSessions: this.sessions.size,
            activeSessions,
            connectedSessions,
            authenticatedSessions
        };
    }

    /**
     * Generate unique session ID
     */
    private generateSessionId(): string {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 8);
        return `session_${timestamp}_${random}`;
    }

    /**
     * Shutdown all sessions
     */
    async shutdown(): Promise<void> {
        this.logger.info('Encerrando todas as sessões', {
            sessionCount: this.sessions.size
        });

        const shutdownPromises = Array.from(this.sessions.keys()).map(sessionId => 
            this.destroySession(sessionId).catch(error => {
                this.logger.error('Erro ao encerrar sessão durante shutdown', {
                    error: error?.message || 'Erro desconhecido',
                    sessionId
                });
            })
        );

        await Promise.all(shutdownPromises);
        
        this.logger.info('Todas as sessões foram encerradas');
    }

    /**
     * Health check for all sessions
     */
    async healthCheck(): Promise<{
        healthy: boolean;
        issues: string[];
        stats: SessionManagerStats;
    }> {
        const issues: string[] = [];
        const stats = this.getStats();

        // Check if there are any authentication failures
        for (const [sessionId, authService] of this.sessions) {
            const state = authService.getAuthState();
            
            // Check for sessions that should be connected but aren't
            if (state.isAuthenticated && !state.isReady) {
                issues.push(`Sessão ${sessionId} está autenticada mas não pronta`);
            }
            
            // Check for very old inactive sessions
            const lastActivity = new Date(state.lastActivity);
            const hoursSinceActivity = (Date.now() - lastActivity.getTime()) / (1000 * 60 * 60);
            
            if (hoursSinceActivity > 24 && state.connectionState !== 'DISCONNECTED') {
                issues.push(`Sessão ${sessionId} sem atividade há ${Math.round(hoursSinceActivity)} horas`);
            }
        }

        return {
            healthy: issues.length === 0,
            issues,
            stats
        };
    }

    /**
     * Get session count
     */
    getSessionCount(): number {
        return this.sessions.size;
    }

    /**
     * Check if session exists
     */
    hasSession(sessionId: string): boolean {
        return this.sessions.has(sessionId);
    }
}
