# MCP Server WhatsApp-GitHub Copilot Bridge

Um sistema completo que permite controlar o GitHub Copilot rodando localmente via WhatsApp pessoal, usando o protocolo MCP (Model Context Protocol) como ponte.

## 🏗️ Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   WhatsApp      │────▶│   MCP Server    │────▶│  VS Code        │
│   Integration   │     │   (Python)      │     │  Extension      │
│   (Node.js)     │◀────│                 │◀────│  (TypeScript)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Componentes

1. **MCP Server (Python 3.9+)**
   - Ponte entre WhatsApp e GitHub Copilot
   - Gerencia contexto de sessões, comandos, estado de projetos/arquivos
   - Localização: `./mcp-server/`

2. **WhatsApp Integration (Node.js)**
   - Usa `whatsapp-web.js`
   - Parsing de comandos, formatação de respostas, gerenciamento de sessões
   - Localização: `./whatsapp-integration/`

3. **VS Code Extension (TypeScript)**
   - Interface com Copilot via VS Code API
   - Manipulação de arquivos, contexto do editor, aplicação de sugestões
   - Localização: `./vscode-extension/`

## 🚀 Comandos WhatsApp

- `/completa [código]` - Completion de código
- `/explica [código]` - Explicação de código
- `/testa [função]` - Geração de testes unitários
- `/abre [caminho]` - Abrir arquivo no VS Code
- `/contexto` - Obter contexto atual do workspace
- `/aplica [id]` - Aplicar sugestão específica
- `/status` - Status da sessão atual

## 📋 Pré-requisitos

- Python 3.9+
- Node.js 16+
- VS Code
- GitHub Copilot instalado e ativo
- WhatsApp Web

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone <repository-url>
cd mcp-whatsapp-copilot
```

### 2. Configure o MCP Server
```bash
cd mcp-server
pip install -r requirements.txt
```

### 3. Configure a integração WhatsApp
```bash
cd whatsapp-integration
npm install
```

### 4. Configure a extensão VS Code
```bash
cd vscode-extension
npm install
npm run compile
```

### 5. Docker (Opcional)
```bash
docker-compose up -d
```

## 📖 Documentação

- [Guia de Instalação](./docs/installation.md)
- [Guia de Uso](./docs/usage.md)
- [API Reference](./docs/api-reference.md)
- [Troubleshooting](./docs/troubleshooting.md)
- [Contribuição](./docs/contributing.md)

## 🧪 Testes

```bash
# Executar todos os testes
npm run test:all

# MCP Server
cd mcp-server && python -m pytest

# WhatsApp Integration
cd whatsapp-integration && npm test

# VS Code Extension
cd vscode-extension && npm test
```

## 🆕 Implementações Recentes

### ✅ Fase 2 MCP Server - Implementações Concluídas (20/06/2025)

#### 🔐 Sistema de Gerenciamento de Sessões
- **RedisSessionManager**: Gerenciamento persistente de sessões com Redis
- **InMemorySessionManager**: Alternativa em memória para desenvolvimento
- Controle automático de expiração e limpeza de sessões
- Mapeamento eficiente usuário → sessão ativa
- Métricas de sessões integradas

#### ⚡ Sistema de Cache e Performance  
- **RedisCacheService**: Cache distribuído com Redis
- **InMemoryCacheService**: Cache local com LRU eviction
- Cache inteligente para sugestões do Copilot
- Estatísticas de hit/miss rate
- Controle automático de TTL e expiração

#### 🏥 Sistema de Health Checks e Monitoramento
- **HealthService**: Monitoramento abrangente de todos os componentes
- Health checks para sistema, sessões, cache e serviços externos
- Métricas Prometheus integradas
- Monitoramento contínuo com alertas automáticos
- Dashboard de status em tempo real

**Arquivos Implementados:**
- `src/session_manager.py` - Gerenciamento completo de sessões
- `src/cache_service.py` - Sistema de cache com Redis/memória
- `src/health_service.py` - Monitoramento e health checks
- `tests/test_session_manager.py` - Testes de sessões
- `tests/test_cache_service.py` - Testes de cache
- `requirements.txt` - Dependências atualizadas

**Funcionalidades:**
- ✅ Sessões persistentes com Redis ou in-memory
- ✅ Cache distribuído para performance
- ✅ Health monitoring de todos os componentes
- ✅ Métricas Prometheus detalhadas
- ✅ Cleanup automático de sessões expiradas
- ✅ Testes unitários abrangentes

## 📊 Status do Projeto

### 🏗️ Fase 1: Estrutura Base e Configuração ✅ (100%)
- [x] Estrutura de pastas completa
- [x] Configuração Python/Node.js/TypeScript
- [x] Docker e scripts de automação
- [x] Ferramentas de desenvolvimento

### 🔧 Fase 2: MCP Server Core ✅ (100%) 
- [x] Servidor MCP base com FastAPI
- [x] Todas as 7 funções MCP implementadas
- [x] Sistema de gerenciamento de sessões
- [x] Sistema de cache e performance 
- [x] Health checks e monitoramento
- [x] Testes unitários completos

### 📱 Fase 3: WhatsApp Integration 🚧 (Próxima)
- [ ] Setup whatsapp-web.js
- [ ] Parser de comandos WhatsApp
- [ ] Implementação dos 7 comandos principais
- [ ] Sistema de formatação de respostas
- [ ] Rate limiting e segurança

**Progresso Total: 30/65 (46.2%)**

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🏆 Roadmap

- [x] Estrutura base do projeto
- [ ] MCP Server implementation
- [ ] WhatsApp integration
- [ ] VS Code extension
- [ ] Testes e validação
- [ ] Deploy e documentação
- [ ] Melhorias futuras

---

**Desenvolvido com ❤️ para facilitar o desenvolvimento via WhatsApp**
