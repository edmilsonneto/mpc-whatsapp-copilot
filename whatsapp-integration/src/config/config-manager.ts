/**
 * Configuration Manager
 * 
 * Manages all configuration for the WhatsApp integration service
 */

import * as dotenv from 'dotenv';
import Joi from 'joi';

// Load environment variables
dotenv.config();

export interface WhatsAppConfig {
    sessionPath: string;
    headless: boolean;
    puppeteerOptions: any;
    qrRetries: number;
    authTimeoutMs: number;
}

export interface MCPConfig {
    serverUrl: string;
    timeout: number;
    retries: number;
    retryDelay: number;
}

export interface CommandConfig {
    prefix: string;
    rateLimitWindowMs: number;
    rateLimitMaxRequests: number;
    allowedUsers: string[];
    adminUsers: string[];
}

export interface ServerConfig {
    port: number;
    host: string;
    enableMetrics: boolean;
    enableHealthCheck: boolean;
}

export class ConfigManager {
    private config: {
        whatsapp: WhatsAppConfig;
        mcp: MCPConfig;
        commands: CommandConfig;
        server: ServerConfig;
    };

    constructor() {
        this.config = this.loadConfig();
    }

    /**
     * Load configuration from environment variables
     */
    private loadConfig() {
        return {
            whatsapp: {
                sessionPath: process.env.WHATSAPP_SESSION_PATH || './sessions',
                headless: process.env.WHATSAPP_HEADLESS !== 'false',
                puppeteerOptions: {
                    args: [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu'
                    ]
                },
                qrRetries: parseInt(process.env.WHATSAPP_QR_RETRIES || '3'),
                authTimeoutMs: parseInt(process.env.WHATSAPP_AUTH_TIMEOUT || '60000')
            },
            mcp: {
                serverUrl: process.env.MCP_SERVER_URL || 'http://localhost:8000',
                timeout: parseInt(process.env.MCP_TIMEOUT || '30000'),
                retries: parseInt(process.env.MCP_RETRIES || '3'),
                retryDelay: parseInt(process.env.MCP_RETRY_DELAY || '1000')
            },
            commands: {
                prefix: process.env.COMMAND_PREFIX || '/',
                rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000'),
                rateLimitMaxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '10'),
                allowedUsers: process.env.ALLOWED_USERS?.split(',') || [],
                adminUsers: process.env.ADMIN_USERS?.split(',') || []
            },
            server: {
                port: parseInt(process.env.PORT || '3001'),
                host: process.env.HOST || '0.0.0.0',
                enableMetrics: process.env.ENABLE_METRICS !== 'false',
                enableHealthCheck: process.env.ENABLE_HEALTH_CHECK !== 'false'
            }
        };
    }

    /**
     * Validate configuration
     */
    async validate(): Promise<void> {
        const schema = Joi.object({
            whatsapp: Joi.object({
                sessionPath: Joi.string().required(),
                headless: Joi.boolean().required(),
                puppeteerOptions: Joi.object().required(),
                qrRetries: Joi.number().min(1).max(10).required(),
                authTimeoutMs: Joi.number().min(10000).required()
            }).required(),
            mcp: Joi.object({
                serverUrl: Joi.string().uri().required(),
                timeout: Joi.number().min(1000).required(),
                retries: Joi.number().min(1).max(10).required(),
                retryDelay: Joi.number().min(100).required()
            }).required(),
            commands: Joi.object({
                prefix: Joi.string().min(1).required(),
                rateLimitWindowMs: Joi.number().min(1000).required(),
                rateLimitMaxRequests: Joi.number().min(1).required(),
                allowedUsers: Joi.array().items(Joi.string()).required(),
                adminUsers: Joi.array().items(Joi.string()).required()
            }).required(),
            server: Joi.object({
                port: Joi.number().min(1024).max(65535).required(),
                host: Joi.string().required(),
                enableMetrics: Joi.boolean().required(),
                enableHealthCheck: Joi.boolean().required()
            }).required()
        });

        const { error } = schema.validate(this.config);
        if (error) {
            throw new Error(`Configuration validation failed: ${error.message}`);
        }
    }

    /**
     * Get WhatsApp configuration
     */
    getWhatsAppConfig(): WhatsAppConfig {
        return this.config.whatsapp;
    }

    /**
     * Get MCP configuration
     */
    getMCPConfig(): MCPConfig {
        return this.config.mcp;
    }

    /**
     * Get command configuration
     */
    getCommandConfig(): CommandConfig {
        return this.config.commands;
    }

    /**
     * Get server configuration
     */
    getServerConfig(): ServerConfig {
        return this.config.server;
    }

    /**
     * Get full configuration
     */
    getConfig() {
        return this.config;
    }
}
