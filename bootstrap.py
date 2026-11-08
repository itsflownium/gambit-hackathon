"""Import only our own package once, shared by the agent and dashboard loaders."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


def runtime():
    root = Path(__file__).resolve().parent
    name = "gambit_runtime_" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, root / "gambit" / "__init__.py",
            submodule_search_locations=[str(root / "gambit")],
        )
        if spec is None or spec.loader is None:
            raise ImportError("Gambit package could not be loaded")
        module = importlib.util.module_from_spec(spec)
        # This namespace is our package, never a Hermes core module.
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]
