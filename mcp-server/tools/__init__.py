"""
MCP Tools Plugin System
Each .py file in this directory is a tool plugin with:
  - get_definition() -> OpenAI function schema
  - execute(**args) -> result dict  
  - to_event(args, result) -> UI event (optional)
  - is_terminal() -> bool (optional)
"""
import os
import importlib
import glob


def load_all_tools():
    """Load all tool plugins"""
    tools = []
    functions = {}
    handlers = {}  # Tool name -> module (for to_event, is_terminal)
    
    tools_dir = os.path.dirname(__file__)
    
    for filepath in glob.glob(os.path.join(tools_dir, "*.py")):
        filename = os.path.basename(filepath)
        if filename.startswith("_"):
            continue
        
        module_name = filename[:-3]
        
        try:
            module = importlib.import_module(f"tools.{module_name}")
            
            # New API: get_definition() function
            if hasattr(module, "get_definition") and hasattr(module, "execute"):
                definition = module.get_definition()
                tool_name = definition["function"]["name"]
                
                tools.append(definition)
                functions[tool_name] = module.execute
                handlers[tool_name] = module
                
                print(f"  ✓ {tool_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {e}")
    
    return tools, functions, handlers
