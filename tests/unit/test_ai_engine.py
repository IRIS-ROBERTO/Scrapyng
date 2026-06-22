"""
Testes unitários do AI Engine com NVIDIA API mockada.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Adiciona o root ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestNvidiaClientFallback:
    """Testa a cadeia de fallback do cliente NVIDIA."""

    @pytest.mark.asyncio
    async def test_fallback_to_second_model_on_failure(self):
        """Se o modelo primário falhar, deve tentar o segundo."""
        from services.ai_engine.nvidia_client import NvidiaClient

        client = NvidiaClient(api_key="test-key")
        call_count = {"n": 0}

        async def mock_call_model(model, messages, max_tokens, temperature):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("Model temporarily unavailable")
            return "Resposta do segundo modelo"

        client._call_model = mock_call_model
        result = await client.chat([{"role": "user", "content": "teste"}])
        assert result == "Resposta do segundo modelo"
        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_raises_after_all_models_fail(self):
        """Se todos os modelos falharem, deve lançar RuntimeError."""
        from services.ai_engine.nvidia_client import NvidiaClient

        client = NvidiaClient(api_key="test-key")

        async def mock_call_model(*args, **kwargs):
            raise Exception("All down")

        client._call_model = mock_call_model
        with pytest.raises(RuntimeError, match="Todos os modelos NVIDIA falharam"):
            await client.chat([{"role": "user", "content": "teste"}])

    @pytest.mark.asyncio
    async def test_chat_json_parses_valid_json(self):
        """chat_json deve retornar dict a partir de resposta JSON válida."""
        from services.ai_engine.nvidia_client import NvidiaClient

        client = NvidiaClient(api_key="test-key")
        client.chat = AsyncMock(return_value='{"result": "ok", "score": 95}')

        result = await client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"result": "ok", "score": 95}

    @pytest.mark.asyncio
    async def test_chat_json_strips_markdown_code_blocks(self):
        """chat_json deve remover blocos de código markdown."""
        from services.ai_engine.nvidia_client import NvidiaClient

        client = NvidiaClient(api_key="test-key")
        client.chat = AsyncMock(return_value='```json\n{"result": "ok"}\n```')

        result = await client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"result": "ok"}


class TestSearchIntelligence:
    """Testa o módulo de busca especializada por tipo."""

    @pytest.mark.asyncio
    async def test_detect_flight_search_type(self):
        """Detecta busca de passagens aéreas corretamente."""
        from services.ai_engine.search_intelligence import SearchIntelligence

        intel = SearchIntelligence(nvidia_client=MagicMock())
        intel.nvidia_client.chat = AsyncMock(return_value="flights")
        search_type = await intel.detect_search_type(
            url="https://www.kayak.com.br/flights/GRU-LIS",
            context="passagens aéreas Lisboa",
        )
        assert search_type == "flights"

    @pytest.mark.asyncio
    async def test_detect_jobs_search_type(self):
        """Detecta busca de vagas de emprego."""
        from services.ai_engine.search_intelligence import SearchIntelligence

        intel = SearchIntelligence(nvidia_client=MagicMock())
        intel.nvidia_client.chat = AsyncMock(return_value="jobs")
        search_type = await intel.detect_search_type(
            url="https://www.linkedin.com/jobs/search?keywords=Python",
            context="vagas desenvolvedor Python",
        )
        assert search_type == "jobs"


class TestDataQuality:
    """Testa o engine de qualidade de dados."""

    def test_score_complete_data(self):
        """Dados completos devem ter score alto."""
        from services.data_quality_engine.quality_score import QualityScorer

        scorer = QualityScorer()
        data = [
            {"name": "Empresa A", "email": "contact@empresa.com", "phone": "+55 11 9999-9999"},
            {"name": "Empresa B", "email": "info@empresa.com", "phone": "+55 21 8888-8888"},
        ]
        result = scorer.score(data)
        assert result["score"] >= 70
        assert "issues" in result
        assert "recommendations" in result

    def test_score_incomplete_data(self):
        """Dados com muitos campos vazios devem ter score baixo."""
        from services.data_quality_engine.quality_score import QualityScorer

        scorer = QualityScorer()
        data = [
            {"name": "", "email": None, "phone": ""},
            {"name": None, "email": "", "phone": None},
        ]
        result = scorer.score(data)
        assert result["score"] < 40

    def test_duplicate_detection(self):
        """Duplicatas exatas devem ser detectadas."""
        from services.data_quality_engine.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        data = [
            {"name": "Empresa X", "email": "x@x.com"},
            {"name": "Empresa X", "email": "x@x.com"},  # duplicata
            {"name": "Empresa Y", "email": "y@y.com"},
        ]
        result = detector.detect(data)
        assert result["duplicates_count"] == 1
        assert result["unique_count"] == 2


class TestExportEngine:
    """Testa exportações de dados."""

    def test_csv_export_returns_string(self, tmp_path):
        """CSV exporter deve gerar string CSV válida."""
        from services.export_engine.csv_exporter import CSVExporter

        exporter = CSVExporter()
        data = [
            {"name": "Voo 1", "price": "R$ 1.200", "airline": "LATAM"},
            {"name": "Voo 2", "price": "R$ 900", "airline": "GOL"},
        ]
        output = exporter.export(data, filename=str(tmp_path / "test.csv"))
        assert output.endswith(".csv")

    def test_json_export_valid_json(self):
        """JSON exporter deve gerar JSON válido."""
        from services.export_engine.json_exporter import JSONExporter

        exporter = JSONExporter()
        data = [{"title": "Notícia 1", "source": "G1"}, {"title": "Notícia 2", "source": "UOL"}]
        output = exporter.export_string(data)
        parsed = json.loads(output)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Notícia 1"
