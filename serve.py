"""Optional local board preview. Native Hermes is the complete coaching experience."""
from __future__ import annotations

import argparse
import importlib.util
import runpy
import sys
import tempfile
from pathlib import Path


def app_for(directory, engine_path="", demo=False):
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    root = Path(__file__).resolve().parent
    runtime = runpy.run_path(str(root / "bootstrap.py"))["runtime"]()
    service = runtime.configure_standalone(directory, engine_path)
    spec = importlib.util.spec_from_file_location("gambit_preview_api", root / "dashboard/plugin_api.py")
    api = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = api
    spec.loader.exec_module(api)
    app = FastAPI(title="Gambit local board preview")
    @app.middleware("http")
    async def local_origin(request: Request, next_call):
        origin = request.headers.get("origin")
        if request.method != "GET" and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"ok": False, "message": "Invalid origin"}, status_code=403)
        return await next_call(request)
    app.include_router(api.router, prefix="/api/plugins/gambit")
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")
    app.mount("/", StaticFiles(directory=root / "preview", html=True), name="preview")
    if demo:
        service.initialize("preview")
        if not service.store.session("preview").get("game_id"):
            service.start("preview")
    return app


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--engine", default="")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    directory = Path(args.data_dir or tempfile.mkdtemp(prefix="gambit-preview-"))
    uvicorn.run(app_for(directory, args.engine, args.demo), host="127.0.0.1", port=args.port, access_log=False)
