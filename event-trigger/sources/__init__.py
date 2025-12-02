"""
Event Sources Plugin System

Each .py file in this directory is a source plugin with:
  - get_definition() -> source config dict
  - get_instructions() -> str (AI instructions for this source)
  - format_event(data) -> str (format event data for AI)
  - get_routes(app) -> None (optional, register custom FastAPI routes)
"""
import os
import importlib
import glob
from typing import Dict, Any, List, Callable


class SourceRegistry:
    """Registry for event source plugins"""
    
    def __init__(self):
        self.sources: Dict[str, Any] = {}  # name -> module
        self.definitions: Dict[str, Dict] = {}  # name -> definition
        self.loaded = False
    
    def load_all(self):
        """Load all source plugins from this directory"""
        if self.loaded:
            return
        
        sources_dir = os.path.dirname(__file__)
        
        print("📦 Loading event sources...")
        
        for filepath in glob.glob(os.path.join(sources_dir, "*.py")):
            filename = os.path.basename(filepath)
            if filename.startswith("_"):
                continue
            
            module_name = filename[:-3]
            
            try:
                module = importlib.import_module(f"sources.{module_name}")
                
                # Required: get_definition() and format_event()
                if hasattr(module, "get_definition") and hasattr(module, "format_event"):
                    definition = module.get_definition()
                    source_name = definition.get("name", module_name)
                    
                    self.sources[source_name] = module
                    self.definitions[source_name] = definition
                    
                    print(f"  ✓ {source_name}")
            except Exception as e:
                print(f"  ✗ {module_name}: {e}")
        
        self.loaded = True
        print(f"📦 Loaded {len(self.sources)} sources")
    
    def get_source(self, name: str):
        """Get a source module by name"""
        self.load_all()
        # Try exact match first, then lowercase
        return self.sources.get(name) or self.sources.get(name.lower())
    
    def get_definition(self, name: str) -> Dict:
        """Get source definition"""
        self.load_all()
        return self.definitions.get(name) or self.definitions.get(name.lower(), {})
    
    def get_instructions(self, name: str, custom: str = None) -> str:
        """Get AI instructions for a source"""
        self.load_all()
        
        if custom:
            return custom
        
        module = self.get_source(name)
        if module and hasattr(module, "get_instructions"):
            return module.get_instructions()
        
        # Default generic instructions
        return f"""Tu es un assistant qui traite les événements {name}.
Analyse l'événement et détermine les actions appropriées.
Réponds de manière concise avec un résumé et les actions recommandées."""
    
    def format_event(self, name: str, data: Dict[str, Any]) -> str:
        """Format event data using source-specific formatter"""
        self.load_all()
        
        module = self.get_source(name)
        if module and hasattr(module, "format_event"):
            return module.format_event(data)
        
        # Default generic formatting
        import json
        from datetime import datetime
        return f"""## 🔔 Événement {name.upper()}

**Source:** {name}
**Date:** {datetime.now().isoformat()}

### Données:
```json
{json.dumps(data, indent=2, default=str)}
```
"""
    
    def list_sources(self) -> List[Dict]:
        """List all available sources"""
        self.load_all()
        return [
            {
                "name": name,
                "description": defn.get("description", ""),
                "endpoint": defn.get("endpoint", f"/webhook/{name}")
            }
            for name, defn in self.definitions.items()
        ]
    
    def register_routes(self, app):
        """Let each source register custom routes"""
        self.load_all()
        
        for name, module in self.sources.items():
            if hasattr(module, "get_routes"):
                try:
                    module.get_routes(app)
                    print(f"  🔗 Registered routes for {name}")
                except Exception as e:
                    print(f"  ⚠️ Failed to register routes for {name}: {e}")


# Singleton
registry = SourceRegistry()


def load_all_sources():
    """Load all sources and return registry"""
    registry.load_all()
    return registry
