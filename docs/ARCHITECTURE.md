# Arquitetura — WebScrapy AI Platform

## Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                     USUÁRIO / BROWSER                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│              NGINX (Reverse Proxy / SSL termination)         │
└──────┬─────────────────────────────┬───────────────────────┘
       │ /                           │ /api/*
┌──────▼──────┐              ┌──────▼──────────────┐
│  FRONTEND   │              │  BACKEND (FastAPI)   │
│  Next.js 14 │              │  Port 8000           │
│  Port 3000  │              └──────┬───────────────┘
└─────────────┘                     │
                      ┌─────────────┼──────────────┐
               ┌──────▼──┐   ┌─────▼────┐   ┌─────▼────┐
               │PostgreSQL│   │  Redis   │   │  MinIO   │
               │ (dados)  │   │(cache/q) │   │(storage) │
               └─────────┘   └─────┬────┘   └──────────┘
                                   │
                         ┌─────────▼─────────┐
                         │   CELERY WORKERS   │
                         │  (scraping tasks)  │
                         └─────────┬──────────┘
                                   │
              ┌────────────────────┼──────────────────┐
       ┌──────▼──────┐    ┌───────▼──────┐    ┌──────▼──────┐
       │   SCRAPY    │    │  PLAYWRIGHT  │    │  NVIDIA NIM  │
       │  (estático) │    │  (dinâmico)  │    │  AI (NLP)   │
       └─────────────┘    └─────────────┘    └─────────────┘
```

## Serviços

| Serviço | Tecnologia | Porta | Função |
|---|---|---|---|
| Frontend | Next.js 14 | 3000 | Interface premium |
| Backend | FastAPI + Uvicorn | 8000 | API REST |
| Worker | Celery | - | Execução assíncrona |
| Scheduler | Celery Beat | - | Jobs periódicos |
| PostgreSQL | v16 | 5432 | Dados relacionais |
| Redis | v7 | 6379 | Cache + Message broker |
| MinIO | Latest | 9000 | Storage de resultados |

## Módulos Internos

### `apps/backend/app/`
- `core/` — Configuração, banco, segurança, logging
- `models/` — Entidades SQLAlchemy (User, ScrapingJob, Run, Result, Schedule)
- `schemas/` — Pydantic schemas para request/response
- `api/routes/` — Endpoints FastAPI organizados por domínio

### `services/`
- `scraper_engine/` — Scrapy runner, Playwright runner, normalização
- `scheduler_engine/` — Celery tasks, agendamento, job manager
- `ai_engine/` — NVIDIA NIM client com fallback, agentes especializados
- `api_discovery_engine/` — Catálogo de APIs públicas, matching
- `data_quality_engine/` — Score, duplicatas, validação, change detection
- `export_engine/` — CSV, Excel, JSON, relatórios
- `monitoring_engine/` — Métricas, health checks, logs estruturados

## Fluxo de Scraping Instantâneo

```
1. POST /scrape/instant
2. Validar URL (segurança, robots.txt)
3. Buscar API pública equivalente (api_discovery_engine)
4. Se API disponível → usar API diretamente
5. Se não → analisar página com IA (nvidia_client → page_analyzer)
6. Escolher método: Scrapy (estático) ou Playwright (JS-heavy)
7. Executar via Celery task (assíncrono)
8. Normalizar resultados (result_normalizer)
9. Calcular quality score (quality_score)
10. Salvar em PostgreSQL + MinIO
11. Retornar job_id para polling
```

## Fluxo de Auto-Healing

```
1. Scraper falha com erro de seletor
2. Capturar HTML atual da página
3. Buscar HTML anterior do job (MinIO)
4. Enviar diff para ScraperRepairAgent (NVIDIA NIM)
5. IA gera novo seletor
6. Testar novo seletor automaticamente
7. Se funcionar: atualizar versão do scraper (version_manager)
8. Registrar em audit_log
9. Notificar usuário via WebSocket/email
```

## Fallback Chain NVIDIA NIM

```python
MODELS = [
    "nvidia/llama-3.3-70b-instruct",    # Primário
    "nvidia/mistral-nemo-12b-instruct",  # Fallback 1
    "nvidia/gemma-2-27b-it",            # Fallback 2
    "nvidia/llama-3.1-8b-instruct",     # Fallback 3
    "meta/llama-3.1-405b-instruct",     # Fallback 4
]
# Se todos falharem → erro gracioso ao usuário
```

## Casos de Uso Especializados

### Passagens Aéreas
- Sites suportados: Kayak, Google Flights, Decolar, ViajaNet, MaxMilhas, Skyscanner
- Dados extraídos: origem, destino, datas, preço, companhia, escalas, bagagem
- API first: Aviationstack, Amadeus (se configuradas)
- Output: lista de voos ordenada por preço + melhor custo-benefício

### Notícias
- Sites suportados: G1, UOL, Folha, Reuters, BBC Brasil, CNN Brasil
- Dados extraídos: título, resumo, conteúdo, **imagem principal**, fonte, data, autor
- API first: NewsAPI, GNews, TheNewsAPI
- Output: artigos estruturados com metadados completos

### Leads Internacionais
- Sites suportados: LinkedIn, Apollo equivalents, páginas de contato
- Dados extraídos: empresa, contato, email, telefone, LinkedIn, país, setor
- API first: Hunter.io (se configurado)
- Output: leads com quality score 0-100

### Vagas de Emprego
- Sites suportados: LinkedIn Jobs, Indeed, Glassdoor, Catho, InfoJobs, Gupy
- Dados extraídos: título, empresa, localização, salário, requisitos, habilidades
- API first: Arbeitnow, The Muse API (gratuitas)
- Output: vagas com match score baseado no perfil informado

## Escalabilidade

- Celery workers horizontalmente escaláveis (Docker Swarm / K8s)
- Redis Cluster para alta disponibilidade
- PostgreSQL com read replicas
- MinIO em modo distribuído para TB de dados
- Rate limiting por usuário e por IP
- Circuit breaker no NVIDIA client (fallback chain)
