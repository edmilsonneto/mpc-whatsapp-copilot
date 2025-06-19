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

## 📊 Status do Projeto

Veja o progresso detalhado em [TODO.md](./TODO.md)

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
