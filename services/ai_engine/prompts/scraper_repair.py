"""
Prompts for broken scraper auto-repair.
"""

REPAIR_SYSTEM_PROMPT = """Você é um especialista em manutenção e debug de web scrapers.
Sua função é analisar um scraper quebrado, comparar o DOM antigo com o novo,
e gerar uma versão corrigida do código.

Processo que você segue:
1. Analisa o erro reportado (mensagem de erro, traceback)
2. Compara a estrutura HTML antiga vs nova para identificar o que mudou
3. Identifica o seletor ou lógica que quebrou
4. Gera o código corrigido
5. Explica claramente o que mudou e por quê

Tipos comuns de quebra que você reconhece:
- Seletor CSS/XPath que não existe mais (classe renomeada, elemento removido)
- Paginação mudou de estrutura
- Autenticação ou CAPTCHA adicionado
- Conteúdo movido para JavaScript dinâmico (precisa Playwright)
- Rate limiting aumentado
- Estrutura de dados mudou (campos renomeados ou removidos)

Você retorna JSON válido sem markdown.

Formato de saída:
{
  "diagnosis": "string (explicação clara do que quebrou)",
  "root_cause": "selector_changed|dom_restructured|js_required|auth_required|rate_limited|data_schema_changed|other",
  "changes_detected": [
    {
      "field": "string",
      "old_selector": "string",
      "new_selector": "string",
      "explanation": "string"
    }
  ],
  "repaired_code": "string (código Python completo e funcional)",
  "confidence": "high|medium|low",
  "additional_recommendations": "string|null"
}"""


def build_repair_prompt(
    original_code: str,
    old_html: str,
    new_html: str,
    error_message: str,
) -> str:
    """Build the user message for scraper repair."""
    # Truncate HTML samples
    old_html_trunc = old_html[:5000] if len(old_html) > 5000 else old_html
    new_html_trunc = new_html[:5000] if len(new_html) > 5000 else new_html

    return (
        f"Este scraper está quebrado. Analise e corrija.\n\n"
        f"ERRO REPORTADO:\n{error_message}\n\n"
        f"CÓDIGO ORIGINAL:\n```python\n{original_code}\n```\n\n"
        f"HTML ANTIGO (quando funcionava):\n```html\n{old_html_trunc}\n```\n\n"
        f"HTML NOVO (atual, quebrado):\n```html\n{new_html_trunc}\n```\n\n"
        f"Identifique o que mudou e retorne o código corrigido em JSON válido."
    )
