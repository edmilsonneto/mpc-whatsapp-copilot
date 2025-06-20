/**
 * WhatsApp Integration Main Entry Point
 * 
 * Main application entry point that initializes and manages
 * WhatsApp integration services, sessions, and HTTP server
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { ConfigManager } from './config/config-manager';
import { Logger } from './utils/logger';
import { WhatsAppSessionManager } from './services/session-manager.service';

class WhatsAppIntegrationApp {
    private app: express.Application;
    private logger = Logger.getInstance();
    private config: ConfigManager;
    private sessionManager: WhatsAppSessionManager;
    private server: any;

    constructor() {
        this.config = new ConfigManager();
        this.sessionManager = new WhatsAppSessionManager(this.config);
        this.app = express();
        this.setupMiddleware();
        this.setupRoutes();
    }

    /**
     * Setup Express middleware
     */
    private setupMiddleware(): void {
        // Security middleware
        this.app.use(helmet());
        this.app.use(cors());

        // Body parsing middleware
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true }));        // Request logging
        this.app.use((req, _res, next) => {
            this.logger.info('HTTP Request', {
                method: req.method,
                url: req.url,
                userAgent: req.get('User-Agent'),
                ip: req.ip
            });
            next();
        });
    }

    /**
     * Setup API routes
     */
    private setupRoutes(): void {        // Health check endpoint
        this.app.get('/health', async (_req, res) => {
            try {
                const healthCheck = await this.sessionManager.healthCheck();
                const stats = this.sessionManager.getStats();
                
                res.json({
                    status: 'ok',
                    timestamp: new Date().toISOString(),
                    uptime: process.uptime(),
                    sessionManager: healthCheck,
                    stats
                });
            } catch (error: any) {
                this.logger.error('Health check failed', { error: error?.message });
                res.status(500).json({
                    status: 'error',
                    error: error?.message || 'Health check failed'
                });
            }
        });

        // Session management endpoints
        this.app.get('/sessions', async (_req, res) => {
            try {
                const sessions = await this.sessionManager.listSessions();
                res.json({ sessions });
            } catch (error: any) {
                this.logger.error('Failed to list sessions', { error: error?.message });
                res.status(500).json({ error: error?.message || 'Failed to list sessions' });
            }
        });

        this.app.post('/sessions', async (req, res) => {
            try {
                const { sessionId } = req.body;
                const newSessionId = await this.sessionManager.createSession(sessionId);
                res.status(201).json({ sessionId: newSessionId });
            } catch (error: any) {
                this.logger.error('Failed to create session', { error: error?.message });
                res.status(400).json({ error: error?.message || 'Failed to create session' });
            }
        });

        this.app.post('/sessions/:sessionId/initialize', async (req, res) => {
            try {
                const { sessionId } = req.params;
                await this.sessionManager.initializeSession(sessionId);
                res.json({ message: 'Session initialization started' });
            } catch (error: any) {
                this.logger.error('Failed to initialize session', { 
                    error: error?.message,
                    sessionId: req.params.sessionId 
                });
                res.status(400).json({ error: error?.message || 'Failed to initialize session' });
            }
        });        this.app.get('/sessions/:sessionId', async (req, res) => {
            try {
                const { sessionId } = req.params;
                const state = this.sessionManager.getSessionState(sessionId);
                const info = await this.sessionManager.getSessionInfo(sessionId);
                
                if (!state) {
                    res.status(404).json({ error: 'Session not found' });
                    return;
                }
                
                res.json({ sessionId, state, info });
            } catch (error: any) {
                this.logger.error('Failed to get session', { 
                    error: error?.message,
                    sessionId: req.params.sessionId 
                });
                res.status(500).json({ error: error?.message || 'Failed to get session' });
            }
        });

        this.app.post('/sessions/:sessionId/restart', async (req, res) => {
            try {
                const { sessionId } = req.params;
                await this.sessionManager.restartSession(sessionId);
                res.json({ message: 'Session restart initiated' });
            } catch (error: any) {
                this.logger.error('Failed to restart session', { 
                    error: error?.message,
                    sessionId: req.params.sessionId 
                });
                res.status(400).json({ error: error?.message || 'Failed to restart session' });
            }
        });

        this.app.delete('/sessions/:sessionId', async (req, res) => {
            try {
                const { sessionId } = req.params;
                await this.sessionManager.destroySession(sessionId);
                res.json({ message: 'Session destroyed' });
            } catch (error: any) {
                this.logger.error('Failed to destroy session', { 
                    error: error?.message,
                    sessionId: req.params.sessionId 
                });
                res.status(400).json({ error: error?.message || 'Failed to destroy session' });
            }
        });

        // Statistics endpoint
        this.app.get('/stats', (_req, res) => {
            try {
                const stats = this.sessionManager.getStats();
                res.json(stats);
            } catch (error: any) {
                this.logger.error('Failed to get stats', { error: error?.message });
                res.status(500).json({ error: error?.message || 'Failed to get stats' });
            }
        });

        // 404 handler
        this.app.use('*', (_req, res) => {
            res.status(404).json({ error: 'Endpoint not found' });
        });        // Global error handler
        this.app.use((err: any, req: express.Request, res: express.Response, _next: express.NextFunction) => {
            this.logger.error('Unhandled error in Express app', {
                error: err?.message || 'Unknown error',
                stack: err?.stack,
                url: req.url,
                method: req.method
            });            res.status(500).json({
                error: 'Internal server error',
                message: process.env['NODE_ENV'] === 'development' ? err?.message : 'An error occurred'
            });
        });
    }

    /**
     * Initialize the application
     */
    async initialize(): Promise<void> {
        try {
            this.logger.info('Inicializando aplicação WhatsApp Integration');

            // Validate configuration
            await this.config.validate();
            this.logger.info('Configuração validada com sucesso');

            // Initialize session manager
            await this.sessionManager.initialize();
            this.logger.info('Session manager inicializado com sucesso');

            this.logger.info('Aplicação inicializada com sucesso');

        } catch (error: any) {
            this.logger.error('Erro ao inicializar aplicação', {
                error: error?.message || 'Erro desconhecido'
            });
            throw error;
        }
    }

    /**
     * Start the HTTP server
     */
    async start(): Promise<void> {
        try {
            const serverConfig = this.config.getServerConfig();
            
            this.server = this.app.listen(serverConfig.port, serverConfig.host, () => {
                this.logger.info('Servidor HTTP iniciado', {
                    host: serverConfig.host,
                    port: serverConfig.port,
                    url: `http://${serverConfig.host}:${serverConfig.port}`
                });
            });

            // Handle server errors
            this.server.on('error', (error: any) => {
                this.logger.error('Erro no servidor HTTP', {
                    error: error?.message || 'Erro desconhecido'
                });
            });

        } catch (error: any) {
            this.logger.error('Erro ao iniciar servidor', {
                error: error?.message || 'Erro desconhecido'
            });
            throw error;
        }
    }

    /**
     * Stop the application gracefully
     */
    async stop(): Promise<void> {
        this.logger.info('Parando aplicação WhatsApp Integration...');

        try {
            // Close HTTP server
            if (this.server) {
                await new Promise<void>((resolve) => {
                    this.server.close(() => {
                        this.logger.info('Servidor HTTP encerrado');
                        resolve();
                    });
                });
            }

            // Shutdown session manager
            await this.sessionManager.shutdown();

            this.logger.info('Aplicação encerrada com sucesso');

        } catch (error: any) {
            this.logger.error('Erro ao encerrar aplicação', {
                error: error?.message || 'Erro desconhecido'
            });
        }
    }

    /**
     * Get session manager instance
     */
    getSessionManager(): WhatsAppSessionManager {
        return this.sessionManager;
    }

    /**
     * Get Express app instance
     */
    getApp(): express.Application {
        return this.app;
    }
}

// Main execution
async function main() {
    const app = new WhatsAppIntegrationApp();

    // Handle graceful shutdown
    const gracefulShutdown = async (signal: string) => {
        console.log(`\nRecebido sinal ${signal}. Encerrando aplicação...`);
        try {
            await app.stop();
            process.exit(0);
        } catch (error) {
            console.error('Erro durante encerramento:', error);
            process.exit(1);
        }
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
        console.error('Uncaught Exception:', error);
        gracefulShutdown('uncaughtException');
    });

    process.on('unhandledRejection', (reason, promise) => {
        console.error('Unhandled Rejection at:', promise, 'reason:', reason);
        gracefulShutdown('unhandledRejection');
    });

    try {
        await app.initialize();
        await app.start();
    } catch (error) {
        console.error('Erro ao iniciar aplicação:', error);
        process.exit(1);
    }
}

// Run the application if this file is executed directly
if (require.main === module) {
    main();
}

export default WhatsAppIntegrationApp;
