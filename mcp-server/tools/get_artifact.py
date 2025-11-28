"""
Get Artifact Tool - Read the current state of an artifact before editing
Solves the "editing blind" problem by providing context
"""

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "get_artifact",
            "description": """Get the current HTML content of the active artifact.

USE THIS BEFORE edit_artifact to:
- See the current structure of the page
- Find the correct CSS selectors
- Understand what elements exist
- Avoid duplicate content or broken edits

Returns the full HTML or a specific section if selector is provided.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector to get only a specific element's HTML. Leave empty for full document."
                    },
                    "include_styles": {
                        "type": "boolean",
                        "description": "Whether to include <style> content in the response. Default: false"
                    }
                },
                "required": []
            }
        }
    }


def execute(selector: str = "", include_styles: bool = False) -> str:
    """Request artifact content from the frontend."""
    return "Requesting artifact content..."


def to_event(args: dict, result: str) -> dict:
    """Convert to UI event that requests current artifact state."""
    return {
        "type": "get_artifact",
        "selector": args.get("selector", ""),
        "include_styles": args.get("include_styles", False)
    }
