import subprocess

def get_definition():
    """Return OpenAI function definition"""
    return {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the terminal. Use this to run system commands, list files, or check status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }


def execute(command: str) -> dict:
    """Execute the tool and return result"""
    try:
        # Run command with timeout
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"error": str(e)}


def to_event(args: dict, result: dict) -> dict:
    """
    Transform tool call into UI event.
    Returns None to use default tool_call display.
    """
    return None


def is_terminal() -> bool:
    """Does this tool end the agentic loop?"""
    return False
