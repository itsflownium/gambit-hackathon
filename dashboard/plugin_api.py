"""Hermes-owned authenticated routes for the native chess board and import picker."""
from __future__ import annotations

import logging
import runpy
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_runtime = runpy.run_path(str(Path(__file__).resolve().parent.parent / "bootstrap.py"))["runtime"]()
router = APIRouter()
logger = logging.getLogger(__name__)


Action = _runtime.Action


class Diagnostic(BaseModel):
    event: str = Field(max_length=32)


@router.post("/diagnostic")
def diagnostic(body: Diagnostic):
    return _runtime.service().diagnostic(body.event)


@router.get("/state")
def state(session_id: str):
    if not session_id or len(session_id) > 256:
        raise HTTPException(400, "Open a Hermes chat to use Gambit.")
    return _runtime.service().state(session_id)


@router.post("/action")
def action(body: Action):
    return _runtime.board_action(_runtime.service(), body)
