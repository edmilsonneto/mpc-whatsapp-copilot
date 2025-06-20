/**
 * Simple test for basic functionality
 */

import { ConfigManager } from '../src/config/config-manager';

describe('Basic Functionality Tests', () => {
    it('should create ConfigManager instance', () => {
        const config = new ConfigManager();
        expect(config).toBeInstanceOf(ConfigManager);
    });

    it('should have default WhatsApp configuration', () => {
        const config = new ConfigManager();
        const whatsappConfig = config.getWhatsAppConfig();
        
        expect(whatsappConfig).toBeDefined();
        expect(whatsappConfig.sessionPath).toBeDefined();
        expect(whatsappConfig.headless).toBeDefined();
        expect(whatsappConfig.qrRetries).toBeGreaterThan(0);
    });

    it('should have default MCP configuration', () => {
        const config = new ConfigManager();
        const mcpConfig = config.getMCPConfig();
        
        expect(mcpConfig).toBeDefined();
        expect(mcpConfig.serverUrl).toBeDefined();
        expect(mcpConfig.timeout).toBeGreaterThan(0);
    });

    it('should have server configuration', () => {
        const config = new ConfigManager();
        const serverConfig = config.getServerConfig();
        
        expect(serverConfig).toBeDefined();
        expect(serverConfig.port).toBeGreaterThan(0);
        expect(serverConfig.host).toBeDefined();
    });
});
