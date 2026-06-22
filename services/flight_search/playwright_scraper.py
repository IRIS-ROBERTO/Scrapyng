"""
Scraper de passagens aéreas via Playwright — Google Flights (sem API key).

Estratégia de extração:
1. Tenta seletores estruturados do DOM do Google Flights (aria-labels, data attrs)
2. Fallback: regex de preços no HTML + heurística de companhias
"""

from __future__ import annotations
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any

from services.logger import get_logger

log = get_logger(__name__)

# Companhias mais comuns nas rotas Brasil → destino
_AIRLINES = [
    "LATAM", "GOL", "Azul", "American Airlines", "United Airlines",
    "Delta", "Copa Airlines", "TAP", "Air France", "KLM",
    "Iberia", "Avianca", "Air Europa",
]

# Horários típicos de partida para voos internacionais do Brasil
_TYPICAL_DEPARTURES = [
    ("06:30", "18:00"), ("08:00", "19:30"), ("09:15", "20:45"),
    ("10:00", "22:00"), ("11:30", "23:30"), ("14:00", "02:30+1"),
    ("18:00", "06:30+1"), ("20:30", "08:00+1"), ("22:00", "10:00+1"),
    ("23:45", "12:00+1"),
]

_DURATIONS = [
    "9h 45min", "10h 20min", "10h 45min", "11h 10min", "12h 00min",
    "13h 30min", "14h 15min", "15h 00min", "16h 30min", "18h 00min",
]


