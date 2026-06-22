"""
SchemaValidator — valida schema e tipos de dados scraped.

Suporta:
- Validação de campos obrigatórios
- Validação de tipos: str, int, float, bool, email, url, date_iso, phone, price
- Inferência automática de schema a partir dos dados
- Relatório detalhado de erros e avisos por item
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns de validação por tipo
# ---------------------------------------------------------------------------

_VALIDATORS: dict[str, re.Pattern] = {
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "url": re.compile(r"^https?://[^\s\"'<>]{3,}$"),
    "phone": re.compile(r"^[\+\d\s\-\(\)\.]{7,20}$"),
    "date_iso": re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?"),
    "date_br": re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    "price": re.compile(r"^R?\$?\s*[\d\.,]+$"),
    "cpf": re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$"),
    "cnpj": re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$"),
    "cep": re.compile(r"^\d{5}-?\d{3}$"),
}

# Tipos Python nativos
_PYTHON_TYPES: dict[str, type | tuple] = {
    "str": str,
    "int": int,
    "float": (int, float),
    "bool": bool,
    "list": list,
    "dict": dict,
    "number": (int, float),
}


class SchemaValidator:
    """
    Valida e infere schema de datasets scraped.

    Exemplo de uso
    --------------
    validator = SchemaValidator()

    # Valida contra schema
    result = validator.validate(
        data=[{"nome": "Iris", "email": "iris@ex.com", "preco": "R$ 1.299"}],
        schema={
            "nome": {"type": "str", "required": True},
            "email": {"type": "email", "required": False},
            "preco": {"type": "price", "required": True},
        },
    )

    # Infere schema automaticamente
    inferred = validator.infer_schema(data)
    """

    def validate(self, data: list[dict], schema: dict) -> dict[str, Any]:
        """
        Valida uma lista de itens contra um schema.

        Parâmetros
        ----------
        data : list[dict]
            Itens a validar.
        schema : dict
            Definição do schema: {campo: {type, required, nullable, ...}}
            Tipos suportados: str, int, float, bool, email, url, date_iso,
            date_br, phone, price, cpf, cnpj, cep, list, dict, number.

        Retorno
        -------
        dict com:
            valid_count : int
            invalid_count : int
            errors : list[str]
            warnings : list[str]
            validation_rate : float (0.0–1.0)
            field_stats : dict {campo: {valid, invalid, missing}}
        """
        if not data:
            return {
                "valid_count": 0,
                "invalid_count": 0,
                "errors": ["Dataset vazio."],
                "warnings": [],
                "validation_rate": 0.0,
                "field_stats": {},
            }

        errors: list[str] = []
        warnings: list[str] = []
        valid_count = 0

        # Estatísticas por campo
        field_stats: dict[str, dict] = {
            field: {"valid": 0, "invalid": 0, "missing": 0}
            for field in schema
        }

        for i, item in enumerate(data):
            item_valid = True

            for field, rules in schema.items():
                value = item.get(field)
                required = rules.get("required", False)
                nullable = rules.get("nullable", True)
                field_type = rules.get("type", "str")

                # Campo ausente ou nulo
                if value in (None, "", [], {}):
                    field_stats[field]["missing"] += 1
                    if required and not nullable:
                        errors.append(
                            f"Item {i}: campo obrigatório '{field}' ausente ou nulo."
                        )
                        item_valid = False
                    continue

                # Validação de tipo Python nativo
                if field_type in _PYTHON_TYPES:
                    expected_type = _PYTHON_TYPES[field_type]
                    if not isinstance(value, expected_type):
                        # Tenta coerção para str
                        if field_type == "str":
                            pass  # Tudo pode ser str
                        else:
                            warnings.append(
                                f"Item {i}: campo '{field}' esperado {field_type}, "
                                f"recebido {type(value).__name__}: {str(value)[:50]}"
                            )
                            field_stats[field]["invalid"] += 1
                            continue

                # Validação por pattern regex
                elif field_type in _VALIDATORS:
                    pattern = _VALIDATORS[field_type]
                    val_str = str(value).strip()
                    if not pattern.match(val_str):
                        warnings.append(
                            f"Item {i}: campo '{field}' ({field_type}) com formato inválido: "
                            f"'{val_str[:60]}'"
                        )
                        field_stats[field]["invalid"] += 1
                        continue

                field_stats[field]["valid"] += 1

            if item_valid:
                valid_count += 1

        invalid_count = len(data) - valid_count

        logger.debug(
            "SchemaValidator.validate() | total=%d | válidos=%d | erros=%d",
            len(data), valid_count, len(errors),
        )

        return {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "errors": errors[:100],  # limita para não explodir o payload
            "warnings": warnings[:100],
            "validation_rate": round(valid_count / len(data), 4),
            "field_stats": field_stats,
        }

    def infer_schema(self, data: list[dict]) -> dict[str, dict]:
        """
        Infere schema automaticamente a partir dos dados.

        Detecta:
        - Tipo dominante de cada campo
        - Taxa de preenchimento (fill_rate)
        - Se é obrigatório (fill_rate > 90%)
        - Se é nullable (fill_rate < 100%)
        - Tipo semântico pelo nome do campo (email, url, price, etc.)

        Retorno
        -------
        dict {campo: {type, required, nullable, fill_rate, sample}}
        """
        if not data:
            return {}

        all_keys: set[str] = set()
        for item in data:
            all_keys.update(item.keys())

        schema: dict[str, dict] = {}

        for key in sorted(all_keys):
            values = [
                item.get(key)
                for item in data
                if item.get(key) not in (None, "", [], {})
            ]
            fill_rate = len(values) / len(data)

            # Tipo semântico pelo nome do campo
            type_name = self._infer_type_by_name(key)

            # Se não inferiu pelo nome, infere pelo conteúdo
            if type_name == "str" and values:
                type_name = self._infer_type_by_content(values)

            # Sample de valores (até 3)
            sample = [str(v)[:80] for v in values[:3]]

            schema[key] = {
                "type": type_name,
                "required": fill_rate >= 0.9,
                "nullable": fill_rate < 1.0,
                "fill_rate": round(fill_rate, 3),
                "sample": sample,
            }

        return schema

    def validate_against_inferred(self, data: list[dict]) -> dict[str, Any]:
        """
        Infere schema e valida os dados automaticamente.
        Atalho para infer_schema() + validate().
        """
        schema = self.infer_schema(data)
        return self.validate(data, schema)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_type_by_name(key: str) -> str:
        """Infere tipo semântico pelo nome do campo."""
        key_lower = key.lower()
        rules = [
            (["email", "mail", "e-mail"], "email"),
            (["url", "href", "link", "src", "website", "site"], "url"),
            (["phone", "tel", "telefone", "celular", "mobile"], "phone"),
            (["price", "preco", "valor", "custo", "cost", "amount"], "price"),
            (["date", "data", "created", "updated", "published", "datetime"], "date_iso"),
            (["cpf"], "cpf"),
            (["cnpj"], "cnpj"),
            (["cep", "zipcode", "postal"], "cep"),
            (["count", "total", "quantity", "qtd", "quantidade"], "int"),
            (["rate", "score", "rating", "latitude", "longitude", "lat", "lng"], "float"),
            (["active", "enabled", "available", "ativo", "disponivel"], "bool"),
        ]
        for keys, type_name in rules:
            if any(k in key_lower for k in keys):
                return type_name
        return "str"

    @staticmethod
    def _infer_type_by_content(values: list) -> str:
        """Infere tipo pelo conteúdo dos valores."""
        if all(isinstance(v, bool) for v in values):
            return "bool"
        if all(isinstance(v, int) for v in values):
            return "int"
        if all(isinstance(v, (int, float)) for v in values):
            return "float"
        if all(isinstance(v, list) for v in values):
            return "list"
        if all(isinstance(v, dict) for v in values):
            return "dict"

        # Tenta inferir por conteúdo de strings
        str_values = [str(v).strip() for v in values if isinstance(v, str)]
        if not str_values:
            return "str"

        email_pattern = _VALIDATORS["email"]
        url_pattern = _VALIDATORS["url"]
        date_pattern = _VALIDATORS["date_iso"]

        if sum(1 for v in str_values if email_pattern.match(v)) / len(str_values) > 0.8:
            return "email"
        if sum(1 for v in str_values if url_pattern.match(v)) / len(str_values) > 0.8:
            return "url"
        if sum(1 for v in str_values if date_pattern.match(v)) / len(str_values) > 0.8:
            return "date_iso"

        return "str"
