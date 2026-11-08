import pytest

from gambit.engine import Engine


class RecordedCalculation(Engine):
    """An engine boundary with deterministic scores, while the rules remain real."""
    def __init__(self, directory, before_mate=None):
        executable = directory / "engine-fixture"
        executable.write_text("engine identity for the analysis cache")
        super().__init__(directory, str(executable))
        self.before_mate = before_mate

    def position(self, board, **kwargs):
        before = len(board.move_stack) == 2
        return {"lines": [{"score_white_cp": 0 if before and self.before_mate is None else None,
                           "mate_white": self.before_mate if before else -1,
                           "line_san": ["Qh4#"] if not before else ["Nc3"]}]}


def fools_mate_prefix(store):
    game = store.create()
    game["moves"] = ["f2f3", "e7e5", "g2g4"]
    return game


@pytest.mark.parametrize("prior,expected", [(None, "allows forced mate"), (-3, "forced mate remains")])
def test_review_distinguishes_a_new_error_from_an_already_lost_position(store, prior, expected):
    result = RecordedCalculation(store.directory, prior).review(fools_mate_prefix(store), 3, store)
    assert result["classification"] == expected
    assert result["played_san"] == "g4"
    assert result["mover"] == "white"


def test_analysis_cache_retains_the_match_it_explains(store):
    engine = RecordedCalculation(store.directory)
    first, second = fools_mate_prefix(store), fools_mate_prefix(store)
    a, b = engine.review(first, 3, store), engine.review(second, 3, store)
    assert a["game_id"] == first["id"]
    assert b["game_id"] == second["id"]
    assert a["game_id"] != b["game_id"]
