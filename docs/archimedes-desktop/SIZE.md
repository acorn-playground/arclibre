# ROM space without removing features

The maintained C builds now use `-Os` in place of `-O2`. SharedCLib saves
8,652 bytes, FilerAct 1,248, Edit 316, Draw 9,472 and Paint 3,972: **23,660
bytes total**. No application, sprite, font, message or runtime facility is
removed. Assembly modules are unchanged.

The intermediate 2 MiB ROM uses 1,883,420 bytes and leaves 213,732 bytes free.
Its exact hash and regression evidence hashes are in
the measurement report. This is a historical
size milestone; later service additions consume some of that space.

Size optimisation exposed an existing 64-bit-host GCCSDK backend bug in signed
APCS frame offsets. The compiler is corrected at source, with O2 and Os leaf
and large-frame stacked-argument checks in the public C ABI fixture. See
[the toolchain notes](../desktop-c/TOOLCHAIN.md). No compiler-output text hack
substitutes for the correction.

Two complete C/application builds produce identical bytes. All retained
cold-reset desktop, TaskWindow/filter, submenu, sprite, Palette, sound, drag,
filing/C ABI, Edit, Draw, Paint and 18-machine edit/save/reopen tests pass on the
smaller ROM. The private Zarch and Nevryon regressions also pass; their media
are not included in the source or ROM packages. This does not establish every
application path or a complete RISC OS 3.11 replacement.

The subsequent integrated profile adds DeviceFS, SystemDevices, PipeFS, RamFS,
RAMFSFiler, Free, ScreenBlanker and StringLib. Stable relative C source paths
save another 36 bytes. It uses **1,916,308 bytes**, leaving **180,844 bytes**
(176.6 KiB) free, with all three original editors still in ROM. This is only
9,228 bytes larger than the previous `bb9d3845…` released image despite the
eight added services. The [current integration report](reports/integration.json)
identifies the delivered bytes and completed gates; intermediate results above
remain separate historical evidence.


Squash, Chars and Help subsequently add 39,724 bytes including their resources.
Replacing the host-calendar C-library identification with `[ArcLibre]` saves
four bytes. IIC and RTCAdjust then add 3,136 bytes. Compacting Chars and Help
with the ArcLibre BASIC squish tool saves 11,540 bytes and stripping Messages
comments 5,316; Alarm then adds 84,436. The original Debugger (8,852 bytes),
the 3.11-style PaletteUtil (4,916, replacing the 3,304-byte Palette), !Calc
(4,952) and !Configure (20,476) then add 38,360 bytes in all; DOSFS is on a
separate disc. The delivered FileCore (no FSLock) adds 24 bytes and ARM3Support
1,160. Moving Alarm to its own disc frees 83,796 bytes with its resources;
the Archimedes colour dialogue for Draw and Paint adds 3,236, the six
networking modules 67,216 and !Configure's Net section (with its three sprites) 3,868.
The 3.11 kernel restorations (branch vectors, OS version, keyboard ID
acknowledge) and the ArcLibre 0.8 version text save 156 bytes. The original
Podule manager, serial and parallel drivers add 19,780 bytes with their
messages; printing ships on its own disc. The current ROM uses
**2,076,436 bytes**, leaving **20,716 bytes (20.2 KiB)**.
All three original editors remain
in ROM; the BASIC applications keep their licence REM lines.
