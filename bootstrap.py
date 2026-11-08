"""Share one runtime per source revision across the agent and dashboard loaders."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


def runtime():
    root = Path(__file__).resolve().parent
    # Hermes reloads the entry point, but our shared package lives outside that
    # entry point's namespace. Include its source so a supported plugin reload
    # cannot silently keep the previous command handlers. Both entry points
    # still resolve the same runtime for an unchanged checkout.
    digest = hashlib.sha256(str(root).encode())
    for source in sorted((root / "gambit").rglob("*.py")):
        digest.update(str(source.relative_to(root)).encode())
        digest.update(source.read_bytes())
    name = "gambit_runtime_" + digest.hexdigest()[:16]
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
            for loaded in list(sys.modules):
                if loaded == name or loaded.startswith(name + "."):
                    sys.modules.pop(loaded, None)
            raise
    return sys.modules[name]
