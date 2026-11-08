# Live demonstration and review cut

The repository includes the revised [89-second demo](../demo/Gambit-Demo-Review.mp4), [poster](../demo/poster.png), captions and a chapter player. The film now uses fresh GPT OAuth play, hints and coaching. Catalog submission, social posting and the organizer form remain separate from this repository PR.

| Time | Evidence in the film |
| --- | --- |
| 0–6.5 s | Gambit and its focused board/chat concept. |
| 6.5–19.5 s | A real human `f3` followed by a GPT-selected `...e5`; the actual pending-move indicator is visible. |
| 19.5–32.5 s | Fresh requested level-one and level-two hints from the actual Hermes chat. |
| 32.5–47.5 s | The same short game ends with `g4 → Qh4#`; fresh feedback explains why the move exposed the king and gives a safer alternative. |
| 47.5–56.5 s | A real Normal-mode opening turn with a model reply and no automatic coaching event. |
| 56.5–66.5 s | The public Chess.com username picker identifies the exact match by opponent, date, result and side. Lichess is also supported and was separately checked. |
| 66.5–79.5 s | Recorded `...c5 → Nf3` and alternative `...e6 → Nc3`, with actual retrospective chat feedback. The imported original retains its 15 half-moves. |
| 79.5–89 s | Recurring-mistake analysis and targeted practice, explicitly labelled future ideas that are not implemented. |

Both opponent moves in the short teaching game were stored as `origin=hermes`, using GPT-6 Sol through the existing Hermes OAuth connection at xhigh reasoning. Stockfish calculates legal candidate moves and provides the evidence for hints and reviews. The visible activity indicator is progress feedback, not private model reasoning.

The recording mounts the unchanged release board through a public Hermes SDK workspace beside the real chat. A local capture adapter binds them to the actual game API and submits real chat turns. This is a live shared-board recording, not a fresh native toolbar-launch test. Crops, stills, timing cuts and accelerated waits make the responses readable within 89 seconds. Chat responses are not recreated. The film is not a latency or reliability benchmark.

The first high-rate capture overloaded the Mac and two hint attempts timed out. They succeeded after closing the disposable app and reducing capture to 10 fps. The edited film uses those verified results; the 30 fps export repeats source frames as needed. Full production notes, voice provenance, captions and integrity checks are in [the demo folder](../demo/README.md).

For a live presentation, open the knight button in Hermes, choose Coach mode, play one move, ask for a hint, and allow the actual chat turn to finish. Then search a public username, choose a specific match, and try a move in replay. Keep working Stockfish and Hermes-provider access configured. Normal mode is available for a quiet game with hints on request.
