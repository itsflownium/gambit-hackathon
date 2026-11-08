# Gambit demo

[![Watch Gambit](poster.png)](Gambit-Demo-Review.mp4)

[Watch the 86-second demo](Gambit-Demo-Review.mp4). It includes original cyan motion graphics, an original ambient score, calm synthetic narration and actual product captures. Download this folder and open `Review.html` locally for chapter buttons and optional English subtitles, or play the MP4 directly.

## Included files

- `Gambit-Demo-Review.mp4`: 1920×1080, 30 fps, H.264 video and stereo 48 kHz AAC.
- `poster.png`: branded demo poster.
- `captions.srt` and `captions.vtt`: 16 English narration cues.
- `chapters.json`: nine chapter start times.
- `Review.html`: local video player with captions and chapter navigation.
- `audio-timings.json`: narration timing and original-score provenance.
- `video-verification.json` and the SHA-256 file: export checks and file integrity.

## What the film shows

The unchanged shared board runs against the real plugin API and local Stockfish. The film shows a public Chess.com username search and exact match selection, one human move followed by one reply, recorded `...c5` → `Nf3`, alternative `...e6` → calculated `d4`, and actual GG/fireworks/reset. Browser replies are identified as engine-assisted. A native Hermes capture provides a genuine saved explanation of Black's `1...c5`, labelled as an earlier verified run.

The film is edited for length. It does not claim instantaneous inference, measured rating improvement or catalog acceptance. Its ending explicitly labels recurring-mistake analysis and targeted practice as future ideas, not implemented features.

The original score, *Quiet Continuation*, uses local additive synthesis without samples or external tracks. Narration uses the installed macOS Daniel voice. Chess piece artwork is by Colin M. L. Burnett via python-chess, using the GPL option documented in [THIRD_PARTY.md](../THIRD_PARTY.md). Gambit's knight logo and board design were created for this plugin. Stockfish is separately installed and is not bundled in this repository.

Raw desktop captures, runtime databases, installed engines and private production files are excluded. [Entry copy](../docs/hackathon-entry.md), [event requirements](../docs/hackathon-preparation.md) and the [release checklist](../docs/release-checklist.md) accompany the source. Catalog submission, social posting and the organizer form are separate from this repository PR.
