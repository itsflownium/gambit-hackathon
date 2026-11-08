# Release checklist

The implementation and demo are proposed for review in `itsflownium/gambit-hackathon`. The [verification report](verification.md) records local evidence and its limits.

## Implementation

- [x] Board-only pane with a knight toolbar button and coaching in the existing chat.
- [x] Normal and Coach modes, with progressive hints available on request.
- [x] Exactly one opponent reply per accepted human move, with a hard 60-second deadline and labelled fallback.
- [x] Legal moves, both colours, promotion, endings, undo, saved matches and PGN export.
- [x] Public Chess.com and Lichess username searches with exact-match selection and source links.
- [x] Replay every half-move, practice recorded or alternative lines, and preserve the original match.
- [x] Position-anchored coaching, draft protection and separate conversation/profile state.
- [x] GG/fireworks after resignation, followed by a fresh playable board.
- [x] 86 Python behavioral tests and desktop contracts passed; all 16 official validator checks passed in the prepared test environment. See the verification report for the installed-environment limitation.
- [x] Fresh Hermes-profile installation passed on the development Mac.
- [x] Board operations follow the visible chat without requiring a dedicated profile; fresh-chat play/import and stale-navigation guards have regression coverage.

## Demo and documentation

- [x] Include the revised 89-second demo, poster, English captions, eight chapter controls and local review player.
- [x] Show fresh GPT OAuth play, progressive hints and coaching; disclose the public SDK capture adapter, timing edits, still crops and unimplemented future ideas.
- [x] Verify 1920×1080 at 30 fps, H.264/AAC, full decoding and a chapter seek to the replay scene.
- [x] Include installation instructions, licenses, dependency notices and behavior disclosures.
- [x] Prepare event requirements, entry copy, a social-post draft and a catalog-entry draft.
- [x] Prepare the [optional second-computer checklist](second-device-check.md).

## Remaining review and submission steps

- [x] Initial implementation PR merged into this repository.
- [x] Revised live-demo and earlier profile-context fix merged; final demo approved.
- [ ] Review the new ordinary-chat routing and startup PR.
- [ ] Repeat fresh native-window startup and default-backend chat creation after the ongoing Hermes update and dependency preparation finish.
- [ ] Optional verification on another physical computer; other operating systems have not been verified.
- [ ] Choose the final merged release commit and validate that exact pin before any catalog submission. The ordinary-chat routing PR still needs review.
- [ ] Separately authorize an upstream catalog PR, social post and organizer form submission.

New conversational coaching requires working access to the configured Hermes provider. Local board fallback and source-match replay are separate from that provider's availability. This repository PR does not submit a marketplace or hackathon entry.
