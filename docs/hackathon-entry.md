# Gambit for Hermes — 0.2.2

Entry copy prepared 8 November 2026 for [itsflownium/gambit-hackathon](https://github.com/itsflownium/gambit-hackathon). The accompanying catalog YAML is a draft pending the final release pin. Repository review does not submit the catalog PR, social post or organizer form.

## Short pitch

Play a game. Understand the mistake. Try another idea. Gambit pairs a focused chess board with your existing Hermes conversation, including replay and practice from your own public Chess.com and Lichess matches.

## Entry description

Gambit brings playing and understanding chess into one Hermes conversation. Open the knight button to reveal a board-only pane beside your existing chat. Start an untimed game as either colour, choose Normal for quiet play or Coach for brief feedback, and ask for progressively stronger hints when you want them.

The Import game picker searches completed public Chess.com and Lichess matches by username. Choose a specific result with its players, date, colour and result; the source link remains visible. Replay every half-move, ask for an explanation of the selected move, then move your own pieces to practice an alternative without changing the original game. Following the source produces exactly its next recorded opponent reply. Deviating produces one calculated reply from Hermes.

Python-chess enforces legal moves, Stockfish supplies local calculation evidence, and the configured Hermes model selects moves and explains mistakes in chat. A hard 60-second board-response deadline keeps play moving with a disclosed legal fallback if needed. Saved positions, annotations and PGN export preserve the learning session; Undo removes feedback belonging to discarded moves.

The result is a small, focused learning loop: play, understand what happened, and try another idea on a board that stays connected to the conversation.

## Why this entry is useful

| Area | Current feature and evidence |
| --- | --- |
| Usefulness | A player can start a game, ask why a move was a mistake, import a particular public match, and practice a different continuation within the same conversation. Native play, requested hints, both import platforms and selected-move explanations were exercised locally. These checks demonstrate the workflow; they are not a claim of measured rating improvement. |
| Reliability | The local report records 82 passing Python behavioral tests, passing desktop contracts, and all 16 local catalog validation checks passing without warnings. A deliberately stalled model produced exactly one legal backup move at 59.607 seconds. Tests cover special moves, duplicate replies, chat boundaries, takebacks, stale feedback and preservation of source matches. |
| Polish | One custom knight launcher opens the pane. The board supports click, drag and keyboard movement, all four promotion choices, compact hover-labelled controls, a two-platform import picker and visible source identity. Normal and Coach modes respect the player's choice about commentary; unfinished chat drafts are protected. Resignation has a GG/fireworks transition into a fresh board. |
| Creativity | A saved match becomes something the player can explore. Following its original line preserves the recorded opponent response; changing a move creates a separate practice branch with one calculated reply. Hermes can explain the decision in the conversation, while the original record remains available for comparison. |

The evidence and its limits are documented in [the local verification report](verification.md). Native tests used the configured Hermes model. The isolated browser harness used real Stockfish with simulated chat availability; its engine replies are not presented as native model replies. Installation also succeeded in a fresh Hermes profile on this Mac. A separate physical machine, Linux and Windows have not been verified.

## Implemented scope and future ideas

Version 0.2.2 includes untimed standard chess as either colour; Learning, Balanced and Strong presets; Normal and Coach modes; four requested hint levels; public username imports with specific-match selection, refresh and older-game browsing; replay controls; practice branches; retrospective move evidence and full-match recaps; local saved games; Undo; resignation; legal draw claims; and annotated PGN export.

Recurring mistake detection across a player's history, personalized training plans, spaced practice and automatic tracking of long-term improvement are possible future directions. They are not implemented features of 0.2.2. The current full-match recap uses evidence from that match; it does not claim a personalized training model or an accuracy score. Strength presets are descriptive rather than calibrated ratings.

## Behavior disclosures for the eventual entry PR

These describe the current plugin and can accompany an eventual catalog PR after the public repository and exact release pin exist.

| Behavior | Disclosure |
| --- | --- |
| Hermes surfaces | Registers eight chess tools, one `pre_llm_call` hook, the `/chess` command and a bundled coaching skill. The native Desktop SDK supplies the toolbar launcher, pane, plugin routes, session state and session-addressed composer. Coaching appears in the existing chat. The plugin has no gateway message-injection permission and does not modify Hermes core. |
| Third-party network requests | Username searches send the selected username to `api.chess.com` or `lichess.org` over HTTPS and retrieve public game data. Opening the official source link can launch that site's page. Only completed public standard-chess games are supported; platform publication delays and rate limits apply. Chess.com Bot and Coach games are not available through this public lookup. |
| Model traffic and cost | Move selection and explanations use the user's configured Hermes provider through Hermes's model API. Chess positions, relevant source-match data and engine evidence may be included in those requests and in the bound conversation. The configured provider's usual usage, billing and data handling apply. The one-minute deadline covers the board reply, not the separate chat response. |
| Local reads outside plugin data | Reads the executable selected in `engine_path`, or discovers Stockfish in its own engine directory, on `PATH`, or at the documented Homebrew/system locations. It checks that executable's filesystem metadata for analysis caching and starts it as a UCI engine. It uses Hermes's supplied configuration and current conversation/profile identifiers. It does not inspect unrelated user documents or credential stores. |
| Processes and background work | Starts local Stockfish subprocesses directly, without a shell, for engine health checks, candidate moves and analysis. Background threads/timers handle the opponent deadline and full-match analysis. A recap may continue calculating while the pane is closed; automatic chat delivery waits for the correct visible, idle conversation and an empty draft. No separate hosted service is operated. The optional development preview is a manually started loopback web server. |
| Stored data | A profile-local SQLite database stores games, moves, source PGN and metadata, analyses, annotations, replay positions, conversation bindings and queued feedback. PGN export writes to the plugin's profile-local export directory. Desktop plugin storage retains routing/delivery bookkeeping. Deleting a saved game removes its associated saved analysis and detaches its selected board. |
| Credentials and telemetry | No Chess.com/Lichess passwords, OAuth login, browser cookies or separate API keys are required. Gambit does not read, store, refresh or rotate provider credentials; Hermes owns provider access. The plugin has no telemetry or usage-reporting endpoint. |
| Engine distribution and updates | Stockfish is a separately installed prerequisite, not a bundled plugin binary. The local verification used Stockfish 19 from its official archive, with the archive checksum and license recorded in the verification materials. Gambit does not download an engine, replace its own code or load remote executable UI code in the background. |
| Dependencies and affiliation | Requires Hermes Agent `>=0.23.0`, Hermes Desktop and local Stockfish; Python requires `>=3.11`. Runtime Python dependency ranges are bounded. Gambit is GPL-3.0-or-later; dependency and piece-art notices are in [THIRD_PARTY.md](../THIRD_PARTY.md). It is an independent project, unaffiliated with Chess.com or Lichess, and has no catalog approval or official/verified tier claim. |

## Suggested demonstration and existing assets

Show a Coach move and its exact-move explanation, switch to Normal and request a hint, then import a chosen public match. Follow one recorded move, try an alternative, and return to the unchanged source. Keep actual model wait times visible or disclose any cut.

The screenshots are [the board](board-preview.png), [the import picker](import-preview.png), [source context during replay](replay-context-preview.png), [the compact menu](menu-preview.png) and [GG/fireworks](gg-preview.png). They show the shared board component in the browser preview. The [demo video](../demo/Gambit-Demo-Review.mp4) also includes a labelled, genuine native Hermes review excerpt.

## X post draft — not posted

> Gambit for Hermes: play chess, understand a mistake, then try another move. Import public Chess.com or Lichess matches and practice alternatives without changing the original. A focused board beside your chat, with coaching when you want it. Local demo of v0.2.2. @NousResearch

## Remaining submission metadata

- Repository: `https://github.com/itsflownium/gambit-hackathon`; maintainer: `itsflownium`.
- The full 40-character commit SHA for the final public 0.2.2 tree, with local validation repeated against that exact pin.
- Confirmation of the proposed macOS-only catalog scope. Other platforms need their own verification before broader compatibility claims.
- A repository-relative `subdir` only if the eventual public repository places the plugin below its root.
- Reviewed, public screenshot URLs pinned to that commit, and an optional public documentation/banner URL. The current draft keeps these unset.
- Approval of the local 86-second review cut, and any event-specific form fields, team details, links or attribution requirements supplied by the organizer. Verified event instructions, deadline and destinations are in [hackathon-preparation.md](hackathon-preparation.md).
- Separate authorization for an upstream catalog PR, social post and organizer form submission. Those actions are not performed by the implementation PR in this repository.

The companion [catalog YAML draft](catalog-entry.draft.yaml) follows the current [official entry schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md#entry-schema), checked alongside the [catalog submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission) on 8 November 2026. Admission requires a public repository, an exact commit pin and maintainer review; passing local validation does not constitute catalog acceptance.
