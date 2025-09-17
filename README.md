# Marketing Miner MCP

Minimalistický MCP server (FastMCP) pro Marketing Miner API, připravený pro nasazení na Smithery.

## Běh lokálně

1. Vytvořte a naplňte `.env` podle `.env.example` (zejména `MM_API_TOKEN`).
2. Nainstalujte závislosti:

```bash
pip install -r requirements.txt
```

3. Spusťte server (SSE transport je výchozí):

```bash
python marketing_miner.py
```

Server poběží na `HOST:PORT` (výchozí `0.0.0.0:8000`).

## Nasazení na Smithery

- Nastavte proměnné prostředí: `MM_API_TOKEN` (povinné), volitelně `HOST`, `PORT`, `TRANSPORT` (`sse`).
- Spouštěcí příkaz: `python marketing_miner.py`.

## Nástroje

- `get_keyword_suggestions(lang, keyword, suggestions_type?, with_keyword_data?)`
- `get_search_volume_data(lang, keyword)`
