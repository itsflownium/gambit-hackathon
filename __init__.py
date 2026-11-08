"""Hermes directory-plugin entry point."""
if __package__:
    from .bootstrap import runtime
else:
    # File-based tools can load a checkout whose directory is not a Python name.
    from pathlib import Path
    import runpy

    runtime = runpy.run_path(str(Path(__file__).resolve().with_name("bootstrap.py")))["runtime"]


def register(ctx):
    runtime().register(ctx)
