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
- [x] 82 Python behavioral tests and desktop contracts passed; all 16 local Hermes validation checks passed.
- [x] Fresh Hermes-profile installation passed on the development Mac.

## Demo and documentation

- [x] Include the 86-second demo, poster, 16 English caption cues, nine chapter controls and local review player.
- [x] Identify engine-assisted footage, the genuine earlier native review and unimplemented future ideas.
- [x] Verify 1920×1080 at 30 fps, H.264/AAC, full decoding and a chapter seek to 49 seconds.
- [x] Include installation instructions, licenses, dependency notices and behavior disclosures.
- [x] Prepare event requirements, entry copy, a social-post draft and a catalog-entry draft.
- [x] Prepare the [optional second-computer checklist](second-device-check.md).

## Remaining review and submission steps

- [ ] Review and merge this repository's implementation PR.
- [ ] Optional verification on another physical computer; other operating systems have not been verified.
- [ ] Choose the final merged release commit and validate that exact pin before any catalog submission.
- [ ] Separately authorize an upstream catalog PR, social post and organizer form submission.

New conversational coaching requires working access to the configured Hermes provider. Local board fallback and source-match replay are separate from that provider's availability. This repository PR does not submit a marketplace or hackathon entry.
