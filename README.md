# WebScrapy AI Platform

**Plataforma premium de web scraping inteligente com IA NVIDIA**

Coleta, estrutura e entrega dados de qualquer fonte web — passagens aéreas, notícias, leads internacionais, vagas de emprego — com análise por IA, exportação flexível e dashboard enterprise.

---

## Funcionalidades

- **Scraping instantâneo** — Cole uma URL, execute, obtenha dados em segundos
- **Scraping periódico** — Agende coletas por minuto, hora, dia, semana ou mês
- **IA NVIDIA integrada** — Análise de página, geração de seletores, correção automática
- **Auto-healing** — Scraper quebrado? A IA detecta a mudança e corrige sozinha
- **API Discovery** — Tenta usar API pública antes de fazer scraping
- **Busca especializada** — Passagens aéreas, notícias (com imagens), leads B2B, vagas de emprego
- **Exportação** — CSV, Excel, JSON, API endpoint
- **Quality Score** — Score 0-100 de qualidade dos dados extraídos
- **Dashboard premium** — Métricas, logs, histórico, auditoria

---

## Início Rápido

```bash
git clone <repo>
cd webscrapy-ai-platform
cp .env.example .env
# Edite .env e configure NVIDIA_API_KEY
make up
make migrate
# Acesse http://localhost:3000
```

Consulte [docs/SETUP.md](docs/SETUP.md) para instruções detalhadas.

---

## Casos de Uso

### 1. Passagens Aéreas Baratas
```json
POST /api/v1/scrape/instant
{
  "url": "https://www.kayak.com.br/flights/GRU-LIS/2026-08-01",
  "search_type": "flights",
  "params": { "origin": "GRU", "destination": "LIS", "passengers": 1 }
}
```
Retorna: lista de voos com preços, horários, companhias e melhor custo-benefício.

### 2. Notícias Estruturadas com Imagens
```json
POST /api/v1/scrape/instant
{
  "url": "https://g1.globo.com",
  "search_type": "news",
  "params": { "topic": "inteligência artificial", "max_articles": 10 }
}
```
Retorna: artigos com título, resumo, conteúdo completo, URL da imagem, fonte e data.

### 3. Leads Internacionais
```json
POST /api/v1/scrape/scheduled
{
  "name": "Leads Tech EUA",
  "url": "https://...",
  "search_type": "leads",
  "cron_expression": "0 8 * * 1",
  "params": { "sector": "SaaS", "country": "EUA", "role": "CTO" }
}
```
Retorna: leads com empresa, contato, email, LinkedIn e quality score.

### 4. Vagas de Emprego
```json
POST /api/v1/scrape/instant
{
  "url": "https://www.linkedin.com/jobs/search?keywords=Python+FastAPI",
  "search_type": "jobs",
  "params": { "skills": ["Python", "FastAPI", "Docker"], "type": "remote" }
}
```
Retorna: vagas com salário, requisitos e match score com o perfil.

---

## Arquitetura NVIDIA AI com Fallback

```
nvidia/llama-3.3-70b-instruct    → Primário (melhor qualidade)
nvidia/mistral-nemo-12b-instruct → Fallback 1
nvidia/gemma-2-27b-it           → Fallback 2
nvidia/llama-3.1-8b-instruct    → Fallback 3
meta/llama-3.1-405b-instruct    → Fallback 4
```

Se um modelo ficar fora do ar, o sistema automaticamente tenta o próximo — sem interrupção para o usuário.

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Scraping | Scrapy 2.11, Playwright, parsel |
| IA | NVIDIA NIM API (5 modelos com fallback) |
| Queue | Celery + Redis |
| Banco | PostgreSQL 16 |
| Storage | MinIO (S3-compatible) |
| Infra | Docker Compose, Nginx |

---

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Setup e Instalação](docs/SETUP.md)
- [Integração NVIDIA AI](docs/NVIDIA_AI_INTEGRATION.md)
- [Motor de Scraping](docs/SCRAPING_ENGINE.md)
- [API Reference](docs/API.md)
- [Governança e Compliance](docs/GOVERNANCE_AND_COMPLIANCE.md)
- [Auditoria de Repositórios](docs/REPOSITORY_AUDIT.md)
- [Roadmap](docs/ROADMAP.md)

---

## Licença

Proprietário. Todos os direitos reservados.
