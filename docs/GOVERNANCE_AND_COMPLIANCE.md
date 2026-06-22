# Governance and Compliance

## Segurança

### Autenticação
- JWT Bearer tokens com expiração configurável (padrão: 480 minutos)
- Senhas armazenadas com bcrypt (salt rounds: 12)
- Refresh token rotation implementado
- Rate limiting: 100 requisições/minuto por IP

### Proteção de Chaves de API
- `NVIDIA_API_KEY` e demais chaves NUNCA são logadas, expostas no frontend ou commitadas
- Variáveis de ambiente via `.env` (gitignored por padrão)
- Secrets em produção via Docker Secrets ou HashiCorp Vault
- Auditoria de acesso às chaves registrada

### Rate Limiting
- Endpoint `/scrape/instant`: 10 requisições/minuto por usuário
- Endpoint `/ai/analyze-page`: 20 requisições/minuto por usuário
- Endpoint `/exports/*`: 5 requisições/minuto por usuário
- Global: 1000 requisições/hora por IP

### Validação de URL
URLs submetidas para scraping passam por validação:
1. Deve ser HTTP ou HTTPS
2. Não pode ser localhost, 127.x.x.x, 10.x.x.x, 172.16-31.x.x (SSRF protection)
3. Bloqueio de extensões perigosas (.exe, .sh, .bat)
4. Timeout máximo de 60 segundos

### Destinos Bloqueados
Lista de domínios bloqueados mantida em banco:
- Sites governamentais críticos (infraestrutura)
- Sistemas financeiros (BACEN, CVM)
- Domínios na lista de phishing conhecidos

## Conformidade

### Respeito a robots.txt
- `protego` (biblioteca do Scrapy) usado para parse de robots.txt
- Jobs que tentam violar robots.txt são bloqueados por padrão
- Usuário pode desabilitar verificação (registrado em auditoria)

### LGPD (Lei Geral de Proteção de Dados)
- Dados pessoais extraídos são sinalizados automaticamente pela IA
- Retenção máxima de dados configurável (padrão: 90 dias)
- Usuário pode solicitar exclusão de todos os seus dados
- Logs de auditoria retidos por 1 ano (mínimo legal)
- Exportação de dados do usuário disponível (portabilidade)

### Termos de Uso
- Plataforma proibida para:
  - Scraping de dados pessoais sem consentimento
  - Ataques DDoS ou sobrecarga intencional de servidores
  - Violação de CFAA ou leis equivalentes
  - Coleta de dados de menores de idade
  - Atividades fraudulentas ou ilegais

### Política Antiabuso
- Monitoramento de padrões de uso anômalos
- Bloqueio automático de jobs com taxa de erro > 80%
- Notificação ao usuário antes de bloqueio
- Canal de reporte de abuso: abuse@webscrapy.ai (configurar)

## Logs de Auditoria

Todos os eventos críticos são registrados em `audit_log`:
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Eventos auditados:
- Login / logout / falha de login
- Criação, edição, exclusão de jobs
- Execução de scraping (com URL e resultado)
- Chamadas à API NVIDIA (model, tokens, custo)
- Exportações de dados
- Mudanças de configuração
- Desabilitação de robots.txt check

## Controle de Acesso

| Role | Permissões |
|---|---|
| `admin` | Acesso total, gestão de usuários, logs de auditoria globais |
| `user` | CRUD próprios jobs, visualização próprios resultados, exportação |
| `viewer` | Somente leitura de jobs e resultados compartilhados |

## Roadmap de Segurança

- [ ] SSO via OAuth2 (Google, GitHub)
- [ ] 2FA obrigatório para admins
- [ ] Criptografia at-rest para dados sensíveis
- [ ] WAF (Web Application Firewall)
- [ ] Penetration testing anual
- [ ] SOC 2 Type II compliance
