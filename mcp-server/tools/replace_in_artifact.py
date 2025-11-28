"""
Replace in Artifact Tool - Simple string replacement like replace_string_in_file
Much more reliable than DOM manipulation
"""

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "replace_in_artifact",
            "description": """Replace a string in the current artifact. Works like find-and-replace.

USAGE:
1. Use get_artifact first to see the current code
2. Copy the EXACT text you want to replace (including whitespace)
3. Provide the new text

This is much safer than edit_artifact for code changes.

Example - change game speed:
  old_string: "let speed = 100;"
  new_string: "let speed = 300;"

Example - fix a function:
  old_string: "function update() { move(); }"
  new_string: "function update() { move(); draw(); checkCollision(); }"
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to find and replace. Must match exactly including whitespace."
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The text to replace it with."
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the change."
                    }
                },
                "required": ["old_string", "new_string", "description"]
            }
        }
    }


def execute(old_string: str, new_string: str, description: str) -> str:
    return f"Replaced: {description}"


def to_event(args: dict, result: str) -> dict:
    return {
        "type": "replace_in_artifact",
        "old_string": args.get("old_string", ""),
        "new_string": args.get("new_string", ""),
        "description": args.get("description", "")
    }
