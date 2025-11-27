"""
Tool: search_web - Search the web (simulated)
"""


def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web (simulated)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "default": 3}
                },
                "required": ["query"]
            }
        }
    }


def execute(query: str, num_results: int = 3) -> dict:
    """Return simulated search results"""
    results = [
        {
            "title": f"Result {i+1} for: {query}",
            "url": f"https://example.com/search/{query.replace(' ', '-')}/{i+1}",
            "snippet": f"This is a simulated search result #{i+1} for the query '{query}'."
        }
        for i in range(min(num_results, 5))
    ]
    
    return {
        "query": query,
        "num_results": len(results),
        "results": results,
        "note": "Simulated results"
    }
