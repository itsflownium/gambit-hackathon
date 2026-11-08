class GambitError(ValueError):
    code = "invalid_action"


class StalePosition(GambitError):
    code = "stale_position"


class EngineUnavailable(GambitError):
    code = "engine_unavailable"


class ImportFailure(GambitError):
    code = "import_failed"
