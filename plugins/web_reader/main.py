import urllib.request
import urllib.parse
import re
import asyncio
from bs4 import BeautifulSoup

def _fetch_jina_reader(url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(jina_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def _fetch_fallback_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        
    soup = BeautifulSoup(html, "html.parser")
    
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()
        
    paragraphs = []
    main_content = soup.find(["article", "main"]) or soup.body
    if not main_content:
        main_content = soup
        
    for p in main_content.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
        text = p.get_text().strip()
        if len(text) > 20:
            paragraphs.append(text)
            
    return "\n\n".join(paragraphs)[:10000]

async def web_reader_parse(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"success": False, "error": "URL không hợp lệ. Phải bắt đầu bằng http:// hoặc https://"}
        
    try:
        content = await asyncio.to_thread(_fetch_jina_reader, url)
        return {
            "success": True,
            "source": "Jina Reader API",
            "url": url,
            "content": content[:8000]
        }
    except Exception as je:
        try:
            content = await asyncio.to_thread(_fetch_fallback_html, url)
            return {
                "success": True,
                "source": "Local BS4 Parser Fallback",
                "url": url,
                "content": content
            }
        except Exception as fe:
            return {
                "success": False,
                "error": f"Lỗi đọc trang web: Jina: {je}, Fallback: {fe}"
            }
