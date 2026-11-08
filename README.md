# Gambit for Hermes

Play a game. Understand a move. Revisit your own matches.

Gambit adds one knight button to Hermes Desktop's top bar. It opens a chess board beside your existing chat, with direct play and a Chess.com/Lichess match picker. Coaching, hints, explanations, and match reviews stay in Hermes chat.

## Demo

[![Watch the Gambit demo](demo/poster.png)](demo/Gambit-Demo-Review.mp4)

[Watch the 89-second demo](demo/Gambit-Demo-Review.mp4). The [demo folder](demo/README.md) includes English captions, a poster, chapter timings and a local review player. The revised film shows a real GPT OAuth game, requested hints and fresh feedback in chat. Its shared-board SDK capture and timing edits are disclosed. The ending clearly identifies future ideas that are not implemented.

## Start

Open the knight button and choose **Play Hermes** or **Import game**. You can also initialize through chat:

```text
/chess
```

Then use ordinary conversation:

```text
Play against me. I'll play White in Coach mode.
Start a normal game against me, without automatic coaching.
My Chess.com username is USERNAME. Find my recent matches.
My Lichess username is USERNAME. Replay my latest completed game.
Explain my last move.
Give me a hint.
Give me a stronger hint.
Show my saved matches.
Export this match as PGN.
```

The knight button shows or hides the board. Click **Play Hermes** or **New game** to start directly on the board; `/chess` also initializes the conversation. It adds no permanent sidebar entry or extra chat panel. Every control has hover help.

### Play modes

**Coach:** Hermes plays against you and sends short feedback about your preceding move to this chat. You can ask for more detail.

**Normal:** Hermes plays against you without automatic commentary. Hints and explanations are available whenever you ask.

Change mode through chat or the board's compact actions menu. Games are untimed standard chess. Select a piece and destination or drag it. Promotions offer all four piece choices. The compact game menu includes undo, resignation, and a draw claim when the rules allow one. Confirming resignation shows a large GG with fireworks, then starts a fresh playable game as White after three seconds. The resigned match stays saved.

Optional shortcuts:

```text
/chess play white normal
/chess play black coach learning
/chess chess.com USERNAME
/chess lichess USERNAME
/chess status
```

### Replay

Click **Import game**, choose **Chess.com** or **Lichess**, enter a username, and search. Select a returned match to open its replay; each result shows the players, date, searched player's colour, and result. Hover for the exact game ID, or use **Older games** to browse further back. Search again to return to the newest matches.

You can also tell Hermes the platform and username, for example, “My Lichess username is Alice.” Hermes returns a numbered list. Reply “game 2” to select that exact match, or explicitly ask for “my latest match.” A username alone does not select a game. Each chat keeps its own search list and player perspective. Coaching and requested hints stay in chat.

The board's match strip shows the selected platform, username, opponent, date, and original result, with a link to the official game. It faces that player's side. **Move your pieces directly**, or click **Play from here**, to play through the match yourself. This creates a saved practice game; the original match remains intact, and its identity stays visible during practice.

When you follow the recorded moves, the opponent plays exactly its next recorded reply. If you try a different move, Hermes calculates one legal reply. You move once, the opponent replies once, and it is your turn again. **Back to recorded match** returns to the source. You can also use first/previous/watch/pause/next/last controls or ask Hermes to jump to a move.

Guided playback waits for chat coaching on the selected player's moves. The small guided-control toggle allows replaying without automatic explanations. Forward and back refer to individual White or Black moves, so every position is accessible.

Only completed public standard-chess matches are imported. Public APIs can delay availability of a newly completed match. A username is a lookup, not an authenticated account connection. Source links and the original PGN are preserved.

**Search games** checks the selected platform's public archive. After a search, **Refresh games** checks the source again instead of reusing the plugin's saved result. Empty searches expire after 30 seconds, so a new account's first published game is not hidden behind an hour-long empty cache. If the source fails, Gambit shows the error; saved nonempty results remain available with a notice.

