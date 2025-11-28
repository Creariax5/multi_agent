
import json

def get_definition():
    return {
        "type": "function",
        "function": {
            "name": "create_artifact",
            "description": "Create a NEW visual artifact (HTML page, dashboard, website, code example) displayed in a side panel. ONLY use this for FIRST creation. If an artifact already exists and user wants modifications, use edit_artifact() instead. Do NOT create a new artifact just to show code - use send_message() for explanations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The full HTML/Markdown/Code content to display. For HTML, include complete document with styles."
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the artifact shown in the panel header."
                    },
                    "type": {
                        "type": "string",
                        "enum": ["html", "markdown", "code"],
                        "description": "The type of content: 'html' for web pages, 'markdown' for formatted text, 'code' for source code."
                    }
                },
                "required": ["content", "title", "type"]
            }
        }
    }

def execute(content: str, title: str = "Artifact", type: str = "html") -> str:
    """
    Create a UI artifact to display content in a side panel.
    """
    # This function primarily exists to trigger the side effect of the UI event.
    # The return value is what the LLM sees.
    return f"Artifact '{title}' created successfully."

def to_event(args: dict, result: str) -> dict:
    """
    Convert the tool call to a UI event.
    """
    return {
        "type": "artifact",
        "content": args.get("content", ""),
        "title": args.get("title", "Artifact"),
        "artifact_type": args.get("type", "html")
    }
