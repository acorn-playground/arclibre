# RISC OS 3.11 standard-service audit

ArcLibre now has a usable desktop and the original Draw, Paint and Edit, but
it is not a complete RISC OS 3.11 replacement. Comparing actual ROM headers
with the user's reference machine gives **44 matching module titles, 43 absent
titles and one partial replacement, ArcPalette for PaletteUtil**. ArcLibre has
45 module identities in total, including the kernel's UtilityModule. These
counts measure presence, not a percentage of software compatibility.

The [complete gap matrix](GAPS.md) separates ordinary services, applications,
printing, hardware-specific services, networking and historical patch markers.
The [actual command inventory](COMMANDS.md) comes from the assembled ROM rather
than source filenames or the existence of headers.

## Reference and method

The user supplied four `*ROMModules` screenshots on 26 October 2026:
[1](reports/riscos311-rommodules-1.png),
[2](reports/riscos311-rommodules-2.png),
[3](reports/riscos311-rommodules-3.png),
[4](reports/riscos311-rommodules-4.png).
Together they cover all 88 system-ROM entries. Every title and version matches
the earlier [published observed 3.11 listing](https://www.chiark.greenend.org.uk/~theom/riscos/mods/311.html).
That web listing was initially obtained through its search-index copy after
direct fetching timed out; the supplied screenshots now provide independent
direct evidence. Machine model was not supplied. This is an observed 3.11
configuration, not a claim about every retail ROM or expansion configuration.

The screenshots show 77 active modules, one running module (ShellCLI), and ten
dormant modules. That explains the earlier 78-entry `*Modules` listing.
Dormant is not absent: ROMModules enumerates ROM residents while Modules lists
installed modules. See the [original module documentation](https://www.riscos.com/support/developers/prm/modules.html).
No reference ROM bytes, code, fonts or sprites were read or extracted.

[The baseline manifest](../../manifests/riscos311-module-baseline.json) stores
the observations and screenshot hashes. Run:

```sh
python3 tools/audit_system.py
```

The tool verifies the current ROM hash against its layout, reads each module
header and its bounded command records, and separately includes the kernel's
system-command pseudo-module. The latter is essential: commands such as Spool,
Load and Save are not entries in UtilityModule's header table. The checked-in
[inventory](reports/inventory.json) covers ROM
`294d5aec83438e1aad9a69bbf5b5c562f6187aa21f7fac246d0a0e79be2beacc`.
It contains 151 ordinary command entries, 14 filing-system command entries,
30 configuration entries, four help-only entries and two help-code entries.
Counts are records, not necessarily unique command spellings. In particular,
`*Commands` and `*FileCommands` have help callbacks, not ordinary code offsets.

This is a bounded module/command-registration audit. It does not establish
all SWI reasons, error semantics, aliases, UKCommand service handlers, external
programs or all hardware behaviours. A missing module name alone does not prove
every related kernel operation is absent. Existing headers alone do not provide
the corresponding runtime SWIs. Reference command output would further refine
the comparison; it is not required to establish the module gaps below.

## Findings that affect implementation

- **TaskWindow is a real missing capability.** The coherent public candidate is
  `Desktop/TaskWindow` at `9d0a32bfcc51b43840d28ef8a23713061834b6f2`.
  Its `s/Taskman` exports TaskWindow and the ShellCLI task commands, and uses
  environment handlers, vectors, Wimp slots and parent/child messages. Its
  `UpCall_Sleep` handler explicitly accommodates PipeFS. The source scan found
  no direct Filter or DeviceFS SWI calls in this candidate; those should not be
  invented as mandatory dependencies. Its private WimpSpace/PublicWS imports
  still need reconciliation with the restored workspace before assembly.
- **DeviceFS/SystemDevices and PipeFS are missing, despite working ADFS.**
  DeviceFS is the character-stream framework. SystemDevices supplies names
  such as `vdu:`, `kbd:` and `null:`; PipeFS supplies real pipes and PipeCopy.
  BufferManager is present, but does not replace those modules. Serial and
  parallel drivers require their own original-machine integration.
- **Free is not the same as `*Free`.** FileCore already supplies the command.
  The missing Free module supplies the desktop free-space viewer and ShowFree.
  Similarly, the build's host Squash compressor is not a guest Squash module.
- **RAM filing, DOS filing and several utilities are absent.** RamFS,
  RAMFSFiler, DOSFS, FilterManager, ScreenBlanker, RTCAdjust, StringLib and
  Debugger have pinned candidate sources but no integrated runtime gate.
  The existing ADFS/ST506 tests do not cover these facilities.
- **The remaining bundled apps need actual implementations and reviewed
  resources.** Alarm, Chars, Help and Configure have cohort candidates. The
  available SciCalc Makefile identifies `!SciCalc`, not the observed `!Calc`;
  no matching calculator implementation was established. ArcPalette remains
  a replacement with a narrower feature set: its mode selector works, but
  original file/persistent-setting workflows and the complete PaletteUtil
  contract are not implemented.
- **Do not import ARM600 support as ARM3Support.** The examined `HWSupport/ARM`
  cohort calls itself `ARM` and explicitly initializes only for ARM600 in
  `s/Module`. It is rejected for this purpose. ARM3 cache/control behaviour
  remains a separate original-machine requirement, even though ARM3Support
  is dormant on the user's current reference machine.
- **Three absent names are historical patch identities.** Maintained
  `src/ADFS/s/Fixes`, fix 9, records incorporation of the ADFSUtils correction.
  The cohort `Desktop/WimpUtils/s/WimpUtils2` and
  `Utilities/Patches/IRQUtils2/s/IRQUtils2` are Acorn's original empty patch
  marker modules, not missing runtime engines. The earlier WimpUtils source
  patches Wimp 2.00 and must not be applied blindly. Do not add synthetic
  success modules to improve the count. Whether legitimate compatibility
  markers are required by old `RMEnsure` scripts remains a separate decision.
- **Printing and networking are substantial independent features.** The
  roster includes the manager, PDriver/PDriverDP, dumper support, a real dumper
  and device paths; a print dialog alone does not deliver printing. Networking
  is not all-or-nothing in the reference listing: NetFiler/NetStatus are active
  while transport/filing modules can be dormant. Podule and IIC interfaces also
  need specific validation; kernel CMOS access is not a complete IIC API test.

## Source and licensing boundary

The [candidate record](reports/source-candidates.json) covers 42 specifically
selected repositories. For 41, it identifies the exact commit whose **subject**
is `Import from cleaned 360 CD`, along with the repository URL and LICENSE hash.
Matching commit bodies alone is unsafe: manufactured CVS branch commits also
quote that phrase. NetUtils has no such exact import subject in the available
local history. BroadcastLoader, original !Calc, PaletteUtil and ARM3Support are
not established by this bounded scan; this is not a claim that no public source
exists anywhere.

Each of those 41 pinned LICENSE files contains the Apache License 2.0 text.
This records notices, not blanket clearance of every asset or a completed
dependency review. Before importing a selected app, review its actual templates,
sprites, messages, fonts, libraries and generated tools and record individual
input hashes under the existing [licensing policy](../../LICENSING.md).
No upstream runtime source, new asset or dependency was added by this audit.
The 41 candidates include rejected or historical alternatives; they are not
41 ready-to-integrate missing modules.

To inspect a candidate reproducibly, use its recorded repository and full pin:

```sh
git -C references/RiscOS/Sources/Desktop/TaskWindow show \
  9d0a32bfcc51b43840d28ef8a23713061834b6f2:s/Taskman
```

## Recommended next milestones

1. **TaskWindow and filter contracts.** Port the real TaskWindow and
   FilterManager candidates as separately tested components. Exercise Edit's
   task window, a CPU-bound BASIC program while another desktop task stays
   responsive, input/output, suspend/resume, escape, normal exit and errors.
   Verify USR26 context/slot restoration and repeated cold runs. For filters,
   cover ordering, claimed events, deregistration and task death. Do not use a
   cooperative substitute for TaskWindow pre-emption.
2. **Streams and everyday filing.** DeviceFS/SystemDevices and PipeFS, then
   RamFS/RAMFSFiler/Free and DOSFS. Gate real reads/writes/EOF, blocking and
   cleanup, RAM-disk resize/full errors, desktop free-space updates, and
   independently checked FAT media. Keep the existing ADFS/ST506 regressions.
3. **Complete the standard utilities.** Review/import Alarm, Chars, Help,
   original-machine Configure, ScreenBlanker, RTCAdjust, StringLib and Squash;
   give each a public functional test. Resolve original Calc provenance and
   complete Palette workflows without presenting SciCalc as the original.
4. **Printing, hardware and wider compatibility.** Select a genuine printer
   pipeline and test output bytes/errors. Add hardware-specific serial,
   parallel, podule and ARM3 gates; retain networking as a deliberate profile
   with explicit unsupported services until implemented. Broaden application,
   media-error and long-session tests, then test physical ARM2/ARM3 machines.

The current 2 MiB ROM has only **203,908 bytes free**. Measure each newly built
component and its resources before deciding ROM residency. Optional resources
can be supplied on a documented boot/support disk where the compatibility
contract permits; silently dropping expected APIs to make the image fit is
not acceptable. Neither an automatic ROM-size increase nor a switch to later
RISC OS compatibility is implied by this audit.

Existing milestones remain bounded: Draw/Paint/Edit now pass the expanded
[editing/interchange gate](../graphics-apps/EDITING.md), SpriteUtils passes its
[public command gate](../spriteutils/RESULTS.md), Zarch has bounded gameplay
coverage and Nevryon reaches its title screen. Printing, full game playthroughs,
all application operations and physical-machine compatibility remain unproven.

The Palette label update is separately [built, tested and installed](PALETTE.md).
No emulator changes were made. Full-release evidence remains attached to its
original ROM hash; this audit does not relabel earlier tests as new execution.

## Follow-up: task services

The [TaskWindow/FilterManager milestone](../task-services/RESULTS.md) implements
the first recommendation. The original audit evidence above remains tied to its
recorded ROM. The integrated tree now has 47 module identities: 46 matching
reference titles, 41 absent reference titles and one partial Palette replacement.
Use `python3 tools/audit_system.py` to regenerate the current ROM inventory.

## Follow-up: streams and RAM filing

The default candidate now contains DeviceFS, SystemDevices, PipeFS, RamFS,
RAMFSFiler and Free. Its actual header inventory has **53 module identities**:
52 matching reference titles, 35 absent titles and one partial Palette
replacement. Dedicated stream and RAM runtime gates pass; the full combined
release regression is tracked in the respective result documents. DOSFS is
still absent. The 2 MiB candidate leaves **186,156 bytes free**, with Draw,
Paint and Edit retained in ROM; compiler size optimisation recovered 23,660
bytes before adding these services. These are presence and bounded runtime
results, not a complete compatibility percentage.

## Follow-up: original standard utilities

ScreenBlanker and StringLib now pass their dedicated cold runtime gates and are
in the default source profile. The [current inventory](reports/current-inventory.json)
has **55 module identities**, with **54 matching reference titles, 33 absent
titles and one partial Palette replacement**. The ROM leaves **180,844 bytes
free**. These counts still measure identities rather than compatibility.
The [gap matrix](GAPS.md) now marks implemented rows explicitly.

DOSFS remains withheld pending [review of its embedded x86 boot template and
module-header tool](../dosfs/RESULTS.md). Squash, RTCAdjust/IIC and the remaining
bundled utilities are still missing. The host SDK was narrowed to remove unused
restricted CMunge code; no such code was used by the working ROM.


## Follow-up: Squash, Chars and interactive Help

The [original utility restoration](../desktop-utilities/RESULTS.md) adds Squash,
Chars and Help. Their dedicated final-ROM gates pass across three cold repeats,
including independent decompression, interleaved workspaces and real desktop
input/help-message lifecycles. IIC, RTCAdjust and Alarm followed, then the
original Debugger and the new ArcLibre PaletteUtil, !Calc, !Configure and
ARM3Support, then the original networking modules (Econet, BBCEconet, NetFS,
NetFiler, NetPrint, NetStatus), with Alarm moved to its own disc to make room,
then the original Podule manager and serial and parallel drivers, with printing
on its own disc. The current inventory has **74 module identities, all matching reference
titles** (four of them, !Calc, !Configure, PaletteUtil and ARM3Support, are
ArcLibre replacements, not the original code), and **14 absent titles**. It
leaves **20,716 bytes free**, retaining Draw, Paint and Edit. DOSFS, !Alarm and
printing (!Printers and its four modules) ship on separate discs.
These are identity counts, not a compatibility percentage.

The original BASIC tokens and licence REMs remain in ROM. Selected resources
come from the same component pins, with the original flat Help template. The
C library's build-date identification is now fixed to make builds reproducible
across days. RTCAdjust/Alarm are the next practical utility milestone; DOSFS
still needs the separately recorded asset/tool review.
