#!/bin/bash
# Quick start script for Synapse

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║          SYNAPSE QUICK START           ║"
echo "║   Self-hosted AI Backend for IDEs      ║"
echo "╔════════════════════════════════════════╝"
echo -e "${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${BLUE}Please edit .env and add your API keys:${NC}"
    echo "  - OPENROUTER_API_KEY (required for LLM)"
    echo "  - OPENAI_API_KEY (required for embeddings)"
    echo ""
    read -p "Press Enter after adding your API keys..."
fi

# Validate API keys
source .env
if [ "$OPENROUTER_API_KEY" = "sk-or-v1-..." ] || [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}❌ Please set OPENROUTER_API_KEY in .env file${NC}"
    echo "Get your key from: https://openrouter.ai/keys"
    exit 1
fi

if [ "$OPENAI_API_KEY" = "sk-..." ] || [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ Please set OPENAI_API_KEY in .env file${NC}"
    echo "Get your key from: https://platform.openai.com/api-keys"
    exit 1
fi

echo -e "${GREEN}✅ API keys configured${NC}"

# Build and start services
echo -e "${BLUE}Building Docker images...${NC}"
docker-compose build

echo -e "${BLUE}Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${BLUE}Waiting for services to be ready...${NC}"
sleep 10

# Check health
echo -e "${BLUE}Checking service health...${NC}"
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Synapse is running!${NC}"
    echo ""
    echo -e "${BLUE}🎉 Setup Complete!${NC}"
    echo ""
    echo "Synapse is now running at:"
    echo -e "  ${GREEN}API:${NC} http://localhost:8000"
    echo -e "  ${GREEN}Docs:${NC} http://localhost:8000/docs"
    echo ""
    echo "Configure your IDE:"
    echo -e "  ${BLUE}Cursor/Cline:${NC}"
    echo "    - API URL: http://localhost:8000/v1"
    echo "    - API Key: ${API_KEY:-your-api-key}"
    echo "    - Model: synapse"
    echo ""
    echo "Useful commands:"
    echo "  make logs    - View logs"
    echo "  make down    - Stop services"
    echo "  make status  - Check status"
    echo ""
else
    echo -e "${RED}❌ Service health check failed${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi