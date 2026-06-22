.PHONY: up down build logs migrate test setup help

# ── Docker Compose ───────────────────────────────────────────

up: ## Sobe todos os serviços em background
	docker compose up --build -d

down: ## Para todos os serviços
	docker compose down

build: ## Build das imagens sem subir
	docker compose build

restart: ## Reinicia todos os serviços
	docker compose restart

logs: ## Logs de todos os serviços
	docker compose logs -f

logs-backend: ## Logs do backend
	docker compose logs -f backend

logs-worker: ## Logs do worker Celery
	docker compose logs -f worker

logs-frontend: ## Logs do frontend
	docker compose logs -f frontend

# ── Database ─────────────────────────────────────────────────

migrate: ## Executa migrações Alembic
	docker compose exec backend alembic upgrade head

migrate-down: ## Desfaz última migração
	docker compose exec backend alembic downgrade -1

migrate-history: ## Histórico de migrações
	docker compose exec backend alembic history

seed-apis: ## Popula catálogo de APIs públicas
	docker compose exec backend python scripts/seed_public_apis.py

# ── Desenvolvimento ──────────────────────────────────────────

dev-backend: ## Backend em modo desenvolvimento local
	cd apps/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Frontend em modo desenvolvimento local
	cd apps/frontend && npm run dev

dev-worker: ## Worker Celery local
	cd apps/backend && celery -A services.scheduler_engine.celery_app worker --loglevel=info

# ── Testes ───────────────────────────────────────────────────

test: ## Todos os testes
	docker compose exec backend pytest tests/ -v

test-unit: ## Testes unitários (sem serviços externos)
	docker compose exec backend pytest tests/unit/ -v --no-header

test-integration: ## Testes de integração (requer serviços)
	docker compose exec backend pytest tests/integration/ -v -m integration

# ── NVIDIA ───────────────────────────────────────────────────

test-nvidia: ## Testa conexão com todos os modelos NVIDIA
	docker compose exec backend python scripts/test_nvidia_connection.py

# ── Utilitários ──────────────────────────────────────────────

shell-backend: ## Shell no container backend
	docker compose exec backend bash

shell-frontend: ## Shell no container frontend
	docker compose exec frontend sh

shell-db: ## Shell PostgreSQL
	docker compose exec postgres psql -U webscrapy -d webscrapy

setup: ## Configuração inicial do projeto
	@echo "→ Criando .env..."
	@if not exist .env copy .env.example .env
	@echo ""
	@echo "✓ .env criado. Configure obrigatoriamente:"
	@echo "  NVIDIA_API_KEY=  (https://build.nvidia.com/)"
	@echo "  SECRET_KEY=      (openssl rand -hex 32)"
	@echo ""
	@echo "Depois execute: make up && make migrate"

ps: ## Status dos containers
	docker compose ps

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
