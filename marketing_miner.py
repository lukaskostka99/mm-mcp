from typing import Any, Optional, Dict
import os
import json
import base64
from urllib.parse import parse_qs
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass
import httpx
from mcp.server.fastmcp import FastMCP

# Inicializace FastMCP serveru
mcp = FastMCP("marketing-miner")

# Konstanty a konfigurace
API_BASE = "https://profilers-api.marketingminer.com"
# API token je načítán z proměnné prostředí MM_API_TOKEN (kvůli bezpečnému nasazení na Smithery)
API_TOKEN = os.getenv("MM_API_TOKEN")

# Typy suggestions
SUGGESTIONS_TYPES = ["questions", "new", "trending"]

# Dostupné jazyky
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s patřičným ošetřením chyb"""
    async with httpx.AsyncClient() as client:
        try:
            # Ověříme přítomnost API tokenu v konfiguraci
            if not API_TOKEN:
                return {
                    "status": "error",
                    "message": "Chybí konfigurace API tokenu. Nastavte proměnnou prostředí MM_API_TOKEN."
                }
            # Přidáme API token do parametrů
            params["api_token"] = API_TOKEN
            
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"Chyba při volání Marketing Miner API: {str(e)}"}

@mcp.tool()
async def get_keyword_suggestions(
    lang: str, 
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False
) -> str:
    """
    Získá návrhy klíčových slov z Marketing Miner API.
    
    Args:
        lang: Kód jazyka (cs, sk, pl, hu, ro, gb, us)
        keyword: Klíčové slovo pro vyhledávání návrhů
        suggestions_type: Volitelný typ návrhů (questions, new, trending)
        with_keyword_data: Zda zahrnout rozšířená data o klíčových slovech
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    if suggestions_type and suggestions_type not in SUGGESTIONS_TYPES:
        return f"Nepodporovaný typ návrhů: {suggestions_type}. Podporované typy jsou: {', '.join(SUGGESTIONS_TYPES)}"
    
    url = f"{API_BASE}/keywords/suggestions"
    
    params = {
        "lang": lang,
        "keyword": keyword
    }
    
    if suggestions_type:
        params["suggestions_type"] = suggestions_type
    
    if with_keyword_data is not None:
        params["with_keyword_data"] = str(with_keyword_data).lower()
    
    response_data = await make_mm_request(url, params)
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    # Zpracování úspěšné odpovědi
    if response_data.get("status") == "success":
        # Upravený kód - správně přistupujeme k datové struktuře
        data = response_data.get("data", {}).get("keywords", [])
        
        if not data:
            return "Nebyla nalezena žádná data pro tento dotaz."
        
        result = []
        for keyword_data in data:
            # Ověřujeme, že keyword_data je slovník
            if not isinstance(keyword_data, dict):
                continue
                
            keyword_info = [f"Klíčové slovo: {keyword_data.get('keyword', 'N/A')}"]
            
            if "search_volume" in keyword_data:
                keyword_info.append(f"Hledanost: {keyword_data.get('search_volume', 'N/A')}")
            
            if "cpc" in keyword_data and keyword_data.get("cpc"):
                cpc = keyword_data.get("cpc", {})
                keyword_info.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
            
            if "difficulty" in keyword_data and with_keyword_data:
                keyword_info.append(f"Obtížnost: {keyword_data.get('difficulty', 'N/A')}")
            
            if "serp_features" in keyword_data and with_keyword_data and keyword_data.get("serp_features"):
                features = ", ".join(keyword_data.get("serp_features", []))
                keyword_info.append(f"SERP features: {features}")
            
            result.append(" | ".join(keyword_info))
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

