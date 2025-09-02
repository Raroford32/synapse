.PHONY: help build up down logs shell test clean init dev prod

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "${BLUE}Synapse - Self-hosted AI Backend${NC}"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}'

build: ## Build Docker images
	@echo "${BLUE}Building Docker images...${NC}"
	docker-compose build

up: ## Start all services
	@echo "${BLUE}Starting Synapse...${NC}"
	docker-compose up -d
	@echo "${GREEN}✅ Synapse is running at http://localhost:8000${NC}"
	@echo "${GREEN}📚 API docs available at http://localhost:8000/docs${NC}"

down: ## Stop all services
	@echo "${BLUE}Stopping Synapse...${NC}"
	docker-compose down

logs: ## View logs
	docker-compose logs -f

shell: ## Open shell in Synapse container
	docker-compose exec synapse /bin/bash

psql: ## Connect to PostgreSQL
	docker-compose exec postgres psql -U synapse -d synapse_db

redis-cli: ## Connect to Redis
	docker-compose exec redis redis-cli

test: ## Run tests
	@echo "${BLUE}Running tests...${NC}"
	docker-compose exec synapse pytest tests/ -v

clean: ## Clean up volumes and containers
	@echo "${RED}⚠️  This will delete all data!${NC}"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "${GREEN}✅ Cleanup complete${NC}"; \
	fi

init: ## Initialize database
	@echo "${BLUE}Initializing database...${NC}"
	docker-compose exec synapse python scripts/init_db.py
	docker-compose exec synapse alembic upgrade head
	@echo "${GREEN}✅ Database initialized${NC}"

dev: ## Start in development mode
	@echo "${BLUE}Starting in development mode...${NC}"
	ENVIRONMENT=development docker-compose up

prod: ## Start in production mode
	@echo "${BLUE}Starting in production mode...${NC}"
	ENVIRONMENT=production docker-compose up -d

status: ## Check service status
	@echo "${BLUE}Service Status:${NC}"
	@docker-compose ps
	@echo ""
	@echo "${BLUE}Health Check:${NC}"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "${RED}Service not responding${NC}"

restart: ## Restart all services
	@echo "${BLUE}Restarting Synapse...${NC}"
	docker-compose restart
	@echo "${GREEN}✅ Services restarted${NC}"

pull: ## Pull latest images
	@echo "${BLUE}Pulling latest images...${NC}"
	docker-compose pull

backup: ## Backup database
	@echo "${BLUE}Backing up database...${NC}"
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U synapse synapse_db | gzip > backups/synapse_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "${GREEN}✅ Backup saved to backups/synapse_$$(date +%Y%m%d_%H%M%S).sql.gz${NC}"

restore: ## Restore database from backup
	@echo "${BLUE}Available backups:${NC}"
	@ls -1 backups/*.sql.gz 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup; \
	if [ -f "$$backup" ]; then \
		gunzip -c $$backup | docker-compose exec -T postgres psql -U synapse synapse_db; \
		echo "${GREEN}✅ Database restored${NC}"; \
	else \
		echo "${RED}Backup file not found${NC}"; \
	fi