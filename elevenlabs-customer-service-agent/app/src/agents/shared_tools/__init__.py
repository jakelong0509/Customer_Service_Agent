"""Auto-discover and register all tools in this package."""

import importlib
import pkgutil

def auto_register_tools() -> None:
    """Auto-import all modules to trigger @register_tool decorators."""
    package_name = __name__
    
    # Import all submodules to trigger registration
    for _, name, _ in pkgutil.iter_modules(__path__):
        full_name = f"{package_name}.{name}"
        importlib.import_module(full_name)

# Auto-run on first import (optional)
auto_register_tools()