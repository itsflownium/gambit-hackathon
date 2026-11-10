# Gambit for Hermes — 0.3.0

Entry copy updated 10 November 2026 for [itsflownium/gambit-hackathon](https://github.com/itsflownium/gambit-hackathon). The terminal release has 175 passing behavioral tests, 24 passing host transport checks, real dashboard/CLI/native-TUI operation, fresh default-home terminal installation/play and a verified 88-second film. Anonymous public-candidate admission and catalogue gates pass; the catalogue PR records the published pin. The existing [catalogue PR #152547](https://github.com/NousResearch/hermes-agent/pull/152547) remains a draft. No social post or organizer form has been submitted by this release work.

## Short pitch

Play a game. Understand the mistake. Try another idea. Gambit brings chess to Hermes terminals and Desktop, with coaching and replay practice from public Chess.com and Lichess matches.

## Entry description

Run `hermes gambit` for a standalone terminal chess board, use `/chess` for text-board output inside a Hermes CLI or TUI conversation, or open the optional graphical pane in Hermes Desktop. Start an untimed game as either colour, choose Normal for quiet play or Coach for brief feedback, and request progressively stronger hints.

Search completed public Chess.com and Lichess games by username, then choose a specific match by its players, date, colour and result. Replay each half-move and practice a different continuation without changing the original. Following the source produces its next recorded opponent reply. Deviating produces one calculated reply.

Python-chess enforces legal moves, Stockfish supplies local calculation evidence, and the configured Hermes model selects moves and explains mistakes. A hard 60-second board-response deadline uses a labelled legal fallback when needed. Saved positions, annotations and PGN export preserve the session; Undo removes feedback belonging to discarded moves.

The standalone dashboard keeps its own Gambit session in the active Hermes profile. Ordinary CLI/TUI chess tools wait for one opponent reply, return the board and request exact-move coaching in Coach mode. Bare `/chess` starts or refreshes the selected board; slash shortcuts return deterministic board or engine evidence on every chat surface without autonomous narration. The Desktop pane delivers coaching to its bound existing chat. The terminal board does not claim to be an embedded Hermes TUI widget.

## Evidence and release status

| Area | Scope and evidence |
| --- | --- |
| Usefulness | Real dashboard play, automatic feedback, two requested hint levels, clean Normal silence, selected public-match practice, production CLI anchored review and native TUI commands were checked. The source match remained unchanged after recorded and alternative practice. |
| Reliability | All 175 behavioral tests, 24 host transport checks, actual curses pseudo-terminal integration, fresh default-home terminal installation/play and Desktop contracts pass. Fixture, fallback and provider evidence are recorded separately. A stable candidate passed dependency resolution/installation and all 16 official checks with a safe scan and no validator warnings. The anonymous public candidate also passes the current admission, structure, payload, confinement and self-updater gates. |
| Polish | The terminal release adds a curses dashboard and conversation text board. Its 88-second film passes decode, caption, chapter-seek, desktop/mobile player and privacy checks. The optional Desktop pane retains its knight launcher, drag/click board, promotion choices, match picker, source identity and resignation animation. |
| Creativity | A selected source match becomes a preserved original plus editable practice branches. Recorded replies remain distinguishable from new calculations, and explanations use position-specific engine evidence. |

The [verification report](verification.md) separates current terminal checks from historical results. The established catalogue scope is macOS only; Linux, Windows and another physical computer have not been verified. No rating-improvement claim or calibrated strength rating is made.

## Implemented scope and future ideas

The 0.3.0 candidate brings terminal presentation to the existing untimed standard-chess service: either colour; Learning, Balanced and Strong presets; Normal and Coach modes; progressive hints; public username imports and exact-match selection; replay and practice branches; move-review evidence; saved games; Undo; resignation; legal draw claims; and annotated PGN export. Full-match recaps remain available through Hermes chat tools: Desktop can announce completion, CLI/TUI users retrieve the result on a later request, and the standalone dashboard has no summary command. The anonymous public candidate passes admission and catalogue gates; the existing catalogue PR remains a draft.

Recurring-mistake detection across a player's history, personalized training plans, spaced practice and long-term improvement tracking remain future ideas. They are not implemented features. A current match recap uses evidence from that match and does not invent accuracy scores.

## Behavior disclosures for the existing draft PR

| Behavior | Disclosure |
| --- | --- |
| Hermes surfaces | Eight chess tools, one `pre_llm_call` hook, `/chess`, a bundled coaching skill and public CLI registration for `hermes gambit`. The optional graphical pane uses the public Desktop SDK toolbar, pane, profile routes, session state and session-addressed composer. No Hermes core replacement or gateway message-injection permission is required. |
| Terminal scope | The standalone curses dashboard is an interactive terminal application with a separate Gambit session. It uses the active profile's plugin data and provider, rather than inferring an active Hermes chat. `/chess` supplies text-board output in a Hermes CLI or TUI conversation. With `plugins.isolation: host`, Hermes skips standalone CLI registration, so use `/chess`. |
| Third-party network requests | Username searches send the selected username to `api.chess.com` or `lichess.org` over HTTPS for public game data. Only completed public standard-chess matches are imported; publication delays and rate limits apply. Chess.com Bot and Coach games are unavailable through public username lookup. Official source links open the source platform. |
| Model traffic and cost | Move selection and explanations use the configured Hermes provider through host model APIs. Requests can include chess positions, source-match data and engine evidence. Normal provider usage and data handling apply. The 60-second deadline covers the board reply, while separate explanations have the provider's response time. |
| Local reads and processes | Reads the selected Stockfish executable or discovers it in plugin engine data, on `PATH` or at documented system locations. Stockfish runs directly as a UCI subprocess without a shell. Background threads/timers handle move deadlines and match review. The optional development preview is a manually started loopback web server. |
| Stored data | Profile-local SQLite data contains games, source PGN, moves, match metadata, analysis, annotations, replay cursors, conversation bindings and queued feedback. PGN exports use the plugin's export directory. Terminal sessions are separate from conversation bindings. Desktop storage retains routing/delivery bookkeeping. |
| Credentials and telemetry | No Chess.com/Lichess passwords, browser cookies or separate API keys are required. Provider access remains host-managed; Gambit does not read credential stores or rotate tokens. No telemetry endpoint is used. |
| Distribution and updates | Stockfish is separately installed, not bundled or downloaded automatically. Gambit does not replace its own source or load remote executable UI code. Updates to the catalogue pin remain subject to maintainer review. |
| Dependencies and compatibility | Hermes Agent `>=0.23.0`, Python `>=3.11` and local Stockfish are required. The standalone dashboard also needs an interactive terminal with Python curses; Desktop is optional for the graphical pane. Runtime ranges are bounded (`chess>=1.11.2,<2`, `httpx>=0.28.1,<1`). Catalogue scope is macOS. License: GPL-3.0-or-later; see [THIRD_PARTY.md](../THIRD_PARTY.md). Gambit is independent of Chess.com and Lichess, with no official or verified catalogue tier claim. |

## Demonstration

The verified [88-second terminal film](../demo/Gambit-Demo-Review.mp4) shows actual play, requested hints, coaching, a clean Normal turn, exact-match import and practice. It is 1080p at 30 fps, H.264/AAC, with 18 English caption cues and nine external chapter controls. Full decode, actual browser playback, chapter seeking, desktop/mobile caption fit and privacy checks passed. The [demo notes](../demo/README.md), [source provenance](../demo/source-provenance.json) and [edit timeline](../demo/edit-timeline.json) disclose capture limits and timing cuts.

The main terminal capture used the supported linked local development install before the final source commit and later copies; exact in-memory bytes were not frozen. A separate clean Normal take followed the core commit/source sync. The film must not be described as an immutable recording of the final release pin.

The [terminal screenshot](terminal-preview.png) and demo poster come from the actual feedback frame. Existing [board](board-preview.png), [import](import-preview.png), [replay](replay-context-preview.png), [menu](menu-preview.png) and [GG](gg-preview.png) screenshots show the graphical board component in the browser preview. Earlier Desktop-film evidence remains historical in the verification report; the current demo link opens the new terminal film.

## X post draft — not posted

> Gambit for Hermes: play chess in your terminal, ask for a hint, then replay a public match and try another line. Normal or Coach mode, legal moves, local Stockfish and an optional Desktop board. New terminal demo of v0.3.0. @NousResearch

## Remaining release and submission work

- Publish the reviewed source and verified terminal film through the source repository; runtime and media acceptance are recorded in [verification.md](verification.md).
- Select the full 40-character public release commit and repeat validation from an anonymous checkout at that pin.
- Update the existing draft catalogue PR's version, pin, README/media links, screenshots and disclosures together; keep it draft.
- Confirm event-specific form fields and attribution requirements using the [preparation notes](hackathon-preparation.md) before any separately authorized submission.

The [source-local catalogue template](catalog-entry.draft.yaml) follows the [official schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md#entry-schema) and [submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission), rechecked 10 November 2026. Local validation does not constitute catalogue acceptance.
