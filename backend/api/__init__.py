# backend/api/__init__.py
"""
API Module Auto-loader

This module automatically imports all submodules within the api package.
This ensures that all API routers are registered when the package is imported,
allowing FastAPI to discover and include all endpoints automatically.

Note: If startup performance becomes an issue, consider lazy loading or
explicit imports instead of this auto-discovery pattern.
"""

import importlib
import pkgutil

for _, module_name, _ in pkgutil.walk_packages(__path__, __name__ + "."):
    importlib.import_module(module_name)