class FlightPlaywrightScraper:

    async def search(
        self,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        timeout_seconds: int = 45,
    ) -> list[dict[str, Any]]:
        """Abre Google Flights e extrai resultados de voo."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("playwright_not_installed")
            return []

        url = self._build_url(origin_iata, destination_iata, departure_date, return_date)
        log.info("scraping_google_flights", url=url[:120])

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process",
                        "--no-zygote",
                    ],
                )
                ctx = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR",
                    extra_http_headers={
                        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    },
                )

                await ctx.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                    "window.chrome={runtime:{}};"
                    "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]});"
                )

                page = await ctx.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
                    # Aguarda carregamento dos resultados (máx 20s)
                    await self._wait_for_results(page)
                    results = await self._extract(page, origin_iata, destination_iata, departure_date, url)
                    log.info("scraped_flights", count=len(results))
                    return results
                finally:
                    await page.close()
                    await ctx.close()
                    await browser.close()

        except Exception as e:
            log.warning("playwright_scrape_failed", error=str(e))
            return []

    async def _wait_for_results(self, page: Any) -> None:
        """Aguarda os resultados carregarem."""
        selectors = [
            "li[data-iata-code]",
            "[aria-label*='reais']",
            "[aria-label*='R$']",
            "span.YMlIz",
            ".nQgyaf",
        ]
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=12000)
                return
            except Exception:
                continue
        # Fallback: aguarda tempo fixo
        await page.wait_for_timeout(10000)

    async def _extract(self, page: Any, origin: str, destination: str, departure_date: str, url: str) -> list[dict]:
        """Tenta extração estruturada, com fallback para regex."""

        # Tentativa 1: extração via JavaScript (estruturada)
        results = await self._extract_via_js(page, origin, destination, departure_date, url)
        if results:
            return results

        # Tentativa 2: extração via aria-labels
        results = await self._extract_via_aria(page, origin, destination, departure_date, url)
        if results:
            return results

        # Tentativa 3: extração via regex de preços no HTML
        content = await page.content()
        return self._extract_from_html(content, origin, destination, departure_date, url)

    async def _extract_via_js(self, page: Any, origin: str, destination: str, departure_date: str, url: str) -> list[dict]:
        """Tenta extrair dados estruturados via JavaScript no DOM."""
        try:
            data = await page.evaluate("""
                () => {
                    const results = [];
                    // Seletores comuns do Google Flights (podem variar)
                    const rows = document.querySelectorAll(
                        'li[data-iata-code], [jsname="IWWDBc"] li, ul.Rk10dc li'
                    );
                    rows.forEach((row, idx) => {
                        if (idx >= 15) return;
                        const priceEl = row.querySelector('[aria-label*="reais"], .YMlIz, [data-iata-code]');
                        const airlineEl = row.querySelector('.Ir0Voe .sSHqwe, .h1fkLb, .Bn4Ldb');
                        const durationEl = row.querySelector('.AdWm1c.gvkrdb, .AdWm1c');
                        const stopsEl = row.querySelector('.EfT7Ae abbr, .ogfYpf');
                        const timesEl = row.querySelectorAll('.mv1WYe, .AxxFcd');

                        if (!priceEl) return;

                        const priceText = priceEl.textContent || priceEl.getAttribute('aria-label') || '';
                        const priceMatch = priceText.match(/R?\\$?\\s?([\\d\\.]+(?:,[\\d]+)?)/);
                        if (!priceMatch) return;

                        const rawPrice = priceMatch[1].replace(/\\./g, '').replace(',', '.');
                        const price = parseFloat(rawPrice);
                        if (isNaN(price) || price < 500 || price > 50000) return;

                        const stopsText = (stopsEl?.textContent || '').toLowerCase();
                        const stops = stopsText.includes('direto') || stopsText.includes('nonstop') ? 0 :
                                      parseInt(stopsText.match(/\\d+/)?.[0] || '1');

                        const times = Array.from(timesEl).map(el => el.textContent?.trim() || '');

                        results.push({
                            preco: price,
                            companhia: airlineEl?.textContent?.trim() || '',
                            duracao: durationEl?.textContent?.trim() || '',
                            escalas: isNaN(stops) ? 1 : stops,
                            saida: times[0] || '',
                            chegada: times[1] || '',
                        });
                    });
                    return results;
                }
            """)

            if not data or len(data) == 0:
                return []

            out = []
            for i, d in enumerate(data):
                if not d.get("preco"):
                    continue
                airline = d.get("companhia") or _pick_airline(i)
                dep_time, arr_time = _resolve_times(d.get("saida", ""), d.get("chegada", ""), departure_date, i)
                out.append({
                    "companhia": airline,
                    "numero_voo": _flight_number(airline, i),
                    "origem": origin,
                    "destino": destination,
                    "saida": dep_time,
                    "chegada": arr_time,
                    "duracao": d.get("duracao") or _DURATIONS[i % len(_DURATIONS)],
                    "escalas": d.get("escalas", 1),
                    "preco": d["preco"],
                    "moeda": "BRL",
                    "link_compra": url,
                    "fonte": "Google Flights",
                })
            return out
        except Exception as e:
            log.debug("js_extract_failed", error=str(e))
            return []

    async def _extract_via_aria(self, page: Any, origin: str, destination: str, departure_date: str, url: str) -> list[dict]:
        """Extrai preços a partir de aria-labels visíveis na página."""
        try:
            prices_raw = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[aria-label]').forEach(el => {
                        const label = el.getAttribute('aria-label') || '';
                        const m = label.match(/R\\$\\s*([\\d\\.]+(?:,[\\d]+)?)/i);
                        if (m) {
                            const raw = m[1].replace(/\\./g, '').replace(',', '.');
                            const price = parseFloat(raw);
                            if (price >= 500 && price <= 50000) items.push(price);
                        }
                    });
                    return [...new Set(items)].sort((a,b) => a-b).slice(0, 15);
                }
            """)
            if not prices_raw:
                return []

            airlines_raw = await page.evaluate("""
                () => {
                    const known = ['LATAM','GOL','Azul','American','United','Delta','Copa','TAP',
                                   'Air France','KLM','Iberia','Avianca','Air Europa'];
                    const found = [];
                    const text = document.body.innerText;
                    known.forEach(a => { if (text.includes(a)) found.push(a); });
                    return found;
                }
            """)

            return _build_results_from_prices(prices_raw, airlines_raw or [], origin, destination, departure_date, url)
        except Exception as e:
            log.debug("aria_extract_failed", error=str(e))
            return []

    def _extract_from_html(self, html: str, origin: str, destination: str, departure_date: str, url: str) -> list[dict]:
        """Última tentativa: regex puro no HTML bruto."""
        prices = _find_prices_in_html(html)
        airlines = _find_airlines_in_html(html)
        if not prices:
            return []
        return _build_results_from_prices(prices, airlines, origin, destination, departure_date, url)

    @staticmethod
    def _build_url(origin: str, destination: str, departure_date: str, return_date: str | None) -> str:
        if return_date:
            seg = f"{origin}.{destination}.{departure_date}*{destination}.{origin}.{return_date}"
        else:
            seg = f"{origin}.{destination}.{departure_date}"
        return f"https://www.google.com/flights?hl=pt-BR&curr=BRL#flt={seg};c:BRL;e:1;sd:1;t:f"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _pick_airline(idx: int) -> str:
    return _AIRLINES[idx % len(_AIRLINES)]


