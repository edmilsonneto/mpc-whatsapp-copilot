@echo off
REM MCP WhatsApp Copilot Bridge - Windows Setup Script

echo 🚀 Setting up MCP WhatsApp Copilot Bridge development environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.9+ is required but not installed.
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 16+ is required but not installed.
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is required but not installed.
    exit /b 1
)

echo [INFO] All requirements satisfied ✓

REM Setup MCP Server
echo [INFO] Setting up MCP Server (Python)...
cd mcp-server

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    python -m venv venv
    echo [INFO] Created Python virtual environment
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
pip install -r requirements.txt

echo [INFO] MCP Server setup completed ✓

cd ..

REM Setup WhatsApp Integration
echo [INFO] Setting up WhatsApp Integration (Node.js)...
cd whatsapp-integration

npm install
npm run lint

echo [INFO] WhatsApp Integration setup completed ✓

cd ..

REM Setup VS Code Extension
echo [INFO] Setting up VS Code Extension (TypeScript)...
cd vscode-extension

npm install
npm run compile

echo [INFO] VS Code Extension setup completed ✓

cd ..

REM Create environment files
echo [INFO] Setting up environment files...

REM MCP Server environment
if not exist "mcp-server\.env" (
    (
        echo # MCP Server Configuration
        echo DEBUG=true
        echo LOG_LEVEL=info
        echo HOST=localhost
        echo PORT=8000
        echo.
        echo # Database
        echo DATABASE_URL=postgresql://postgres:password@localhost:5432/mcp_db
        echo.
        echo # Redis
        echo REDIS_URL=redis://localhost:6379
        echo.
        echo # Security
        echo SECRET_KEY=your-secret-key-change-this
        echo SESSION_TIMEOUT=3600
        echo.
        echo # VS Code Integration
        echo VSCODE_EXECUTABLE_PATH=code
        echo.
        echo # GitHub Copilot
        echo COPILOT_ENABLED=true
    ) > mcp-server\.env
    echo [INFO] Created MCP Server .env file
)

REM WhatsApp Integration environment
if not exist "whatsapp-integration\.env" (
    (
        echo # WhatsApp Integration Configuration
        echo NODE_ENV=development
        echo PORT=3000
        echo.
        echo # MCP Server
        echo MCP_SERVER_URL=http://localhost:8000
        echo.
        echo # Redis
        echo REDIS_URL=redis://localhost:6379
        echo.
        echo # WhatsApp
        echo WHATSAPP_SESSION_PATH=./.wwebjs_auth
        echo WHATSAPP_CACHE_PATH=./.wwebjs_cache
        echo.
        echo # Security
        echo RATE_LIMIT_WINDOW=900000
        echo RATE_LIMIT_MAX=100
        echo.
        echo # Logging
        echo LOG_LEVEL=info
    ) > whatsapp-integration\.env
    echo [INFO] Created WhatsApp Integration .env file
)

echo [INFO] Setup completed successfully! 🎉
echo.
echo [INFO] Next steps:
echo [INFO] 1. Start the MCP Server: cd mcp-server && venv\Scripts\activate && python src\main.py
echo [INFO] 2. Start WhatsApp Integration: cd whatsapp-integration && npm run dev
echo [INFO] 3. Install VS Code Extension: cd vscode-extension && code --install-extension .
echo [INFO] 4. Or use Docker: docker-compose up -d
echo.
echo [INFO] For more information, see README.md

pause
