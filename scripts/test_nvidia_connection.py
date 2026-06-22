"""
Script para testar conexão com todos os modelos NVIDIA NIM.
Execute: python scripts/test_nvidia_connection.py
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

NVIDIA_MODELS = [
    "nvidia/llama-3.3-70b-instruct",
    "nvidia/mistral-nemo-12b-instruct",
    "nvidia/gemma-2-27b-it",
    "nvidia/llama-3.1-8b-instruct",
    "meta/llama-3.1-405b-instruct",
]


async def test_model(model: str, api_key: str, base_url: str) -> dict:
    import httpx
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Responda apenas: OK"}],
                    "max_tokens": 10,
                    "temperature": 0.1,
                },
            )
            latency_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                answer = resp.json()["choices"][0]["message"]["content"]
                return {"model": model, "status": "✅ OK", "latency_ms": latency_ms, "response": answer[:50]}
            else:
                return {"model": model, "status": f"❌ HTTP {resp.status_code}", "latency_ms": latency_ms, "error": resp.text[:200]}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"model": model, "status": f"❌ ERROR", "latency_ms": latency_ms, "error": str(e)[:200]}


async def main():
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    if not api_key:
        print("❌ NVIDIA_API_KEY não configurada.")
        print("   Configure no .env ou exporte: export NVIDIA_API_KEY=nvapi-xxx")
        sys.exit(1)

    print(f"\n🔍 Testando {len(NVIDIA_MODELS)} modelos NVIDIA NIM...")
    print(f"   Base URL: {base_url}\n")

    results = await asyncio.gather(*[
        test_model(m, api_key, base_url) for m in NVIDIA_MODELS
    ])

    available = 0
    for r in results:
        status = r["status"]
        latency = r.get("latency_ms", "?")
        print(f"  {status}  {r['model']:<45} ({latency}ms)")
        if "OK" in status:
            available += 1

    print(f"\n📊 Resultado: {available}/{len(NVIDIA_MODELS)} modelos disponíveis")
    if available > 0:
        print(f"✓ Fallback chain ativa com {available} modelos disponíveis")
    else:
        print("❌ Nenhum modelo disponível — verifique sua NVIDIA_API_KEY")


if __name__ == "__main__":
    asyncio.run(main())