Chess.com may still return its own cached data; refreshing Gambit cannot force Chess.com to publish a newly finished game sooner. Its [public API documentation](https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it) explains that delay. [Bot and Coach games are private](https://support.chess.com/en/articles/8609271-can-i-save-my-games-against-the-bots), so username search does not include them. Gambit is an independent plugin and is not affiliated with Chess.com or Lichess.

### Requested hints

Hints reveal progressively: a clue, the piece/source square, the destination, then the exact move and a legal continuation. Later levels are withheld until requested. A new position starts again at the first level. Normal mode supports the same hints as Coach mode.

## The move-time limit

The default move-response budget is **60 seconds**, with an enforced maximum of 60. Hermes's structured move-selection request gets at most 45 seconds within that budget. A separate deadline worker reserves time to commit a precomputed legal local-engine move if the model stalls. Late model results cannot add another move or change a newer position.

Moves can finish sooner; Gambit never sleeps just to stretch a fast answer to 30 seconds. The intended ordinary response range is around 30–60 seconds when the configured model needs that time. The UI shows the remaining move budget.

The deadline applies to the board reply, not the speed of the separate conversational coaching response. If the configured model is unavailable or times out, the board labels the reply as engine-assisted, and the coaching evidence records that fallback. A rare engine failure uses an explicitly labelled legal recovery reply to preserve the deadline.

New chat explanations need working access to the configured Hermes provider. If that provider rejects calls because access or credits are unavailable, board play can continue with its labelled local-engine fallback; conversational coaching resumes when provider access is available again.

## Calculation and coaching

Python-chess owns the legal game state. A local Stockfish process supplies move candidates, tactical lines, and position estimates. Hermes chooses among legal candidates and teaches from the calculation evidence through the user's configured model.

Opponent strength and full-strength review are separate. Learning, Balanced, and Strong are descriptive presets, not calibrated player ratings. Coaching does not invent accuracy scores or claim a position is checkmate merely because a source match ended by resignation or time forfeit.

Every accepted move is stored before any model request. Replay navigation cannot alter the original move sequence. Analysis, source PGN, results, and replay position survive restarts. PGN export includes saved review annotations.

Undo restores your turn, including after a final checkmating move. Coaching and saved annotations follow the retained move sequence: taking back a move removes its pending feedback, and a delayed analysis cannot attach to a different move or match.

## Install

Requires Hermes Agent **0.23.0 or later** with Hermes Desktop and a local Stockfish executable. Python dependencies are declared with bounded versions in `pyproject.toml` and prepared by Hermes's package manager.

While the implementation PR is under review, clone its branch and install the committed checkout through the supported Hermes installer:

```sh
gambit_checkout="$(pwd)/gambit"
git clone --branch feat/gambit-plugin-and-demo --single-branch https://github.com/itsflownium/gambit-hackathon.git "$gambit_checkout"
hermes plugins install "file://$gambit_checkout" --yes-deps --enable
```

After the implementation is merged into the default branch, the repository URL can be used directly with the supported installer. An unpacked source ZIP can use the linked-folder installation below; the Git-URL installer expects a committed Git checkout.

For linked local development, place a link to the checkout in the active Hermes home's `plugins/gambit` directory and run `hermes plugins enable gambit`. Enable **Gambit Chess** in Desktop's Capabilities → Plugins page and rescan if needed. If dependencies were installed after the gateway started, restart the gateway through Hermes's normal restart command.

Download Stockfish from [its official site](https://stockfishchess.org/download/) and choose its executable in Gambit's plugin settings, or install it on your system PATH. Gambit also recognizes an executable at its profile-local `plugin-data/gambit/engine/stockfish` path. It never downloads or updates an engine in the background.

Local verification used Stockfish 19 from its official macOS archive, checked against SHA-256 `a1f0e3bcc5a6927a11fe6fc8e54a779754645f3c2bae2cf13420fd1957adaa77`. The engine binary is not included in this repository.

### Plugin settings

- `engine_path`: optional absolute executable path.
- `move_timeout_seconds`: default 60, always capped at 60.
- `analysis_seconds`: default 0.4 seconds for initial local analysis; significant errors get a deeper check.

Settings live under `plugins.entries.gambit.settings`. Global Hermes model and reasoning settings are left intact.

## Chat delivery and data

Coaching is delivered through the native SDK's **session-addressed desktop composer**. It targets only the visible conversation bound to the board, waits while that conversation is busy, and acknowledges delivered events. If that chat is closed or another chat is selected, feedback waits for the correct chat to be visible again. No gateway message-injection permission is required.

Data is profile-local in Hermes's persistent `plugin-data/gambit` directory. Each match and each replay cursor is bound to its own conversation. Deleting a saved match removes its saved analysis and detaches its board from that conversation.

Network and process disclosure:

- Username searches request public game data from `api.chess.com` or `lichess.org` using documented APIs. No account passwords, browser cookies, private game chat, or scraping are used.
- Move selection and chat coaching use the user's existing Hermes model/provider. Normal provider usage applies. Chess positions and calculation evidence are supplied to that model.
- Stockfish runs locally as a bounded subprocess. The plugin uses small background threads for move deadlines and full-match reviews.
- No telemetry or separate hosted service is used.
- Imported text is treated as untrusted data, never executable instructions.

This independent plugin is not affiliated with or endorsed by Chess.com or Lichess. Its board colours, logo, and interface are its own. Open-source dependencies and piece-art attribution are described in `THIRD_PARTY.md`.

## Development and verification

Native source is in `src/`. Rebuild the standalone SDK entry after edits:

```sh
python3 scripts/build_ui.py
```

From a development environment with the declared dependencies and pytest:

```sh
python -m pytest tests -q
node tests/desktop_contract.mjs
hermes plugins doctor . --ci
hermes plugins validate . --install-deps
```

The optional `serve.py` previews only the chessboard in a local browser. The complete conversation experience runs in Hermes Desktop. Install the development extras, then run:

```sh
python serve.py --demo --engine /absolute/path/to/stockfish
```

The preview binds only to loopback. It does not simulate a Hermes chat or pretend that local engine responses are model responses.

The committed preview bundle can be rebuilt after board changes with `npm ci && npm run build` from `preview/`. Its dependencies and integrity hashes are locked. Hermes Desktop itself uses the host's React and needs no Node dependency installation.

## Release status

Version 0.2.2 includes the plugin source, bundled desktop entry, browser preview, tests, documentation and demo video. The initial implementation is merged in this repository. The fresh live demo and API-first profile fix are proposed in a new pull request. Local verification records 83 passing behavioral tests and all 16 Hermes validation checks passing; macOS was the tested platform. Catalog submission, social posting and the hackathon entry form are separate steps. See the [release checklist](docs/release-checklist.md) and [verification report](docs/verification.md).
