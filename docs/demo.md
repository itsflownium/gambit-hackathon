# Terminal demonstration

The repository includes an [88-second terminal demo](../demo/Gambit-Demo-Review.mp4), [poster](../demo/poster.png), English captions and a [nine-chapter review player](../demo/Review.html). The film opens with a real Hermes CLI launch, follows the supported `hermes gambit` dashboard through a game, requested hints, coaching, import and practice, then closes in the native Hermes Ink TUI.

| Time | Evidence in the film |
| --- | --- |
| 0–4 s | The actual `itsflownium` shell prompt, typed Hermes CLI launch and real CLI chess board. |
| 4–18 s | Human `f3`, actual public progress and a genuine Hermes `...e5` reply. |
| 18–27 s | A requested level-one clue for the current position. |
| 27–34 s | A distinct level-two hint, requested at the same position. |
| 34–53 s | Human `2.g4`, the genuine `...Qh4#` reply and actual coaching explaining the exposed king and forced mate. |
| 53–59 s | A separate, completed Normal-mode `1.e4 c5` turn with a genuine Hermes reply and no automatic coaching. |
| 59–68 s | A public Chess.com search, specific match selection and loaded replay. |
| 68–81 s | Recorded `...c5 → Nf3` and genuine alternative `...e6 → d4`, with the imported original preserved. |
| 81–88 s | The native Hermes Ink TUI shows `/chess` input and the genuine `1.e4 c5` board and reply. |

The public alias `itsflownium` appears in added chrome throughout the film. The real child-shell prompt already uses that handle. Disposable profile identity and visible working-directory fields are relabelled only in the declared presentation regions; chess state, moves, public match data and model response text are unchanged. The middle 4–81 seconds retains the original 17 source spans, and the audio and 18 caption cues are unchanged.

The actual terminal session is rendered from its timestamped ANSI capture. Cuts shorten waits; the responses are genuine. The source-to-edit map retains the original events and waits privately. The film is an edited demonstration, not a performance benchmark. It shows public move status, with no private model reasoning or recreated product replies.

The fresh provider run uses GPT-6.1 Sol, selected through Hermes before capture in an isolated demo profile using the existing authorized OAuth connection. Both opponent moves in `1.f3 e5 2.g4 Qh4#` were genuine Hermes replies. The coaching ties `2.g4` to the exposed king and forced mate. Stockfish calculates legal candidates and supplies the position evidence for hints and reviews.

The import selects completed Chess.com match `186751169392` from the Black perspective. A recorded practice branch follows `...c5 → Nf3`; a separate alternative `...e6` receives the fresh Hermes reply `d4`. Both branches receive real retrospective feedback. The imported original retains all 15 half-moves and its `1–0` result.

The main Coach/import/practice take used the supported linked local terminal candidate during development. Its exact in-memory source bytes were not frozen, and files were refreshed after its modules loaded. The separate clean Normal take followed the core commit and source sync. [Capture provenance](../demo/source-provenance.json) records that limit; [the exact edit spans](../demo/edit-timeline.json) retain source timing.

Narration uses the locally rendered Kokoro v1.0 `af_heart` synthetic voice through kokoro-onnx 0.6.1 at speed 0.95. The original score, *Quiet Continuation*, uses local additive synthesis without external samples or tracks. Eighteen caption cues use the narration model's original phoneme durations. Production notes, audio provenance, captions and integrity checks are in [the demo folder](../demo/README.md).

For a live presentation, run `hermes gambit` from a configured Hermes installation. Choose Coach, play a legal move and allow the real reply and feedback to complete. Request a clue, then ask for the next hint level when wanted. Choose Normal for a quiet game, or import a specific public match and try a move in replay. The CLI/TUI chat command is `/chess`.

Raw terminal captures, runtime homes, account credentials, database files, engine binaries, voice model weights and production helpers are excluded from the public demo package. Catalog submission, social posting and the organizer form remain separate actions.
