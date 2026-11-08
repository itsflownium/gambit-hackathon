"""One validated action contract for the board HTTP and session-command transports."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Action(BaseModel):
    session_id: str = Field(min_length=1, max_length=256)
    action: str = Field(max_length=32)
    move: str | None = Field(default=None, max_length=24)
    revision: int | None = None
    ply: int | None = None
    view_revision: int | None = None
    game_id: str | None = Field(default=None, max_length=64)
    mode: str | None = Field(default=None, max_length=16)
    colour: str | None = Field(default=None, max_length=5)
    strength: str | None = Field(default=None, max_length=16)
    platform: str | None = Field(default=None, max_length=16)
    username: str | None = Field(default=None, max_length=50)
    source_id: str | None = Field(default=None, max_length=100)
    game_number: int | None = Field(default=None, ge=1, le=50)
    limit: int = Field(default=10, ge=1, le=50)
    before: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    refresh: bool = False
    event_id: str | None = Field(default=None, max_length=64)


def board_action(service, body: Action):
    try:
        if body.action == "start":
            return service.start(body.session_id, body.colour or "white", body.strength or "balanced", body.mode or "normal")
        if body.action == "find_games":
            return service.find_games(body.session_id, body.platform or "", body.username or "", limit=body.limit, before=body.before, refresh=body.refresh)
        if body.action == "open_replay":
            return service.open_replay(body.session_id, platform=body.platform, source_id=body.source_id,
                                       username=body.username, game_number=body.game_number, ply=body.ply or 0)
        if body.action == "coach_ack":
            return service.acknowledge_coaching(body.session_id, body.event_id)
        if body.action == "move":
            return service.move(body.session_id, body.move or "", body.revision, body.game_id)
        if body.action == "practice_move":
            return service.practice(body.session_id, game_id=body.game_id, view_revision=body.view_revision,
                                    mode=body.mode, move=body.move or "")
        if body.action == "seek":
            return service.seek(body.session_id, body.ply, view_revision=body.view_revision, game_id=body.game_id)
        if body.action not in {"set_mode", "undo", "resign", "claim_draw", "export", "resume", "practice", "replay_source"}:
            raise ValueError("Use a valid board action")
        return service.action(body.session_id, body.action, revision=body.revision, game_id=body.game_id,
                              mode=body.mode, view_revision=body.view_revision)
    except ValueError as exc:
        return {"ok": False, "error": getattr(exc, "code", "invalid_action"), "message": str(exc)}
