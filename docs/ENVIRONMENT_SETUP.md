# Environment Setup Guide

This guide explains how to set up environment variables for Endor Cockpit development, testing, and AI agent operations.

## 🚀 Quick Start

### 1. Automatic Setup
```bash
# Run the setup script to create .env file and validate configuration
python scripts/setup_environment.py
```

### 2. Manual Setup
```bash
# Copy the example file
cp env.example .env

# Edit with your actual values
# Windows: notepad .env
# Linux/Mac: nano .env or vim .env
```

## 📋 Required Environment Variables

### Core API Configuration
```bash
# Endor Labs API endpoint
ENDOR_API=https://api.endorlabs.com

# API credentials (get these from your Endor Labs dashboard)
ENDOR_API_CREDENTIALS_KEY=your-actual-api-key
ENDOR_API_CREDENTIALS_SECRET=your-actual-api-secret
```

### Optional Configuration
```bash
# Namespace for operations (defaults to tenant namespace)
ENDOR_NAMESPACE=your-tenant-namespace

# Agent ID for testing and identification
AGENT_ID=my-development-agent

# OpenAI API Key for RAG functionality
OPENAI_API_KEY=your-openai-api-key
```

## 🔧 Development Environment Setup

### VS Code Integration

The project includes VS Code settings that automatically:
- Set `PYTHONPATH` to include the `src` directory
- Configure UV environment variables
- Provide terminal profiles that load `.env` files

**Terminal Profiles Available:**
- **PowerShell**: Standard PowerShell with UV
- **PowerShell with Env**: PowerShell that loads `.env` variables
- **Bash/Linux**: Bash with environment loading
- **Zsh/macOS**: Zsh with environment loading

### Direnv Integration

If you use `direnv`, the `.envrc` file will:
- Activate the UV virtual environment
- Set `PYTHONPATH` correctly
- Load variables from `.env` file

```bash
# Install direnv (if not already installed)
# Windows: choco install direnv
# macOS: brew install direnv
# Linux: apt install direnv

# Allow direnv in this directory
direnv allow
```

## 🧪 Testing Your Setup

### 1. Validate Environment
```bash
# Run the validation script
python scripts/validate_environment.py

# Or with UV
uv run python scripts/validate_environment.py
```

### 2. Test SDK Import
```bash
# Test that the SDK can be imported
uv run python -c "from endor_cockpit.api_client import EndorClient; print('✅ SDK import successful')"
```

### 3. Test API Connection
```bash
# Test API connection (requires valid credentials)
uv run python -c "
from endor_cockpit.api_client import EndorClient
client = EndorClient()
print('✅ API client created successfully')
"
```

## 🤖 AI Agent Environment

For AI agents working with this codebase, the environment should include:

### Required for All Operations
- `ENDOR_API`: API endpoint
- `ENDOR_API_CREDENTIALS_KEY`: API key
- `ENDOR_API_CREDENTIALS_SECRET`: API secret

### Required for RAG Operations
- `OPENAI_API_KEY`: For vector database queries and semantic search

### Required for Namespace Operations
- `ENDOR_NAMESPACE`: Target namespace for operations

### Agent-Specific Variables
- `AGENT_ID`: Unique identifier for the agent

## 🔍 Troubleshooting

### Common Issues

#### 1. PYTHONPATH Not Set
**Problem**: `ModuleNotFoundError: No module named 'endor_cockpit'`

**Solution**: Ensure `PYTHONPATH` includes the `src` directory
```bash
# Windows PowerShell
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"

# Linux/macOS
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
```

#### 2. UV Environment Issues
**Problem**: UV not using project virtual environment

**Solution**: Set `UV_SYSTEM_PYTHON=0`
```bash
# Windows PowerShell
$env:UV_SYSTEM_PYTHON = "0"

# Linux/macOS
export UV_SYSTEM_PYTHON=0
```

#### 3. Environment Variables Not Loading
**Problem**: Variables from `.env` not available in terminal

**Solutions**:
- **VS Code**: Restart terminal or reload window
- **Terminal**: Run `source .envrc` (if using direnv)
- **Manual**: Run `source .env` (Linux/macOS) or load in PowerShell

#### 4. API Connection Issues
**Problem**: API calls failing with authentication errors

**Check**:
- API credentials are correct and not placeholder values
- API endpoint is accessible
- Network connectivity to Endor Labs API

### Validation Commands

```bash
# Check environment variables
echo $ENDOR_API
echo $ENDOR_API_CREDENTIALS_KEY

# Check Python path
python -c "import sys; print(sys.path)"

# Check UV environment
uv run python -c "import sys; print(sys.executable)"
```

## 📚 Additional Resources

- [VS Code Settings](../.vscode/settings.json): Terminal and environment configuration
- [Environment Example](../env.example): Template for environment variables
- [Direnv Configuration](../.envrc): Automatic environment loading
- [Validation Script](../scripts/validate_environment.py): Environment validation
- [Setup Script](../scripts/setup_environment.py): Automated environment setup

## 🔒 Security Notes

- Never commit `.env` files to version control
- Use placeholder values in example files
- Rotate API credentials regularly
- Store sensitive credentials in secure credential managers when possible

## 🎯 Success Indicators

Your environment is properly configured when:
- ✅ All required environment variables are set with real values
- ✅ `PYTHONPATH` includes the `src` directory
- ✅ UV environment is active (`UV_SYSTEM_PYTHON=0`)
- ✅ SDK imports work without errors
- ✅ API client can be instantiated
- ✅ Validation script passes all checks
