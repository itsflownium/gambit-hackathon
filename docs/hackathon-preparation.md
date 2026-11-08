# Hackathon preparation — Gambit 0.2.2

Prepared 8 November 2026 for repository review. This source and demo PR is separate from the upstream catalog PR, social post and organizer form submission described below.

## Deadline and entry route

The organizer specifies **5 PM EST on 11 November** for this November 2026 event. The corresponding times are:

| Zone | Deadline |
| --- | --- |
| EST, UTC−05:00 | Wednesday **11 November 2026, 5:00 PM** |
| UTC | Wednesday **11 November 2026, 22:00** |
| Australia/Sydney, AEDT, UTC+11:00 | Thursday **12 November 2026, 9:00 AM** |

The time conversion uses `America/New_York` and `Australia/Sydney`. The announcement gives November 11 without spelling out the year; 2026 is the current event context. [Organizer announcement](https://uk.linkedin.com/company/nousresearch).

After the user separately authorizes the external work, the organizer requires:

1. A pull request adding the plugin to the [Hermes catalog](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog).
2. A working demo video **under 90 seconds**, posted on X and tagging **@NousResearch**.
3. Both the **catalog PR URL** and **X demo-post URL** submitted through the [organizer-linked Typeform](https://form.typeform.com/to/FwJLvOln). The form can be submitted once the PR is open; a merged PR is not stated as an entry prerequisite. Maintainers initiate catalog checks and review separately. [Organizer instructions](https://uk.linkedin.com/company/nousresearch).

Judges assess usefulness, reliability, polish and creativity, with preference for capabilities beyond what a prompt or skill could provide. [Organizer announcement](https://uk.linkedin.com/company/nousresearch).

## Catalog preparation

The eventual submission needs a public, cloneable HTTPS repository and a loadable plugin at a full **40-character commit SHA**. Add `plugin-catalog/gambit.yaml` to the upstream repository; use the correct maintainer, declared capabilities, quoted version `"0.2.2"`, and a truthful SemVer `requires_hermes` floor matching the plugin manifest. Include UI screenshots and explain the plugin's public Hermes surfaces. [Official submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).

Before opening that PR, rerun `hermes plugins validate /path/to/gambit --install-deps` against the exact proposed commit. Public SDK/API use, no core overrides, compatible dependencies and accurate disclosures remain required. The README and PR should disclose public Chess.com/Lichess requests, optional official Stockfish download, its subprocess, local storage and background workers. Do not include an installed engine binary, runtime databases or credentials in source. Upstream downloads at setup must be official, checksum-pinned and disclosed. [Canonical catalog rules and schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md).

## Completed local evidence

- **Version 0.2.2** matches `plugin.yaml` and `pyproject.toml`.
- **82 Python behavioral tests passed**, plus desktop contracts, syntax and compilation checks.
- **All 16 local catalog-validation checks passed without warnings**; Plugin Doctor reported eight tools and one hook. This is local validation, not catalog approval.
- Native play, Coach/Normal behavior, exact imported-match selection, immutable replay/practice, draft protection and the one-minute fallback are recorded in [verification.md](verification.md). The real stalled-model check committed one legal backup at **59.607 seconds**.
- Screenshots, disclosures and a [local demo outline](demo.md) exist. These evidence statements come from the current [verification record](verification.md); this research pass did not rerun the test suite.

## Decisions and verification still needed

- Repository owner/name is `itsflownium/gambit-hackathon`, with `itsflownium` as maintainer. Choose the final merged release commit to pin for a separate catalog PR.
- Approve the final demo, narration, visible usernames and X account. Show actual plugin operation; label cuts or previously imported data where relevant.
- Decide separately whether to authorize the catalog PR, social video post and final entry submission. The implementation PR includes the repository's source and demo only.
- Reopen the form before any entry attempt to inspect its current fields, status and terms. The organizer's LinkedIn shortlink resolved to the Typeform URL above, but its contents could not be loaded here. The original X posts returned HTTP 403; the organizer's own LinkedIn announcement supplied the entry instructions. Additional entrant eligibility, team, age or regional conditions were not verified. Local checks do not establish acceptance or eligibility.

For later questions, the announcement links the [Nous Research Discord](https://discord.gg/nousresearch). No external message was sent.
