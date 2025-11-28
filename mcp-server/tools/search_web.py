"""
Tool: search_web - Search the web using DuckDuckGo or Google fallback
"""
from ddgs import DDGS
from googlesearch import search as google_search
import os

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for real information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    }


def execute(query: str, num_results: int = 5) -> dict:
    """Execute real web search with fallback"""
    results = []
    source = "DuckDuckGo"
    
    # Try DuckDuckGo first
    try:
        with DDGS() as ddgs:
            # Use 'lite' backend which is often more robust against proxy geo-issues
            # and force 'fr-fr' region
            search_gen = ddgs.text(query, max_results=num_results, region="fr-fr", backend="lite")
            
            for r in search_gen:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
                
        # Check if results are garbage (Chinese characters in title for a French query)
        # Heuristic: if query is not Chinese but results are
        if results and any("\u4e00" <= c <= "\u9fff" for c in results[0]["title"]):
            print("Detected irrelevant Chinese results, switching to fallback...")
            raise Exception("Irrelevant results detected")
            
    except Exception as e:
        print(f"DuckDuckGo failed or returned bad results: {e}")
        # Fallback to Google Search (scraper)
        try:
            source = "Google"
            results = []
            # googlesearch-python simple search returns URLs only
            # Try to get more results to ensure we have some
            # Note: googlesearch-python might fail silently or return empty generator if blocked
            print("Attempting Google fallback...")
            g_results = google_search(query, num_results=num_results, lang="fr")
            for url in g_results:
                results.append({
                    "title": "Result from Google",
                    "url": url,
                    "snippet": "No snippet available (Google fallback)"
                })
            
            if not results:
                print("Google returned 0 results.")
                raise Exception("No results from Google")
                
        except Exception as e2:
            print(f"Google fallback failed: {e2}")
            # Final fallback: Try DDG again but with 'wt-wt' region (World) as a last resort
            # Maybe the Chinese results are specific to 'fr-fr' + proxy combo?
            try:
                print("Attempting DDG World fallback...")
                source = "DuckDuckGo (World)"
                with DDGS() as ddgs:
                    search_gen = ddgs.text(query, max_results=num_results, region="wt-wt", backend="html")
                    for r in search_gen:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")
                        })
            except Exception as e3:
                return {"error": f"All search methods failed. DDG: {e}, Google: {e2}, DDG-World: {e3}"}

    return {
        "query": query,
        "num_results": len(results),
        "results": results,
        "source": source
    }


def to_event(args: dict, result: dict) -> dict:
    """
    Transform tool call into UI event.
    Returns None to use default tool_call display.
    """
    return None


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
