"""
Edit Artifact Tool - Make targeted modifications to an existing artifact
Supports multiple operations: replace content, insert, delete, update styles
"""

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "edit_artifact",
            "description": """Make targeted edits to an existing artifact WITHOUT rewriting everything.
Use this to modify specific parts of an HTML artifact.

Operations:
- replace: Replace the innerHTML of an element matching the selector
- insert_after: Insert HTML after an element
- insert_before: Insert HTML before an element  
- delete: Remove an element
- set_style: Change CSS properties of an element
- set_attribute: Change an attribute of an element
- append: Append content inside an element (at the end)
- prepend: Prepend content inside an element (at the start)

Examples:
- Change header text: selector="#header h1", operation="replace", content="New Title"
- Add new section: selector="#about", operation="insert_after", content="<section id='contact'>...</section>"
- Change background: selector="body", operation="set_style", content="background: #f0f0f0"
- Delete element: selector="#old-section", operation="delete"
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
                        "enum": ["replace", "insert_after", "insert_before", "delete", "set_style", "set_attribute", "append", "prepend"],
                        "description": "The type of edit operation to perform"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new HTML content, CSS styles, or attribute value (not needed for delete)"
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
