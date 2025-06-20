/**
 * Logger Utility
 * 
 * Centralized logging service using Winston with structured logging
 */

import winston from 'winston';

export class Logger {
    private static instance: winston.Logger;

    /**
     * Get logger instance (singleton)
     */
    public static getInstance(): winston.Logger {
        if (!Logger.instance) {
            Logger.instance = Logger.createLogger();
        }
        return Logger.instance;
    }    /**
     * Create Winston logger instance
     */
    private static createLogger(): winston.Logger {
        const logLevel = process.env['LOG_LEVEL'] || 'info';
        const logFormat = process.env['NODE_ENV'] === 'production' ? 'json' : 'console';

        const consoleFormat = winston.format.combine(
            winston.format.timestamp(),
            winston.format.colorize(),
            winston.format.printf(({ timestamp, level, message, ...meta }) => {
                const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
                return `${timestamp} [${level}]: ${message}${metaStr}`;
            })
        );

        const jsonFormat = winston.format.combine(
            winston.format.timestamp(),
            winston.format.errors({ stack: true }),
            winston.format.json()
        );

        const transports: winston.transport[] = [
            new winston.transports.Console({
                format: logFormat === 'json' ? jsonFormat : consoleFormat
            })
        ];        // Add file transport in production
        if (process.env['NODE_ENV'] === 'production') {
            transports.push(
                new winston.transports.File({
                    filename: 'logs/error.log',
                    level: 'error',
                    format: jsonFormat
                }),
                new winston.transports.File({
                    filename: 'logs/combined.log',
                    format: jsonFormat
                })
            );
        }

        return winston.createLogger({
            level: logLevel,
            transports,
            exitOnError: false
        });
    }
}
