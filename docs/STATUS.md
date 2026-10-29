# Status

ArcLibre 0.9. The exact ROMs, disc and test reports of the current release
are recorded in [manifests/arclibre-desktop-release.json](../manifests/arclibre-desktop-release.json)
and summarised in [the integration record](archimedes-desktop/reports/integration.json).

## What is in it

The 2 MB ROM holds the kernel and 73 modules, almost all built from the
original Acorn sources. DOSFS, !Alarm and printing, which RISC OS 3.11 had in
ROM, are on the extras disc, and the 4 MB ROM has them built in. !Calc,
!Configure, the palette utility and ARM3Support are new ArcLibre
replacements written to match the 3.11 originals, because their sources
aren't public. [The gap matrix](system-audit/GAPS.md) compares the set with
3.11's, module by module. 20 KB of the 2 MB ROM is free.

It runs on the A300 and A400 series and the A3000 (ARM2, IOC, 1772 floppy
controller) and on the A5000, A3010, A3020 and A4000 (ARM3 or ARM250, IOEB,
82C710/711), detecting which at reset as 3.11 does. The tested machine is an
emulated A440/1 with an ARM2; the A5000, A3010 and A3020 are tested for their
I/O.

## What has been tested

Every gate in the release suite passes on the release's exact ROMs, usually
with three cold boots and a negative control (see [BUILD.md](../BUILD.md)).
Among them: the desktop, Filer and Pinboard by mouse and keyboard; Edit,
Draw and Paint editing, saving and reopening, including Paint-to-Draw
interchange; TaskWindow pre-emption and the software floating point
registers; sound DMA timing; floppy and hard-disc reading, writing and
formatting; PC discs through DOSFS; Econet file serving against a host
server; printing to dot-matrix, LaserJet and PostScript, with the output
decoded and checked; serial, parallel and expansion cards; the A5000's
floppy, IDE, serial and parallel; the IIC clock; and the Debugger.

Two commercial games, Zarch and Nevryon, have been run in bounded private
gates (their discs are not distributed): Zarch to gameplay with keyboard,
mouse and sound; Nevryon to its title screen.

## What has not

- **Real hardware.** Nothing has run on a physical Archimedes or ROM board;
  every test is in MacArch.
- **Full 3.11 compatibility.** The gates are bounded: they establish that
  each component works for the cases tested, not that every 3.11 program
  will run. [The gap matrix](system-audit/GAPS.md) lists what is known to
  differ or be missing.
- **Components without public sources:** BroadcastLoader (its CMOS bits are
  only stored), AUN remote printing, and MakePSFont, so outline fonts on a
  PostScript printer may not print correctly.
- **Untested:** DOSFS's 1.2M and Atari formats and `*Format` of them, PCL
  compression modes, the A4000 and the A5000 with other processors as
  separate runs.
- **An emulator limit:** MacArch's A5000 floppy controller doesn't raise
  disc-changed as a real drive does at power-on, so copying between a PC
  floppy and another drive fails there ("Please insert disc"); see
  [new I/O](new-io/RESULTS.md).

## What could come next

- Rebasing the source provenance from the 4corn mirror onto RISC OS Open's
  GitLab when it is back online ([LICENSING.md](../LICENSING.md)).
- Testing on real hardware.
- More 3.11 application and game testing.
- About 12 KB of ROM space, measured but not taken: tokenising `*Help` text as
  3.11 did, and switching off post-3.11 features
  ([network results](network/RESULTS.md)).
