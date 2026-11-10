# Gambit terminal demo

[![Watch the 88-second Gambit demo](poster.png)](Gambit-Demo-Review.mp4)

[Watch the film](Gambit-Demo-Review.mp4), or open [Review.html](Review.html) for nine chapter controls and optional English captions. The video is 1920×1080, H.264 at 30 fps, with AAC stereo audio at 48 kHz.

The fresh terminal session shows the real board and public move status, a deliberately short teaching game `1.f3 e5 2.g4 Qh4#`, requested hint levels one and two, and genuine Hermes feedback explaining the exposed king. Both opponent replies were stored as `origin=hermes`; the model was GPT-6.1 Sol, selected through Hermes before capture in an isolated demo profile using the existing authorized Hermes OAuth connection. The clean Normal-mode turn is `1.e4 c5`, with a genuine Hermes reply and no automatic coaching.

A real public Chess.com search selects match `186751169392`, from Black's perspective. Practice `...c5` receives the exact recorded `Nf3`; alternative `...e6` receives a fresh Hermes-selected `d4`. The imported original retains all 15 half-moves and its `1-0` result. The source move hashes before and after practice match. The final replay position is labelled `15 / 15`; its `Qxe7+` is a check, and the film makes no mate claim about the imported match.

Actual terminal sessions are rendered faithfully from timestamped ANSI captures. Every application cell and response comes from those captures. Added presentation is limited to outer terminal chrome, chapter labels and the visible “cuts shorten waits” disclosure. All selected source spans play at their original speed; cuts remove waits between them. The terminal is rendered at 12 fps and encoded at 30 fps with repeated frames. Full waits and failed or discarded takes remain private. This is an edited demonstration, not a latency or reliability benchmark. [The exact edit spans](edit-timeline.json) and [capture provenance](source-provenance.json) accompany the film.

The Coach recording used the supported linked local Gambit 0.3.0 terminal candidate. Source files were refreshed during the run after Python had imported its modules, so the exact in-memory code bytes were not frozen. The repository revision and current tree fingerprint are labelled as observations made after capture. They are not an immutable capture-time commit claim. The clean Normal recording began after the final core commit and source sync. One genuine Unicode take was discarded for piece readability; a fresh Normal take keeps earlier Coach history out of that scene.

Narration retains the approved Kokoro v1.0 `af_heart` synthetic voice, rendered locally through kokoro-onnx 0.6.1 at speed 0.95. The original score is *Quiet Continuation*, made with local additive synthesis without external samples or tracks. [Audio timings](audio-timings.json) include the original-model phoneme timing used for the 18 English caption cues.

Private runtime homes, raw logs, credentials, databases, engines, model weights and local machine paths are excluded. The terminal text scan and visual review are reported directly; no successful OCR claim is made. Catalog submission, social posting and organizer submission remain separate actions.
