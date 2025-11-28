"""
Batch Edit Artifact Tool - Apply multiple edits in a single operation
Solves the coordination problem when making complex changes
"""

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "batch_edit_artifact",
            "description": """Apply multiple edits to an artifact in a single atomic operation.

USE THIS when you need to:
- Make coordinated changes to multiple elements
- Replace and add content in one operation
- Ensure all changes succeed or none apply

Each operation in the batch follows edit_artifact syntax.

Example batch:
[
  {"selector": ".old-section", "operation": "delete"},
  {"selector": "main", "operation": "append", "content": "<section class='new'>...</section>"},
  {"selector": ".header h1", "operation": "replace", "content": "New Title"}
]

Operations are applied in order. If one fails, subsequent operations still attempt.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "description": "Array of edit operations to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "selector": {
                                    "type": "string",
                                    "description": "CSS selector for the target element"
                                },
                                "operation": {
                                    "type": "string",
                                    "enum": ["replace", "insert_after", "insert_before", "delete", "set_style", "set_attribute", "append", "prepend", "replace_outer", "wrap", "unwrap", "clear"],
                                    "description": "The edit operation type"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "HTML/CSS content for the operation"
                                },
                                "attribute": {
                                    "type": "string",
                                    "description": "Attribute name for set_attribute"
                                }
                            },
                            "required": ["selector", "operation"]
                        }
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the batch changes"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, validate operations without applying. Returns what would change."
                    }
                },
                "required": ["operations", "description"]
            }
        }
    }


def execute(operations: list, description: str, dry_run: bool = False) -> str:
    """Execute batch edit operations."""
    mode = "Dry run" if dry_run else "Batch edit"
    return f"{mode}: {len(operations)} operations - {description}"


def to_event(args: dict, result: str) -> dict:
    """Convert to UI event for batch processing."""
    return {
        "type": "batch_artifact_edit",
        "operations": args.get("operations", []),
        "description": args.get("description", ""),
        "dry_run": args.get("dry_run", False)
    }
