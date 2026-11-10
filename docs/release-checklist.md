# Release checklist

Updated 10 November 2026 for the 0.3.0 terminal release. All 175 behavioral tests, real pseudo-terminal integration, production dashboard play/coaching, 24 host transport checks, native TUI commands, fresh default-home terminal installation/play, dependency-aware candidate validation and final 88-second film QA passed. Anonymous final-pin validation and the existing catalogue draft update are pending. The [verification report](verification.md) preserves the evidence boundaries and earlier Desktop results.

## 0.3.0 candidate

- [x] Set the plugin, Python package, dashboard and preview package release labels to 0.3.0.
- [x] Document standalone `hermes gambit`, `/chess` text output in Hermes CLI/TUI conversations, and the optional graphical Desktop pane.
- [x] Retain macOS-only catalogue scope and the `>=0.23.0` Hermes floor.
- [x] Review public CLI registration and profile-scoped model, settings and storage APIs; no new runtime dependencies, environment requirements or hooks.
- [x] Pass all 175 behavioral tests, including CLI/TUI reply/board/coaching contracts, terminal session isolation, engine recovery, portable bare/start slash commands, legacy surface detection and close-race regressions.
- [x] Launch the actual curses renderer in a real pseudo-terminal with a fixture engine; complete one turn, refresh the reply, resize, show help, quit and restore terminal input flags.
- [x] Run the official profile-scoped `hermes gambit --help`; command registration succeeds.
- [x] Complete actual terminal `1.f3 e5 2.g4 Qh4#` with both replies from GPT-6.1 Sol through the existing host provider, automatic `f3` review and requested hint levels 1 and 2.
- [x] Complete clean Normal `1.e4 c5` with a model-selected reply and no automatic feedback; verify recorded `...c5 → Nf3`, alternative `...e6 → d4`, and preservation of the selected source match.
- [x] Pass official candidate validation with `--install-deps`, actual dependency resolution/installation, all 16 checks, a safe security scan and no validator warnings; final-pin acceptance remains separate.
- [x] Pass automated feature coverage for both colours, modes, hints, imports, replay/practice, Undo, endings, saving and restoration; keep live acceptance claims scoped to the recorded checks.
- [x] Verify production CLI move tools return one completed model reply, the exact anchored review request, real review and board.
- [x] Launch the official native Ink TUI; run `/chess`, `/chess move e4`, `/chess hint 1` and `/exit` successfully.
- [x] Pass production CLI Normal play without automatic review/hints, an explicit level-one clue and all 24 host transport checks.
- [x] Install the documented runtime candidate through the official Git installer into a fresh default Hermes home without Desktop, a named profile or copied auth; verify actionable missing-engine handling, then configured-engine Normal play, one labelled fallback, help and clean exit.
- [x] Run official Plugin Doctor on that clean installed candidate: exit 0, eight tools, one hook and no issues.
- [x] Pass Python compilation, generated Desktop-entry syntax, Desktop contracts and whitespace checks after shared-runtime changes.
- [x] Pass candidate payload, outside-tree symlink and self-updater checks; validate catalogue shape with the current upstream schema checker.
- [ ] Run required final-pin regression/validator checks, including Desktop contracts, Plugin Doctor and the official dependency-aware plugin validator.

## New terminal demo

- [x] Capture actual terminal operation and promote the verified 88.000-second film and review package.
- [x] Keep model replies, local engine fallback and recorded source replies distinguishable; disclose timing cuts and the faithful ANSI capture rendering.
- [x] Disclose that the main linked-development capture predates the final commit and its exact in-memory bytes were not frozen; the separate Normal take follows the core commit/source sync.
- [x] Replace the earlier Desktop demo and its review-player links with the terminal film.
- [x] Verify 18 caption cues, nine external chapter controls, the real feedback poster/screenshot, audio attribution, clean full decode, desktop/mobile player seeking and MP4 checksum.
- [x] Review visible frames, repository text and media metadata for private information. Verify final Git author/committer metadata when publishing the source.

## Exact pin and existing catalogue PR

- [ ] Commit the complete source, documentation and reviewed terminal demo to `itsflownium/gambit-hackathon` using the public maintainer identity.
- [ ] Resolve a public, cloneable full 40-character source commit and verify the candidate from an anonymous checkout at that exact pin.
- [ ] Rerun the current structural, executable-payload, self-updater and symlink-confinement checks; inspect every warning.
- [ ] Update only `plugin-catalog/gambit.yaml` on the existing `feat/gambit-catalog-0.2.4` branch for [PR #152547](https://github.com/NousResearch/hermes-agent/pull/152547).
- [ ] Bump its pin and version together; update `docs_url`, screenshots, demo/source links and behavior disclosures to the same verified commit.
- [x] Match the candidate's declared eight tools, one hook, empty middleware and empty environment requirements to its registrations; standalone CLI registration adds no tool or hook.
- [ ] Keep the existing upstream PR in draft and record the actual checks completed. A passing local validator does not constitute catalogue acceptance.

The catalogue entry remains `tier: community` and macOS only. The standalone terminal board requires curses and an interactive terminal; Desktop is required only for the graphical pane. With `plugins.isolation: host`, Hermes skips standalone CLI command registration; use `/chess` in a Hermes conversation. Stockfish remains a separately installed local executable. Linux, Windows and another physical computer are unverified.

## Historical 0.2.4 acceptance

- [x] Native regular-chat startup, Normal play, requested OAuth hint, automatic Coach feedback, selected-match replay and cold-start restoration checked on one Mac.
- [x] 86 behavioral tests, Desktop contracts and all 16 official validator checks passed without warnings in the documented environments.
- [x] Supported installation into two clean default Hermes homes passed with real Stockfish, Undo, restart persistence, public imports and replay navigation.
- [x] Earlier 89-second Desktop demo, poster, English captions, eight chapters, decode and player-seek checks completed.

Those checks describe earlier source and media. They are not a substitute for 0.3.0 acceptance. The [second-computer checklist](second-device-check.md) and verification on other operating systems are optional follow-ups, not blockers for this macOS-only release; those scopes remain unverified.

Social posting and the organizer form require their own authorization. Neither is performed by updating the existing catalogue draft.
