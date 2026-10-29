# Original-machine sound and Zarch launch

ArcLibre's sound profile uses the cleaned-3.60 SoundDMA 1.48, SoundChannels,
SoundScheduler, WaveSynth and Percussion implementations. The ARM2/MEMC1/IOC/
VIDC1a branches are retained; no IOMD/VIDC20 implementation is substituted.

## Reproduce the public gate

```
make arclibre-test
make arclibre-package
```

`tools/build_sound.py` assembles each module twice normally and once with the
observer, requires identical fully resolved AOF, and independently decodes every
emitted integer instruction. It checks processor-state settling, branch targets,
module SWI bases and SoundDMA's indexed dispatch table. Tokenised help is generated
from each original HelpSrc with the pinned public Tokenise tool. Original UK
Messages are installed under the names in the original Makefiles.

`tests/run_sound.py` launches the original `!SndTest` floppy application by a real
desktop double-click across three cold boots. It verifies Sound_Enable query,
Sound_Stereo set/query, a genuine unsupported Sound_Mode error, ChannelVoice,
WaveSynth-Beep, Percussion-Snare, Sound_Control and a real Sound_QSchedule event.
The harness requires new non-silent VIDC output after application launch and a
return to the four desktop tasks. All three observations match. Sampled ROM
instructions match independently decoded module bytes; all undefined exceptions
are classified software-FPA operations. No emulator changes or guest injection.

The patch series `patches/sound` reverses to every original pinned file hash.
Adaptations are AREA replacing LEADR, KernelEntry macro spelling, explicit ARM2
settling, canonical SWI base aliases and the original-machine workspace exports.
The VIDC20-only SWIs are excluded from the dispatch table and return the genuine
NoSuchSWI error on original hardware, rather than fabricated success.

## Workspace contract

The new `SoundWorkspace` header exports existing values from the unchanged,
restored KernelWS. The build checks each against the actual kernel symbol table.

| Contract | Value |
| --- | --- |
| IOCControlSoftCopy | &106 |
| SoundLevel0Base | &1F04000 |
| SoundDMABuffers | &1F06000 |
| SoundDMABufferSize | &1000, two buffers |
| TopOfDMAWorkSpace | &1F08000 |
| TopOfDMAPhysRAM | &80000, physical RAM offset |
| Buffer mappings observed in MEMC | &1F06000 → &7E000; &1F07000 → &7F000 |

SoundDMA derives the physical buffer address from this fixed contract. Runtime
captures record MEMC sound register writes, VIDC sample rate and stereo registers,
non-silent byte counts, sound hashes and actual logical-to-physical mappings.
The kernel SHA remains `cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30`.

## Private Zarch compatibility gate

The user's own `Zarch (1987)(Superior Software).adf` is an external,
read-only E-format fixture. SHA-256:
`bc082f7313cf8b20714f842cb30d5aec3eb4677f3acc3131f8b3235b20a6f86f`.
It is not copied into source or release archives. To repeat with that same
legitimately held image:

```
python3 tests/run_zarch.py '/path/to/Zarch (1987)(Superior Software).adf'
```

(This and the other private game gates are kept in the project's development
archive, with the game media, not in this repository.)

Three cold boots open the floppy through the drive icon and double-click
`!Zarch`. The unmodified loader kills/reinitializes the real sound modules and
loads the game, reaching its original entry at &DBA8 in USR26. Absence of its
optional `!OldCMOS` file is the only observed loader error. With the sound modules
missing, it instead enters its fallback reconfiguration/reset path.

Space at the title screen starts the game. Paired runs from the same snapshot
compare idle, thrust, thrust with sustained mouse steering, and firing. All show
the expected distinct rendered frames, with no new undefined instructions,
prefetch/data aborts or address exceptions. Sound DMA emits non-silent samples.
Image hashes and observations match across the three cold runs, and the original
disc hash remains unchanged. Private screenshots, instruction traces and state
captures are confined to `build/private-zarch/acceptance` and are never packaged.

This is a bounded launch and input/sound gate, not certification of the whole
game. Long sessions, all levels, pause/quit and score persistence, ARM3 timing and
physical hardware still need testing. The target remains unmodified RISC OS
3.11 applications and games; using the public 3.60 implementations does not
change that requirement.

## Subsequent sample-rate correction

The earlier non-silence gate did not establish accurate pitch or duration. The
[VIDC1 rate investigation](RATE_FIX.md) fixes a wrong-register store in the
original source and adds elapsed-time/DMA checks for eight configurations,
repeated across three cold machines. Its report identifies the newer exact ROM.
