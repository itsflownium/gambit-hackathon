# Release checklist

Updated 9 November 2026. The earlier implementation and approved demo are merged in `itsflownium/gambit-hackathon`. Version 0.2.4 includes the reviewed native startup fixes and completed acceptance evidence. The [verification report](verification.md) records local evidence and its limits.

## Implementation

- [x] Board-only pane with a knight toolbar button and coaching in the existing chat.
- [x] Normal and Coach modes, with progressive hints available on request.
- [x] Exactly one opponent reply per accepted human move, with a hard 60-second deadline and labelled fallback.
- [x] Legal moves, both colours, promotion, endings, undo, saved matches and PGN export.
- [x] Public Chess.com and Lichess username searches with exact-match selection and source links.
- [x] Replay every half-move, practice recorded or alternative lines, and preserve the original match.
- [x] Position-anchored coaching, draft protection and separate conversation/profile state.
- [x] GG/fireworks after resignation, followed by a fresh playable board.
- [x] 86 Python behavioral tests and desktop contracts passed; all 16 official validator checks passed in both the normal Hermes installation and clean default homes, with no warnings.
- [x] Supported Git installations into two empty default Hermes homes passed on the development Mac, without a named profile or copied account credentials.
- [x] Board operations follow the visible chat without requiring a dedicated profile; fresh-chat play/import and stale-navigation guards have regression coverage.

## Demo and documentation

- [x] Include the revised 89-second demo, poster, English captions, eight chapter controls and local review player.
- [x] Show fresh GPT OAuth play, progressive hints and coaching; disclose the public SDK capture adapter, timing edits, still crops and unimplemented future ideas.
- [x] Verify 1920×1080 at 30 fps, H.264/AAC, full decoding and a chapter seek to the replay scene.
- [x] Include installation instructions, licenses, dependency notices and behavior disclosures.
- [x] Prepare event requirements, entry copy, a social-post draft and a catalog-entry draft.
- [x] Prepare the [optional second-computer checklist](second-device-check.md).

## Review and submission status

- [x] Initial implementation PR merged into this repository.
- [x] Revised live-demo and earlier profile-context fix merged; final demo approved.
- [x] Ordinary-chat routing and startup PR #3 merged.
- [x] Repair same-owner refresh cancellation, unrelated gateway discovery delays, startup connection lifetime and duplicate chat-title failures; add regression coverage.
- [x] Native regular-chat launch, Normal turn, requested OAuth hint and automatic Coach feedback passed with All profiles selected.
- [x] Fixed candidate passed clean default-home real-engine play, Undo, restart persistence, both public imports and replay navigation.
- [x] Native fresh-chat Chess.com picker preserved its username/results, opened the exact selected match and returned position-specific OAuth coaching.
- [x] Cold native launch restored the match, cursor and coaching transcript; live controls worked without recovery steps after installer work finished.
- [ ] Optional verification on another physical computer; other operating systems have not been verified.
- [x] Review the 0.2.4 startup fixes and verify that generated bundles match their source.
- [ ] Choose and validate the final merged release pin before any catalog submission.
- [ ] Separately authorize an upstream catalog PR, social post and organizer form submission.

New conversational coaching requires working access to the configured Hermes provider. Local board fallback and source-match replay are separate from that provider's availability. This repository PR does not submit a marketplace or hackathon entry.
