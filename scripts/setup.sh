#!/bin/bash

# MCP WhatsApp Copilot Bridge - Setup Script
# This script sets up the development environment for all components

set -e

echo "🚀 Setting up MCP WhatsApp Copilot Bridge development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.9+ is required but not installed."
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js 16+ is required but not installed."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is required but not installed."
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "git is required but not installed."
        exit 1
    fi
    
    print_status "All requirements satisfied ✓"
}

# Setup Python environment for MCP Server
setup_mcp_server() {
    print_status "Setting up MCP Server (Python)..."
    
    cd mcp-server
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate || source venv/Scripts/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Install development dependencies
    pip install -e .[dev]
    
    print_status "MCP Server setup completed ✓"
    
    cd ..
}

# Setup Node.js environment for WhatsApp Integration
setup_whatsapp_integration() {
    print_status "Setting up WhatsApp Integration (Node.js)..."
    
    cd whatsapp-integration
    
    # Install dependencies
    npm install
    
    # Run lint check
    npm run lint
    
    print_status "WhatsApp Integration setup completed ✓"
    
    cd ..
}

# Setup VS Code Extension
setup_vscode_extension() {
    print_status "Setting up VS Code Extension (TypeScript)..."
    
    cd vscode-extension
    
    # Install dependencies
    npm install
    
    # Compile TypeScript
    npm run compile
    
    print_status "VS Code Extension setup completed ✓"
    
    cd ..
}

# Setup Docker environment
setup_docker() {
    print_status "Setting up Docker environment..."
    
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        # Create docker configuration files
        mkdir -p docker/grafana/{dashboards,datasources}
        
        # Create Prometheus config
        cat > docker/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['mcp-server:8000']
  
  - job_name: 'whatsapp-integration'
    static_configs:
      - targets: ['whatsapp-integration:3000']
EOF
        
        print_status "Docker environment setup completed ✓"
    else
        print_warning "Docker not found. Skipping Docker setup."
    fi
}

# Setup git hooks
setup_git_hooks() {
    print_status "Setting up git hooks..."
    
    # Create pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running pre-commit checks..."

# Check Python code
cd mcp-server
if [ -d "venv" ]; then
    source venv/bin/activate || source venv/Scripts/activate
    black --check src/
    isort --check-only src/
    flake8 src/
    mypy src/
fi
cd ..

# Check Node.js code
cd whatsapp-integration
npm run lint
cd ..

cd vscode-extension
npm run lint
cd ..

echo "Pre-commit checks passed ✓"
EOF
    
    chmod +x .git/hooks/pre-commit
    
    print_status "Git hooks setup completed ✓"
}

# Create environment files
setup_environment() {
    print_status "Setting up environment files..."
    
    # MCP Server environment
    if [ ! -f "mcp-server/.env" ]; then
        cat > mcp-server/.env << EOF
# MCP Server Configuration
DEBUG=true
LOG_LEVEL=info
HOST=localhost
PORT=8000

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/mcp_db

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-change-this
SESSION_TIMEOUT=3600

# VS Code Integration
VSCODE_EXECUTABLE_PATH=code

# GitHub Copilot
COPILOT_ENABLED=true
EOF
        print_status "Created MCP Server .env file"
    fi
    
    # WhatsApp Integration environment
    if [ ! -f "whatsapp-integration/.env" ]; then
        cat > whatsapp-integration/.env << EOF
# WhatsApp Integration Configuration
NODE_ENV=development
PORT=3000

# MCP Server
MCP_SERVER_URL=http://localhost:8000

# Redis
REDIS_URL=redis://localhost:6379

# WhatsApp
WHATSAPP_SESSION_PATH=./.wwebjs_auth
WHATSAPP_CACHE_PATH=./.wwebjs_cache

# Security
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=100

# Logging
LOG_LEVEL=info
EOF
        print_status "Created WhatsApp Integration .env file"
    fi
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Test MCP Server
    cd mcp-server
    if [ -d "venv" ]; then
        source venv/bin/activate || source venv/Scripts/activate
        python -m pytest tests/ -v --cov=src --cov-report=term-missing
    fi
    cd ..
    
    # Test WhatsApp Integration
    cd whatsapp-integration
    npm test
    cd ..
    
    # Test VS Code Extension
    cd vscode-extension
    npm test
    cd ..
    
    print_status "All tests completed ✓"
}

# Main setup function
main() {
    print_status "Starting MCP WhatsApp Copilot Bridge setup..."
    
    check_requirements
    setup_environment
    setup_mcp_server
    setup_whatsapp_integration
    setup_vscode_extension
    setup_docker
    setup_git_hooks
    
    print_status "Setup completed successfully! 🎉"
    print_status ""
    print_status "Next steps:"
    print_status "1. Start the MCP Server: cd mcp-server && source venv/bin/activate && python src/main.py"
    print_status "2. Start WhatsApp Integration: cd whatsapp-integration && npm run dev"
    print_status "3. Install VS Code Extension: cd vscode-extension && code --install-extension ."
    print_status "4. Or use Docker: docker-compose up -d"
    print_status ""
    print_status "For more information, see README.md"
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
