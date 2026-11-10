"""One real pseudo-terminal pass catches curses/input/worker integration failures."""
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import time

import pytest

from gambit.storage import Store


CHILD = r'''
import sys
import chess
from gambit.service import Service
from gambit.storage import Store
from gambit.terminal import run_terminal

class Engine:
    configured_path = "fixture"
    def health(self):
        return {"ready": True, "name": "fixture"}
    def candidates(self, board, strength="balanced"):
        move = "e7e5" if chess.Move.from_uci("e7e5") in board.legal_moves else next(iter(board.legal_moves)).uci()
        return {"choices": [move], "recommended": move, "lines": [], "engine": "fixture"}
    def review(self, game, ply, store):
        return {"game_id": game["id"], "ply": ply, "played_san": "e4", "classification": "sound move", "facts": [], "loss_cp": 0}

service = Service(Store(sys.argv[1]), engine=Engine())
try:
    code = run_terminal(service, "pty-fixture", mode="normal", ascii_pieces=True, poll_interval=.05)
finally:
    service.stop()
raise SystemExit(code)
'''


@pytest.mark.skipif(os.name != "posix", reason="A real Unix pseudo-terminal is required")
def test_real_terminal_accepts_move_refreshes_reply_survives_resize_and_restores_terminal(tmp_path):
    import fcntl
    import pty
    import termios

    store = Store(tmp_path)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 100, 0, 0))
    terminal_flags = termios.tcgetattr(slave)
    environment = dict(os.environ, TERM="xterm-256color")
    process = subprocess.Popen([sys.executable, "-c", CHILD, str(tmp_path)],
                               cwd=Path(__file__).resolve().parents[1],
                               env=environment, stdin=slave, stdout=slave, stderr=slave,
                               start_new_session=True)
    output = bytearray()

    def pump_until(predicate, message, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], .02)
            if ready:
                try:
                    output.extend(os.read(master, 65536))
                except OSError:
                    pass
            if predicate():
                return
            assert process.poll() is None, f"Terminal exited before {message}: {bytes(output[-1500:])!r}"
        pytest.fail(f"Terminal did not reach {message}: {bytes(output[-1500:])!r}")

    def reply_saved():
        session = store.session("pty-fixture")
        return bool(session.get("game_id") and store.game(session["game_id"])["moves"] == ["e2e4", "e7e5"])

    try:
        pump_until(lambda: b"GAMBIT" in output, "its initial dashboard")
        os.write(master, b"e4\n")
        pump_until(reply_saved, "one saved legal reply")
        pump_until(lambda: b"e5" in output, "the refreshed reply on the actual terminal")
        assert b"e4" in output
        before_resize = len(output)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 18, 45, 0, 0))
        os.kill(process.pid, signal.SIGWINCH)
        os.write(master, b"?\n")
        pump_until(lambda: b"Enter SAN" in output[before_resize:], "its help after a terminal resize")
        os.write(master, b"q\n")
        pump_until(lambda: process.poll() is not None, "a clean quit", timeout=3)
        assert process.returncode == 0
        restored_flags = termios.tcgetattr(slave)
        assert restored_flags[3] & (termios.ECHO | termios.ICANON) == terminal_flags[3] & (termios.ECHO | termios.ICANON)
        assert reply_saved()
        session = store.session("pty-fixture")
        assert store.game(session["game_id"])["pending"] is None
        assert len(store.list_games()) == 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        os.close(master)
        os.close(slave)
