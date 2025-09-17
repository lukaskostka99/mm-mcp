from typing import Any, Optional, Dict
import os
import httpx
from mcp.server.fastmcp import FastMCP

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Konfigurace serveru ---
PORT_STR = os.getenv("SMITHERY_PORT") or os.getenv("PORT") or "8081"
try:
    PORT = int(PORT_STR)
except (ValueError, TypeError):
    PORT = 8081
HOST = "0.0.0.0"

print(f"Initializing Marketing Miner MCP for {HOST}:{PORT}")
mcp = FastMCP("marketing-miner", host=HOST, port=PORT)

# --- Konstanty a API ---
API_BASE = "https://profilers-api.marketingminer.com"
SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s robustním logováním."""
    print("[DEBUG] Entering make_mm_request...")
    api_token = os.getenv("MM_API_TOKEN")
    
    if not api_token:
        print("[ERROR] MM_API_TOKEN is not set or empty in environment!")
        return {
            "status": "error",
            "message": "Chyba: MM_API_TOKEN není nastaven v prostředí serveru."
        }
    
    # Pro bezpečnostní logování zobrazíme jen část tokenu
    print(f"[DEBUG] Using API Token ending with '...{api_token[-4:]}'")
    
    async with httpx.AsyncClient() as client:
        try:
            params["api_token"] = api_token
            print(f"[DEBUG] Making request to: {url} with params: {params}")
            
            response = await client.get(url, params=params, timeout=30.0)
            print(f"[DEBUG] Received response with status code: {response.status_code}")
            
            response.raise_for_status()
            
            response_data = response.json()
            print("[DEBUG] Request successful, returning JSON data.")
            return response_data
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP chyba: {e.response.status_code} - {e.response.text}"
            print(f"[ERROR] {error_message}")
            return {"status": "error", "message": error_message}
        except Exception as e:
            error_message = f"Obecná chyba při volání API: {str(e)}"
            print(f"[ERROR] {error_message}")
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
    print(f"Starting Marketing Miner MCP server with SSE transport on {HOST}:{PORT}...")
    mcp.run(transport="sse")