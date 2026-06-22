# REPOSITORY AUDIT

> Gerado em 2026-06-22 | Fase 1 do Plano de Execução

---

## 1. nextlevelbuilder/ui-ux-pro-max-skill

### Resumo
Toolkit de inteligência de design UI/UX com banco de dados pesquisável. Inclui 50+ estilos, 161 paletas de cores, 57 pares tipográficos, 161 tipos de produto, 99 diretrizes UX e 25 tipos de gráfico para 10 stacks tecnológicos.

### Principais Diretórios
| Diretório | Conteúdo |
|---|---|
| `src/ui-ux-pro-max/data/` | CSVs canônicos: products, styles, colors, typography, charts, ux-guidelines |
| `src/ui-ux-pro-max/scripts/` | Motor de busca BM25 + regex (search.py, core.py, design_system.py) |
| `.claude/skills/ui-ux-pro-max/` | Skill para Claude Code |
| `cli/` | CLI npm (uipro-cli) com templates |

### Tecnologias Detectadas
- Python 3.x (scripts de busca, sem dependências externas)
- TypeScript (CLI npm)
- BM25 + regex para ranking de busca

### Padrões Úteis
- Design system com tokens primitivos → semânticos → componente
- Paletas de cores por tipo de produto (SaaS, dashboard, e-commerce)
- Diretrizes de acessibilidade WCAG 4.5:1, touch targets 44×44px
- Estilos: glassmorphism, dark mode, bento grid, minimalism, brutalism

### Oportunidades de Reaproveitamento
- ✅ Paletas de cores para o design do dashboard premium
- ✅ Diretrizes UX para formulários, tabelas, estados de loading/empty/error
- ✅ Font pairings para tipografia da plataforma
- ✅ Padrões de SaaS enterprise para UI cards e layouts
- ✅ Stack Next.js + shadcn/ui + Tailwind diretamente suportada

### Riscos
- Nenhum risco crítico. Repositório somente leitura/referência.

### Decisões Técnicas
- Usar paleta de cores "dark dashboard" com acentos cyan/emerald
- Aplicar glassmorphism moderado em cards analíticos
- Font pairing: Inter (body) + Geist Mono (código/métricas)
- shadcn/ui como biblioteca de componentes principal

---

## 2. public-apis/public-apis

### Resumo
Catálogo curado manualmente com centenas de APIs públicas gratuitas em categorias como News, Jobs, Transportation, Finance, Geocoding e muito mais.

### Principais Categorias Relevantes para a Plataforma
| Categoria | Relevância |
|---|---|
| **News** | NewsAPI, Gnews, NY Times — busca de notícias estruturadas |
| **Jobs** | Arbeitnow, Reed, Jooble, The Muse — busca de empregos |
| **Transportation** | Aviationstack, FlightAware, Skyscanner API — passagens aéreas |
| **Geocoding** | OpenCage, Nominatim, HERE — localização |
| **Finance** | Alpha Vantage, Marketstack — dados financeiros |
| **Government** | APIs governamentais para leads |
| **Business** | Hunter.io, Apollo equivalents — leads internacionais |

### Tecnologias Detectadas
- Markdown como formato de catálogo principal
- Scripts Python para validação de links e formato

### Oportunidades de Reaproveitamento
- ✅ Usar como banco de dados para o `api_discovery_engine`
- ✅ Indexar README.md como fonte de APIs sugeridas antes do scraping
- ✅ Mapear categorias para use cases específicos do usuário

### Decisões Técnicas
- Parsear o README.md do repositório para extrair todas as APIs catalogadas
- Armazenar em PostgreSQL como tabela `public_api_catalog`
- Indexar por categoria, autenticação, CORS e HTTPS

---

## 3. scrapy/scrapy

### Resumo
Framework production-stable de web scraping em Python. Arquitetura baseada em Twisted (async), com suporte a CSS e XPath, robots.txt via Protego, e pipeline de processamento modular.

### Principais Componentes
| Componente | Função |
|---|---|
| `scrapy/spiders/` | Base classes para spiders |
| `scrapy/http/` | Request/Response pipeline |
| `scrapy/selector/` | CSS + XPath selectors via parsel/lxml |
| `scrapy/pipelines/` | Item processing pipelines |
| `scrapy/downloadermiddlewares/` | Retry, User-Agent, Redirect, Cookies |
| `scrapy/extensions/` | Telnet console, log stats, core signals |
| `scrapy/settings/` | Configuração modular e hierárquica |

### Dependências Chave
```
Twisted>=21.7.0      # async I/O
lxml>=4.6.4          # HTML/XML parsing
parsel>=1.5.0        # CSS/XPath selectors
protego>=0.1.15      # robots.txt parser
cssselect>=0.9.1     # CSS to XPath translator
w3lib>=1.17.0        # URL utilities
```

### Padrões Úteis
- Spider como classe com `parse()` callback
- Settings hierárquicas: default → project → spider
- AutoThrottle para controle de concorrência adaptativo
- Signals para hooks de eventos (spider_opened, item_scraped etc.)
- CrawlerRunner/CrawlerProcess para execução programática (usado pelo nosso backend)

### O que SERÁ usado
- ✅ `CrawlerRunner` para execução de spiders via FastAPI
- ✅ `ItemPipeline` para normalização de dados
- ✅ `DownloaderMiddleware` para retry, user-agent e proxy
- ✅ `parsel.Selector` para CSS/XPath em modo standalone
- ✅ AutoThrottle para scraping respeitoso

### O que NÃO será usado diretamente
- ❌ CLI `scrapy crawl` (usaremos execução programática)
- ❌ scrapy.cfg / scrapyd (gerenciamento próprio via Celery)
- ❌ Feed exporters nativos (export_engine próprio)

---

## Repositórios Adicionais Identificados como Benéficos

| Repositório | Motivo |
|---|---|
| `microsoft/playwright-python` | Scraping dinâmico JS-rendered |
| `tiangolo/fastapi` | Framework backend principal |
| `celery/celery` | Task queue para jobs periódicos |
| `pydantic/pydantic` | Validação e serialização de dados |

---

## Resumo das Decisões Técnicas Globais

| Área | Decisão |
|---|---|
| Scraping estático | Scrapy CrawlerRunner programático |
| Scraping dinâmico | Playwright-Python async |
| Backend API | FastAPI + Pydantic + SQLAlchemy |
| Task Queue | Celery + Redis |
| Banco relacional | PostgreSQL |
| Cache | Redis |
| Storage bruto | MinIO (S3-compatible) |
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui |
| IA | NVIDIA NIM API com fallback chain de 5 modelos |
| Design | Dark dashboard + glassmorphism + Inter/Geist |
| Exportação | CSV, Excel, JSON, API, relatório PDF |
