"""
Tool: search_web - Search the web using DuckDuckGo
"""
from duckduckgo_search import DDGS
import os

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for real information using DuckDuckGo.",
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
    """Execute real web search"""
    try:
        results = []
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        with DDGS(proxy=proxy) as ddgs:
            # ddgs.text() returns a generator of results
            # keywords: query string
            # max_results: number of results
            search_gen = ddgs.text(query, max_results=num_results, region="fr-fr")
            
            for r in search_gen:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
                
        return {
            "query": query,
            "num_results": len(results),
            "results": results,
            "source": "DuckDuckGo"
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


def to_event(args: dict, result: dict) -> dict:
    """
    Transform tool call into UI event.
    Returns None to use default tool_call display.
    """
    return None


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