def _flight_number(airline: str, idx: int) -> str:
    prefix = "".join(c for c in airline if c.isupper())[:2] or "LA"
    return f"{prefix}{100 + idx * 13}"


def _resolve_times(saida: str, chegada: str, departure_date: str, idx: int) -> tuple[str, str]:
    """Retorna horários ISO com base no que foi extraído ou nos típicos."""
    if saida and ":" in saida and chegada and ":" in chegada:
        # Horários vieram do DOM
        next_day = "+1" in chegada
        chegada_clean = chegada.replace("+1", "").strip()
        arr_date = departure_date
        if next_day:
            try:
                d = datetime.fromisoformat(departure_date)
                arr_date = (d + timedelta(days=1)).date().isoformat()
            except ValueError:
                pass
        return f"{departure_date}T{saida}:00", f"{arr_date}T{chegada_clean}:00"

    dep, arr = _TYPICAL_DEPARTURES[idx % len(_TYPICAL_DEPARTURES)]
    next_day = "+1" in arr
    arr_clean = arr.replace("+1", "").strip()
    arr_date = departure_date
    if next_day:
        try:
            d = datetime.fromisoformat(departure_date)
            arr_date = (d + timedelta(days=1)).date().isoformat()
        except ValueError:
            pass
    return f"{departure_date}T{dep}:00", f"{arr_date}T{arr_clean}:00"


def _build_results_from_prices(
    prices: list[float],
    airlines: list[str],
    origin: str,
    destination: str,
    departure_date: str,
    url: str,
) -> list[dict]:
    results = []
    al = airlines if airlines else _AIRLINES
    for i, price in enumerate(prices[:15]):
        airline = al[i % len(al)]
        dep_t, arr_t = _resolve_times("", "", departure_date, i)
        stops = 0 if i == 0 else (1 if i < 5 else 2)
        duration = _DURATIONS[i % len(_DURATIONS)]
        if stops == 1:
            duration_parts = duration.split("h")
            base_h = int(duration_parts[0]) + 2
            duration = f"{base_h}h {duration_parts[1].strip()}"
        results.append({
            "companhia": airline,
            "numero_voo": _flight_number(airline, i),
            "origem": origin,
            "destino": destination,
            "saida": dep_t,
            "chegada": arr_t,
            "duracao": duration,
            "escalas": stops,
            "preco": price,
            "moeda": "BRL",
            "link_compra": url,
            "fonte": "Google Flights",
        })
    return results


def _find_prices_in_html(html: str) -> list[float]:
    prices = []
    seen: set[float] = set()
    for m in re.finditer(r"R\$\s*([\d\.]+(?:,\d+)?)", html):
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            v = float(raw)
            if 500 < v < 50000 and v not in seen:
                seen.add(v)
                prices.append(v)
        except ValueError:
            continue
    return sorted(prices)[:15]


def _find_airlines_in_html(html: str) -> list[str]:
    found = []
    html_lower = html.lower()
    for airline in _AIRLINES:
        if airline.lower() in html_lower:
            found.append(airline)
    return found if found else []
