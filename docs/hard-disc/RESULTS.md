# Original ST506 restoration — first checkpoint

The original A1 ADFS build includes the real byte-addressed ST506 driver
(`Top16Write=true`, `BigDisc=false`), but the pinned cleaned-3.60
`ReadNewCMOS0` unconditionally clears its configured drive count. The new
`ArcLibreST506` opt-in removes that suppression. It does not select a later
IDE/IOMD profile or replace the driver. The default historical build retains
exactly the same bytes.

`python3 tools/build_hard_disc.py` assembles twice plus the observer and
independently decodes all 8,115 instructions, including branch destinations
and 96 processor-state sequences. No relocations or unresolved symbols remain.
`python3 tools/build_arclibre_rom.py --with-hard-disc` joins an isolated
candidate without installing it. Kernel bytes are unchanged.

`HardDiscProbe ROM BUILD_DIRECTORY OUTPUT [reopen]` creates a disposable
615-cylinder, four-head, 32-sector/track, 256-byte-sector old-map disk, starts
at the reset vector, and uses real keyboard input to catalogue/read/copy/
dismount/read it through FileSwitch, FileCore, ADFS and the HD63463. `reopen`
starts a separate fresh machine using the existing disk file. Eleven sector
writes and successful reopening were observed. An independent host reader
checked both actual file payloads, the directory checksum and both free-map
checksums; compact evidence is in `ST506.json`. Detailed instruction traces,
HD63463 commands and screenshots are under `build/hard-disc/probe-write`.

The fixture contains only ArcLibre-authored text. No proprietary media or ROM
is required. MacArch was unchanged. This is a storage checkpoint, not yet the
Edit desktop persistence milestone or a general hardware compatibility claim.
