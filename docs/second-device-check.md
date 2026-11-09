# Optional second computer verification

The local candidate passed two fresh default-home installations and native regular-chat checks on the development Mac. A different physical computer has not been tested. This checklist is prepared for that optional check; it is not evidence that it already passed.

Use another Mac with Hermes Agent 0.23.0 or later, Hermes Desktop and a separately installed local Stockfish executable. Follow the release README's supported installation method. A Git-URL installation needs a committed checkout; an unpacked source ZIP uses the documented linked-folder method. Configure that computer's engine path and its own Hermes provider access.

- [ ] Confirm Plugin Doctor discovers eight chess tools and one hook, and local catalog validation passes.
- [ ] Confirm the knight toolbar button opens the pane beside the existing chat.
- [ ] In Normal mode, play a legal move and receive exactly one reply. Request a hint explicitly.
- [ ] In Coach mode, play a turn and receive a retrospective explanation of that exact human move in chat.
- [ ] Import a specific completed public game from Chess.com, then one from Lichess. Check source ID, player colour, move count and official source link.
- [ ] Follow one original move for a recorded reply, try an alternative for a calculated reply, and return to the preserved original match.
- [ ] Undo a completed turn and verify that the player moves next and discarded feedback is gone.
- [ ] Resign and observe GG/fireworks followed by a fresh playable board.
- [ ] Restart Hermes normally and confirm a saved match/cursor can be resumed.

Record the computer, macOS version, Hermes version, engine version and result before marking this check complete. Other operating systems need their own verification before broader platform claims are made.
