# Optional second computer verification

The earlier Desktop release passed two fresh default-home installations and native regular-chat checks on the development Mac. The 0.3.0 candidate also has terminal tests and selected live provider interactions on that Mac. A different physical computer has not been tested. This checklist is prepared for that optional check; it is not evidence that it already passed.

Use another Mac with Hermes Agent 0.23.0 or later and a separately installed local Stockfish executable. The standalone dashboard needs an interactive terminal with Python curses; Desktop is optional for its graphical pane. Follow the release README's supported installation method. A Git-URL installation needs a committed checkout; an unpacked source ZIP uses the documented linked-folder method. Configure that computer's engine path and its own Hermes provider access.

- [ ] Confirm Plugin Doctor discovers eight chess tools and one hook, and local catalog validation passes.
- [ ] Run `hermes gambit --help`, launch the standalone board, play a turn, request a hint and verify automatic Coach feedback in its own pane. Resize and quit; confirm normal terminal input is restored.
- [ ] In Hermes CLI/TUI, use bare `/chess` to start a White Coach game, play through ordinary chat and verify one reply, the text board and exact-move review. Check slash shortcuts return board/engine evidence directly.
- [ ] Confirm standalone sessions and Hermes conversations retain separate games in the correct profile. With host isolation enabled, use `/chess` because standalone CLI registration is skipped.
- [ ] If Desktop is installed, confirm the knight toolbar button opens the pane beside the existing chat.
- [ ] In Normal mode, play a legal move and receive exactly one reply. Request a hint explicitly.
- [ ] In Coach mode, play a turn and receive a retrospective explanation of that exact human move in chat.
- [ ] Import a specific completed public game from Chess.com, then one from Lichess. Check source ID, player colour, move count and official source link.
- [ ] Follow one original move for a recorded reply, try an alternative for a calculated reply, and return to the preserved original match.
- [ ] Undo a completed turn and verify that the player moves next and discarded feedback is gone.
- [ ] Resign and verify the saved result. In Desktop, also observe GG/fireworks followed by a fresh playable board.
- [ ] Restart Hermes normally and confirm a saved match/cursor can be resumed.

Record the computer, macOS version, Hermes version, engine version and result before marking this check complete. Other operating systems need their own verification before broader platform claims are made.