@mcp.tool()
async def get_search_volume_data(
    lang: str, 
    keyword: str
) -> str:
    """
    Získá data o hledanosti klíčového slova z Marketing Miner API.
    
    Args:
        lang: Kód jazyka (cs, sk, pl, hu, ro, gb, us)
        keyword: Klíčové slovo pro vyhledání dat o hledanosti
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    url = f"{API_BASE}/keywords/search-volume-data"
    
    params = {
        "lang": lang,
        "keyword": keyword
    }
    
    response_data = await make_mm_request(url, params)
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    # Zpracování úspěšné odpovědi
    if response_data.get("status") == "success":
        data = response_data.get("data", [])
        
        if not data or len(data) == 0:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        
        # Vezmeme první výsledek (při GET requestu by měl být jen jeden)
        keyword_data = data[0]
        
        result = [
            f"Klíčové slovo: {keyword_data.get('keyword', 'N/A')}",
            f"Hledanost: {keyword_data.get('search_volume', 'N/A')}"
        ]
        
        if "cpc" in keyword_data and keyword_data.get("cpc"):
            cpc = keyword_data.get("cpc", {})
            result.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        
        if "yoy_change" in keyword_data:
            yoy = keyword_data.get("yoy_change")
            if yoy is not None:
                result.append(f"Meziroční změna: {yoy * 100:.2f}%")
        
        if "peak_month" in keyword_data and keyword_data.get("peak_month"):
            result.append(f"Nejsilnější měsíc: {keyword_data.get('peak_month')}")
        
        if "monthly_sv" in keyword_data and keyword_data.get("monthly_sv"):
            monthly_data = keyword_data.get("monthly_sv", {})
            monthly_result = ["Měsíční hledanost:"]
            
            for month, volume in monthly_data.items():
                monthly_result.append(f"  - Měsíc {month}: {volume}")
            
            result.extend(monthly_result)
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port_str = os.getenv("PORT") or os.getenv("SMITHERY_PORT") or "8000"
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 8000
    
    print(f"Preparing Marketing Miner MCP on {host}:{port}")

    sse_app_candidate = getattr(mcp, "sse_app", None) or getattr(mcp, "app", None)
    if callable(sse_app_candidate):
        try:
            sse_app = sse_app_candidate()
        except TypeError:
            sse_app = None
    else:
        sse_app = sse_app_candidate

    if sse_app is None:
        print("Running in STDIO fallback mode.")
        mcp.run(transport="stdio")
    else:
        try:
            from starlette.applications import Starlette
            from starlette.routing import Mount
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware

            class SmitheryConfigMiddleware:
                def __init__(self, app):
                    self.app = app

                async def __call__(self, scope, receive, send):
                    if scope["type"] == "http":
                        qs = scope.get("query_string", b"").decode()
                        params = parse_qs(qs)
                        config_b64 = params.get("config", [None])[0]
                        
                        if config_b64:
                            try:
                                # Správné ošetření paddingu pro base64
                                missing_padding = len(config_b64) % 4
                                if missing_padding:
                                    config_b64 += '=' * (4 - missing_padding)
                                decoded_config = base64.urlsafe_b64decode(config_b64).decode()
                                config_data = json.loads(decoded_config)
                                if config_data.get("MM_API_TOKEN"):
                                    os.environ["MM_API_TOKEN"] = config_data["MM_API_TOKEN"]
                                    # Aktualizujeme globální proměnnou
                                    globals()["API_TOKEN"] = config_data["MM_API_TOKEN"]
                            except Exception as e:
                                print(f"Error decoding config: {e}")
                    
                    await self.app(scope, receive, send)

            # Sestavení ASGI aplikace s CORS a konfiguračním middlewarem
            asgi_app = Starlette(
                routes=[
                    Mount("/mcp", app=sse_app),
                    Mount("/", app=sse_app), 
                ],
                middleware=[
                    Middleware(SmitheryConfigMiddleware),
                    Middleware(
                        CORSMiddleware,
                        allow_origins=["*"],
                        allow_methods=["GET", "POST", "OPTIONS"],
                        allow_headers=["*"],
                    ),
                ],
            )
            
            import uvicorn
            print(f"Starting Uvicorn server on {host}:{port}")
            uvicorn.run(asgi_app, host=host, port=port, log_level="info")

        except ImportError:
            print("Starlette or Uvicorn not found. Running in STDIO fallback mode.")
            mcp.run(transport="stdio")