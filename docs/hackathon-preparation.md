# Hackathon preparation — Gambit 0.3.0

Updated 10 November 2026 for the terminal release candidate. The existing [upstream catalogue PR #152547](https://github.com/NousResearch/hermes-agent/pull/152547) remains a draft. This release work updates that draft after exact-pin verification; social posting and the organizer form are separate actions. The event notes below were recorded on 8 November and should be rechecked before submission.

## Deadline and entry route

The organizer specifies **5 PM EST on 11 November** for this November 2026 event. The corresponding times are:

| Zone | Deadline |
| --- | --- |
| EST, UTC−05:00 | Wednesday **11 November 2026, 5:00 PM** |
| UTC | Wednesday **11 November 2026, 22:00** |
| Australia/Sydney, AEDT, UTC+11:00 | Thursday **12 November 2026, 9:00 AM** |

The time conversion uses `America/New_York` and `Australia/Sydney`. The announcement gives November 11 without spelling out the year; 2026 is the current event context. [Organizer announcement](https://uk.linkedin.com/company/nousresearch).

The recorded organizer instructions require:

1. A pull request adding the plugin to the [Hermes catalog](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog).
2. A working demo video **under 90 seconds**, posted on X and tagging **@NousResearch**.
3. Both the **catalog PR URL** and **X demo-post URL** submitted through the [organizer-linked Typeform](https://form.typeform.com/to/FwJLvOln). The form can be submitted once the PR is open; a merged PR is not stated as an entry prerequisite. Maintainers initiate catalog checks and review separately. [Organizer instructions](https://uk.linkedin.com/company/nousresearch).

Judges assess usefulness, reliability, polish and creativity, with preference for capabilities beyond what a prompt or skill could provide. [Organizer announcement](https://uk.linkedin.com/company/nousresearch).

## Catalog preparation

The source repository is public at `itsflownium/gambit-hackathon`, maintained by `itsflownium`, with the plugin at its root. The existing draft adds only `plugin-catalog/gambit.yaml` to the upstream repository. Update its source pin to a full **40-character commit SHA**, quote version `"0.3.0"`, match the manifest's `requires_hermes: ">=0.23.0"`, and retain `tier: community` and macOS-only scope. Re-pin documentation and screenshot URLs with the code, and update the PR's source/demo links and terminal disclosures. [Official submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).

Before updating the pin, rerun `hermes plugins validate /path/to/gambit --install-deps` against an anonymous checkout at the exact proposed commit. Also rerun current catalogue structure, payload, self-update and symlink checks. Public SDK/API use, no core overrides, compatible dependencies and accurate disclosures remain required. The README and PR disclose public Chess.com/Lichess requests, host provider use, Stockfish subprocesses, local storage and background workers. Stockfish is separately installed, not bundled or downloaded automatically. Keep runtime databases, credentials and production captures out of source. [Canonical catalogue rules and schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md).

## Current 0.3.0 checks

- Release labels are 0.3.0 across the plugin, Python package, dashboard and preview package.
- The final candidate suite passed 175 tests, with two existing dependency deprecation warnings. Real pseudo-terminal integration verifies actual curses input, one fixture-engine reply, refresh, resize, help, clean exit and terminal restoration. Profile-scoped help, Desktop contracts, compilation and generated-entry syntax checks also passed.
- The actual ASCII dashboard completed `1.f3 e5 2.g4 Qh4#` with GPT-6.1 Sol selecting both replies through the existing host provider, plus automatic `f3` feedback and requested level-one/level-two hints. These production interactions are separate from fixture-based PTY evidence.
- The official CLI one-shot JSONL model/tool cycle returned one completed Hermes reply, an exact anchored review request, actual model review and the board. Normal then completed one reply without automatic commentary, and an explicit request returned only a level-one clue. The official native Ink TUI passed bare `/chess`, move, requested clue and clean-exit checks. Combined host transport acceptance passed 24/24.
- The supported Git installer and a cold terminal launch passed in a fresh default Hermes home at the documented runtime candidate: no Desktop, named profile or copied auth. Missing Stockfish produced an actionable error; after configuring only the plugin engine path, Normal play returned one labelled local fallback with no feedback, help worked and quit returned 0.
- A stable candidate copy passed official `--install-deps` validation with actual dependency resolution/installation, all 16 checks, a safe security scan and no validator warnings. The anonymous public candidate also passed all 16 dependency-aware checks and current catalogue structure, payload, confinement and self-updater gates. The existing catalogue PR records the published pin.
- The verified terminal film is 88.000 seconds, 1080p30 H.264/AAC, with 18 English caption cues and nine external chapters. Full decoding, browser playback/seek, desktop/mobile caption fit, provenance and privacy checks passed. It replaces the earlier demo package; [capture notes](../demo/README.md) disclose source and editing limits.
- The standalone dashboard is a separate terminal session; the optional Desktop pane is not required. With `plugins.isolation: host`, standalone CLI registration is unavailable; `/chess` remains the conversation interface.
- Bare `/chess` starts a White, Balanced, Coach game when no game is selected; otherwise it refreshes the current board. Bare/start slash commands return portable text on every chat surface; graphical Desktop requests remain asynchronous.
- Ordinary CLI/TUI chat waits for one reply and follows an anchored review request in Coach mode. Slash shortcuts return board or engine evidence directly. Full-match recap completion is announced through Desktop; terminal chat can request the result later, and the standalone dashboard has no summary command.

## Historical local evidence

The [verification record](verification.md) preserves earlier macOS results: 86 behavioral tests, passing Desktop contracts, all 16 official validator checks without warnings, and Plugin Doctor discovery of eight tools and one hook for 0.2.4. Native play, hints, Coach feedback, imports and replay were checked, alongside two clean default-home installs. An earlier stalled-model test committed one legal backup at **59.607 seconds**. Those checks do not validate the changed 0.3.0 source or its new terminal demo.

## Decisions and verification still needed

- Publish the reviewed source and verified media through the source repository, choose the public merged release commit, repeat exact-pin checks and update the existing catalogue draft. Keep the PR in draft; do not create a replacement PR.
- Preserve the completed demo, narration, visible-content and metadata checks when publishing; verify final Git author/committer metadata uses the public maintainer identity.
- Preserve the capture disclosure: main linked-development take predates the final commit and exact in-memory source bytes were not frozen; the clean Normal take follows the core commit/source sync.
- Social video posting and final entry submission need separate authorization. Updating the existing catalogue draft does not perform them.
- Reopen the form before any entry attempt to inspect its current fields, status and terms. The organizer's LinkedIn shortlink resolved to the Typeform URL above, but its contents could not be loaded here. The original X posts returned HTTP 403; the organizer's own LinkedIn announcement supplied the entry instructions. Additional entrant eligibility, team, age or regional conditions were not verified. Local checks do not establish acceptance or eligibility.

For later questions, the announcement links the [Nous Research Discord](https://discord.gg/nousresearch). No external message was sent.
