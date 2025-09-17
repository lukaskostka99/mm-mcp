from typing import Any, Optional, Dict
import os
import httpx
from mcp.server.fastmcp import FastMCP

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Inicializace FastMCP serveru. Host/Port se nastaví až při spuštění Uvicornu.
mcp = FastMCP("marketing-miner")

# --- Konstanty a API ---
API_BASE = "https://profilers-api.marketingminer.com"
SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s patřičným ošetřením chyb"""
    api_token = os.getenv("MM_API_TOKEN")
    if not api_token:
        print("ERROR: MM_API_TOKEN is not set!")
        return {
            "status": "error",
            "message": "Chybí konfigurace API tokenu. Nastavte proměnnou prostředí MM_API_TOKEN."
        }
        
    async with httpx.AsyncClient() as client:
        try:
            params["api_token"] = api_token
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_message = f"Chyba při volání Marketing Miner API: {str(e)}"
            print(f"ERROR: {error_message}")
            return {"status": "error", "message": error_message}

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
    # Smithery poskytuje port v proměnných SMITHERY_PORT nebo PORT.
    port_str = os.getenv("SMITHERY_PORT") or os.getenv("PORT") or "8081"
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 8081
    
    # V kontejneru vždy nasloucháme na 0.0.0.0
    host = "0.0.0.0"

    print(f"Preparing Marketing Miner MCP ASGI app for {host}:{port}")

    # Získáme ASGI aplikaci z FastMCP
    sse_app_candidate = getattr(mcp, "sse_app", None) or getattr(mcp, "app", None)
    if callable(sse_app_candidate):
        sse_app = sse_app_candidate()
    else:
        sse_app = sse_app_candidate

    if sse_app is None:
        print("Fatal: Could not get ASGI app from FastMCP. Cannot start server.")
    else:
        try:
            from starlette.applications import Starlette
            from starlette.routing import Mount, Route
            from starlette.responses import JSONResponse
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware
            
            async def health_check(request):
                """Jednoduchý health check endpoint pro Smithery."""
                return JSONResponse({"status": "ok"})

            # Sestavení finální, robustní ASGI aplikace
            asgi_app = Starlette(
                routes=[
                    Mount("/mcp", app=sse_app),
                    Route("/health", endpoint=health_check, methods=["GET", "HEAD"]),
                ],
                middleware=[
                    Middleware(
                        CORSMiddleware,
                        allow_origins=["*"],
                        allow_methods=["GET", "POST", "OPTIONS"],
                        allow_headers=["*"],
                        allow_credentials=True,
                        expose_headers=["mcp-session-id", "mcp-protocol-version"],
                    ),
                ],
            )
            
            import uvicorn
            print(f"Starting Uvicorn server on {host}:{port}")
            uvicorn.run(asgi_app, host=host, port=port, log_level="info")

        except ImportError:
            print("Fatal: Starlette or Uvicorn not found. Please check requirements.txt.")