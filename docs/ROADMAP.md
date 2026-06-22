# Roadmap — WebScrapy AI Platform

## Fase Atual: MVP Enterprise (v1.0)

### ✅ Entregues
- Arquitetura modular completa
- Backend FastAPI com todos os endpoints
- Motor de scraping Scrapy + Playwright
- IA NVIDIA com fallback chain de 5 modelos
- Busca especializada: passagens, notícias, leads, empregos
- Auto-healing de scrapers
- Dashboard premium dark mode
- Exportação CSV, Excel, JSON
- Agendamento periódico via Celery
- Qualidade de dados com score
- Docker Compose completo
- Documentação completa

---

## v1.1 — Alertas e Notificações

- [ ] Email de notificação quando job falha
- [ ] Webhook configurável por job (Slack, Discord, Teams)
- [ ] Alerta de mudança de preço (passagens aéreas)
- [ ] Alerta de nova vaga compatível com perfil
- [ ] Alerta de notícia por keyword

## v1.2 — Analytics Avançado

- [ ] Gráficos de tendência de preços ao longo do tempo
- [ ] Comparação entre execuções do mesmo job
- [ ] Relatório executivo com IA (insight agent)
- [ ] Export de relatório PDF
- [ ] Visualização geográfica de leads (mapa)

## v1.3 — Colaboração

- [ ] Workspaces com múltiplos usuários
- [ ] Compartilhamento de jobs entre usuários
- [ ] Comentários em resultados
- [ ] Tags e categorias de jobs
- [ ] Templates de scraping pré-configurados

## v2.0 — Enterprise Features

- [ ] SSO via SAML/OIDC (Azure AD, Okta, Google)
- [ ] RBAC granular (admin, editor, viewer, api-only)
- [ ] Multi-tenancy com isolamento de dados
- [ ] SLA garantido e monitoramento 24/7
- [ ] API pública com rate limiting por plano
- [ ] Webhooks para integração com sistemas externos (Zapier, Make)
- [ ] Proxy rotation gerenciado (pool de IPs residenciais)

## v2.1 — Inteligência Avançada

- [ ] Fine-tuning de modelo NVIDIA para domínios específicos
- [ ] Agente autônomo de descoberta de fontes
- [ ] Recomendação proativa de dados relevantes
- [ ] Detecção automática de anomalias nos dados
- [ ] Pipeline de ETL visual (drag-and-drop)
- [ ] Integração com data warehouses (BigQuery, Snowflake, Redshift)

## v2.2 — Marketplace

- [ ] Marketplace de templates de scraping
- [ ] Venda de datasets prontos
- [ ] API de dados curados
- [ ] Plugin system para parsers customizados

## v3.0 — AI-Native

- [ ] Agente autônomo que cria, agenda e monitora scrapers sozinho
- [ ] Linguagem natural para descrever o que quer coletar
- [ ] Auto-descoberta de fontes relevantes
- [ ] Enriquecimento de dados com múltiplas fontes
- [ ] IA de negócios: analisa dados e sugere ações

---

## Pendências Técnicas (v1.0)

1. **WebSocket para status em tempo real** — Atualmente o frontend faz polling. Implementar WS para atualizações push.
2. **Rate limiting por usuário** — Implementado a nível de endpoint, mas falta persistência cross-instance com Redis.
3. **Playwright stealth avançado** — Integrar playwright-stealth para evitar detecção em sites como LinkedIn.
4. **Queue prioritária** — Jobs instantâneos devem ter prioridade sobre agendados no Celery.
5. **Criptografia de dados sensíveis** — Dados como emails de leads deveriam ser criptografados at-rest.
6. **Testes E2E** — Playwright tests do frontend não implementados (estrutura criada, testes pendentes).
7. **Monitoramento Grafana** — Stack Prometheus/Grafana para métricas de sistema.
8. **Compressão de resultados** — Resultados grandes no MinIO deveriam ser comprimidos (gzip/lz4).
