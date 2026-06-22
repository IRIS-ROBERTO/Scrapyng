# NVIDIA AI Integration

## Visão Geral

A plataforma usa as APIs NVIDIA NIM (NVIDIA Inference Microservices) para todas as operações de inteligência artificial. A integração é feita via `services/ai_engine/nvidia_client.py` com **fallback automático** entre modelos.

## Fallback Chain

A cadeia de fallback garante que a plataforma nunca fique sem IA disponível:

```
Primário:   nvidia/nemotron-3-ultra-550b-a55b    ← Frontier: agentes, raciocínio e contexto longo
Fallback 1: deepseek-ai/deepseek-v4-pro          ← Frontier: código, tool use e contexto 1M
Fallback 2: nvidia/nemotron-3-super-120b-a12b    ← Forte para agentes de alto volume
Fallback 3: deepseek-ai/deepseek-v4-flash        ← Rápido para código e agentes
Fallback 4: nvidia/llama-3.3-70b-instruct        ← Estável para uso geral
Fallback 5: meta/llama-3.1-405b-instruct         ← Reserva legada de alta capacidade
Fallback 6: nvidia/mistral-nemo-12b-instruct     ← Leve, rápido e confiável
Fallback 7: nvidia/gemma-2-27b-it                ← Leve para tarefas simples
Fallback 8: nvidia/llama-3.1-8b-instruct         ← Compacto, último recurso
```

Se todos falharem simultaneamente, o sistema retorna erro gracioso com mensagem ao usuário.

## Configuração

```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

A chave é obtida em: https://build.nvidia.com/

Observação: a aplicação também aceita `NVIDIA_API` como alias local, mas `NVIDIA_API_KEY` é o nome recomendado.

## Agentes de IA Implementados

### 1. PageAnalyzer
- **Função**: Analisa HTML de uma página e identifica campos extraíveis
- **Input**: URL + HTML raw
- **Output**: `{fields: [...], selectors: {...}, strategy: "scrapy|playwright", confidence: 0-1}`

### 2. SelectorGenerator
- **Função**: Gera seletores CSS e XPath para campos específicos
- **Input**: HTML + campo desejado
- **Output**: `{css: "...", xpath: "...", alternatives: [...]}`

### 3. ScraperGenerator
- **Função**: Gera código completo de Spider Scrapy ou script Playwright
- **Input**: URL + campos + estratégia
- **Output**: código Python funcional

### 4. ScraperRepairAgent (Auto-Healing)
- **Função**: Corrige scrapers quebrados comparando HTML antigo vs novo
- **Input**: código original + HTML antigo + HTML novo + erro
- **Output**: `{fixed_code: "...", explanation: "...", changed_selectors: [...]}`

### 5. DataStructuringAgent
- **Função**: Transforma dados brutos em JSON limpo e normalizado
- **Input**: lista de dicts brutos + contexto
- **Output**: dados normalizados + schema inferido

### 6. DataValidationAgent
- **Função**: Valida qualidade dos dados extraídos
- **Input**: dados + schema esperado
- **Output**: `{score: 0-100, issues: [...], valid_count: int, invalid_count: int}`

### 7. InsightAgent
- **Função**: Gera resumo executivo e insights dos dados coletados
- **Input**: dados estruturados + contexto do job
- **Output**: relatório em markdown com insights, anomalias, tendências

### 8. SearchIntelligence (Busca Especializada)

#### Passagens Aéreas
```python
result = await search_intel.analyze_flight_search(
    url="https://www.kayak.com.br/...",
    html=page_html,
    params={"origin": "GRU", "destination": "LIS", "date": "2026-08-01"}
)
# Retorna: flights[], cheapest_option, best_value_option, price_alerts
```

#### Notícias
```python
result = await search_intel.analyze_news_search(
    url="https://g1.globo.com/...",
    html=page_html,
    params={"topic": "inteligência artificial", "period": "7d"}
)
# Retorna: articles[{title, summary, content, image_url, source, published_at}]
```

#### Leads Internacionais
```python
result = await search_intel.analyze_leads_search(
    url="https://...",
    html=page_html,
    params={"sector": "tecnologia", "country": "EUA", "role": "CTO"}
)
# Retorna: leads[{company, contact_name, email, phone, linkedin, quality_score}]
```

#### Vagas de Emprego
```python
result = await search_intel.analyze_jobs_search(
    url="https://www.linkedin.com/jobs/...",
    html=page_html,
    params={"skills": ["Python", "FastAPI"], "location": "Remoto"}
)
# Retorna: jobs[{title, company, salary_range, requirements, match_score, apply_url}]
```

## Custo Estimado

| Operação | Tokens Médios | Custo Estimado |
|---|---|---|
| Análise de página | ~2.000 tokens | ~$0.002 |
| Geração de scraper | ~3.000 tokens | ~$0.003 |
| Estruturação de dados | ~4.000 tokens | ~$0.004 |
| Insight executivo | ~5.000 tokens | ~$0.005 |

*Valores aproximados. A plataforma prioriza endpoints gratuitos da NVIDIA Build quando disponíveis.*

## Monitoramento de IA

O dashboard exibe:
- Total de chamadas à API por modelo
- Custo acumulado estimado
- Taxa de fallback (qual % foi para modelos secundários)
- Latência média por modelo
- Status de disponibilidade em tempo real
