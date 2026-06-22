# Setup — WebScrapy AI Platform

## Pré-requisitos

- Docker Desktop ≥ 4.0
- Docker Compose ≥ 2.0
- Git
- Node.js ≥ 20 (para desenvolvimento frontend)
- Python ≥ 3.12 (para desenvolvimento backend)

## Instalação Rápida (Docker)

```bash
# 1. Clonar o repositório
git clone <seu-repo>
cd webscrapy-ai-platform

# 2. Criar .env a partir do exemplo
cp .env.example .env

# 3. Editar .env e configurar obrigatoriamente:
#    NVIDIA_API_KEY=nvapi-xxxxxxxxxxxx
#    SECRET_KEY=$(openssl rand -hex 32)
nano .env

# 4. Subir todos os serviços
make up
# ou: docker compose up --build -d

# 5. Executar migrações do banco
make migrate

# 6. Acessar a plataforma
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs (Swagger): http://localhost:8000/docs
# MinIO Console: http://localhost:9001 (user: minioadmin / pass: minioadmin123)
```

## Desenvolvimento Local

### Backend

```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Subir apenas bancos de dados
docker compose up postgres redis minio -d

# Iniciar backend em modo dev
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd apps/frontend
npm install

# Configurar variável de ambiente
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Iniciar frontend em modo dev
npm run dev
# Acesse: http://localhost:3000
```

### Worker Celery

```bash
cd apps/backend
celery -A services.scheduler_engine.celery_app worker --loglevel=info
```

## Configurar NVIDIA API

1. Acesse https://build.nvidia.com/
2. Crie uma conta e gere uma API Key
3. No `.env`, configure:
```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

Os modelos são testados automaticamente. O sistema usa fallback entre eles.

## Executar Testes

```bash
# Todos os testes
make test

# Somente unitários (sem serviços rodando)
make test-unit

# Testes de integração (requer serviços)
docker compose exec backend pytest tests/integration/ -v -m integration
```

## Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Exemplo |
|---|---|---|
| `NVIDIA_API_KEY` | Chave da API NVIDIA NIM | `nvapi-xxxx` |
| `SECRET_KEY` | Chave para JWT (≥ 32 chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | URL do PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_URL` | URL do Redis | `redis://localhost:6379/0` |

## Variáveis Opcionais (APIs Externas)

| Variável | API | Para que serve |
|---|---|---|
| `NEWSAPI_KEY` | NewsAPI.org | Notícias sem scraping |
| `AVIATIONSTACK_KEY` | Aviationstack | Voos sem scraping |
| `HUNTER_IO_KEY` | Hunter.io | Leads/emails sem scraping |

## Solução de Problemas

### Backend não sobe
```bash
docker compose logs backend
# Verificar: DATABASE_URL correto? PostgreSQL rodando?
```

### NVIDIA API retorna 401
```bash
# Verificar se NVIDIA_API_KEY está configurada no .env
grep NVIDIA_API_KEY .env
```

### Scraping muito lento
```bash
# Aumentar workers do Celery
docker compose scale worker=4
```

### MinIO não acessível
```bash
# Console MinIO em http://localhost:9001
# Usuário padrão: minioadmin / minioadmin123
```
