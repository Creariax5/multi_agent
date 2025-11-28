"""
Edit Artifact Tool - Make targeted modifications to an existing artifact
Supports multiple operations: replace content, insert, delete, update styles
"""

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "edit_artifact",
            "description": """Make targeted edits to an existing HTML artifact WITHOUT rewriting everything.

IMPORTANT RULES:
- NEVER use 'replace' on 'body' - it removes the <head> with CSS styles!
- Use 'append' or 'prepend' on 'body' or 'main' to add sections
- Target specific elements like 'header', 'main', 'section', '#id', etc.
- Use get_artifact() first to see the current structure!

Operations:
- replace: Replace innerHTML of a SPECIFIC element (NOT body!)
- replace_outer: Replace the entire element including its tag
- insert_after: Insert HTML after an element
- insert_before: Insert HTML before an element  
- delete: Remove an element
- set_style: Change CSS properties
- append: Add content at the end of an element
- prepend: Add content at the start of an element
- wrap: Wrap element in a new container
- unwrap: Remove wrapper, keep children
- clear: Empty an element's content

Examples:
- Add section: selector="main", operation="append", content="<section>...</section>"
- Change title: selector="header h1", operation="replace", content="New Title"
- Change color: selector="body", operation="set_style", content="background: blue"
- Replace card: selector=".card:first-child", operation="replace_outer", content="<div class='card'>...</div>"
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to target the element (e.g., '#header', '.nav-link', 'section:first-child')"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "replace_outer", "insert_after", "insert_before", "delete", "set_style", "set_attribute", "append", "prepend", "wrap", "unwrap", "clear"],
                        "description": "The type of edit operation to perform"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new HTML content, CSS styles, or attribute value (not needed for delete/clear/unwrap)"
                    },
                    "attribute": {
                        "type": "string",
                        "description": "Attribute name when using set_attribute operation"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the change for the user"
                    }
                },
                "required": ["selector", "operation", "description"]
            }
        }
    }


def execute(selector: str, operation: str, description: str, content: str = "", attribute: str = "") -> str:
    """Execute an edit operation on the artifact."""
    return f"Edit applied: {description}"


def to_event(args: dict, result: str) -> dict:
    """Convert to UI event that will be processed by the frontend."""
    return {
        "type": "artifact_edit",
        "selector": args.get("selector", ""),
        "operation": args.get("operation", "replace"),
        "content": args.get("content", ""),
        "attribute": args.get("attribute", ""),
        "description": args.get("description", "")
    }
