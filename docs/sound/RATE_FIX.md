# VIDC1 sample-rate correction

The reported Lemmings symptom was nearly double-speed music with higher-pitched,
shorter effects. The original cleaned-3.60 SoundDMA source contains a VIDC1-path
register error in `WorkOutVIDCParams`: it computes and clamps the byte period in
r2, but stores r1 into `VIDCSFR_N`. The preceding division preserves r1=6.
Subsequent hardware programming subtracts two, yielding SFR=&104 for every rate.

The [public sound PRM](https://www.riscos.com/support/developers/prm/sound.html)
distinguishes the period per channel from the byte output period. At a 24 MHz
VIDC clock the latter is the former divided by channel count. The fix stores
r2, retaining the real channel scaling, clock conversion, clamping and IRQ
pipeline. There is no host-audio workaround or emulator modification.

## Before the fix

The public disk-loaded `!SndTest` calls Sound_Configure with 1, 2, 4 and 8
channels at both 48 and 80 microseconds. It waits for the genuine double-buffer
pipeline, then marks a 20-centisecond interval using OS_ReadMonotonicTime.
The read-only harness records VIDC SFR and actual DMA bytes at both endpoints.

[Captured observations](reports/pre-fix-rates.json) show SFR=&104 in every case,
with approximately 166,667 bytes emitted per second. Sound_Configure reports the
requested period even though the hardware receives a different value. Four
channels at 48 microseconds require 83,333 bytes/second, so the observed error is
exactly 2x. This reproduces a sufficient cause of the reported symptom. The
user later confirmed manually that Lemmings plays correctly on the fixed ROM.

The prior sound gate tested non-silence, genuine voices and scheduler operation,
but did not compare sample timing against elapsed time. This exposes that gap.

## Correction and regression gate

[Patch 0002](../../patches/sound/0002-vidc1-sample-period.patch) is separate from
the existing assembly adaptations. The manifest retains the original upstream
hash and records the corrected source hash. Patch verification reverses the
whole series back to the exact pinned public source and reapplies without fuzz.

`python3 tools/build_sound.py` requires identical normal/observer assemblies,
resolved symbols and independent ARM2 decoding. `python3 tests/run_sound.py`
now requires all eight channel/period combinations to program the expected SFR
and emit the expected number of bytes within one 16-byte DMA event. It repeats
across three cold machines alongside the existing voice, stereo and scheduler
tests. The kernel and emulator are unchanged.

All three cold machines pass with identical observations. The eight measured
rates match the requested settings within one DMA event.
[Acceptance](reports/rate-acceptance.json) and
[assembly verification](reports/rate-assembly.json) record ROM SHA-256
`361281151b3079b4046c72f3fb7cc4574ff01b04ce53e4fffa09a4c7e2d0d8b1`.
The installed integrated image is now
`bb9d384592b076b630c95ac174ca1985a97fe18dc70025985bae80f34a3063cf`,
which also corrects classic Wimp submenu messages. The same three-cold sound
gate passes on that image; see current acceptance
and [release integration](../archimedes-desktop/reports/integration.json).
Close and reopen the machine to reload it; Power Cycle retains the already
loaded image. The original diagnosis reports above retain their historical hashes.
