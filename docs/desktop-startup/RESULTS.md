# ArcLibre desktop ROM milestone

The original Desktop startup application now runs from the experimental ROM,
starts Filer, ADFSFiler, TaskManager and Pinboard, sends Service_StartedWimp and exits.
The remaining four real user-mode tasks continue polling. A physical mouse
Select event on the icon bar opens TaskManager. Pinboard supplies the background
window and clears the welcome screen normally.

The target remains RISC OS 3.11 compatibility on original ARM2/ARM3 hardware.
A working desktop start from the public 3.60 implementation cohort does not
establish compatibility with arbitrary applications or games.

## Reproduce

On the supported macOS host with the documented host tools:

```sh
make arclibre-test
make arclibre-package
```

The first command reconstructs the exact filing baseline, builds all providers,
assembles the startup/provider and original-machine sound components, verifies source patches, joins the
separate experimental ROM and tests three fresh power-ons. The package step
also requires the retained base, rendering, font, FPA, Wimp and multitasking
acceptance reports. To regenerate these:

```sh
ARCLIBRE_OUTPUT="$PWD/build/desktop-baseline" make test desktop-test multitask-test
```

ROM: `build/arclibre/arclibre.rom`, delivered as `dist/arclibre.rom`.
SHA-256: `94fb12c8fdde58bff239890de5f66f95bf6b4590f7a7cdb60d2812903a6a45a0`.
Sources: `dist/arclibre-source.tar.gz`. Evidence and licences accompany the
`dist/arclibre-desktop-experimental.tar.gz` bundle.

## Machine configuration

Use an A440/1, ARM2, 4 MB RAM, standard monitor, WD1772, one floppy drive and no
hard discs. The test uses ordinary CMOS settings: Floppies 1, Drive 0, NoBoot,
Language 10 and WimpMode 12. An independently generated CMOS image and MacArch
machine JSON are packaged; neither contains any proprietary ROM material.
A Delete power-on initializes CMOS; the machine profile reapplies these settings.
CMOS byte 135 is set to 1 in full: this ADFS cohort also reads IDE counts in
bits 6–7. Masking only bits 0–5 left a phantom :4 drive icon. No hard-disc
controller code was changed. With an existing configuration, the equivalent
commands at Supervisor are:

```text
Configure Floppies 1
Configure HardDiscs 0
Configure IDEDiscs 0
Configure Drive 0
Configure NoBoot
Configure Language 10
Configure WimpMode 12
Desktop
```

NoBoot disables automatic disc boot, not desktop startup. The earlier baseline
snapshot had a real Boot$Error from attempting an unavailable drive. The isolated
probe exercised the genuine Cancel button before startup; the final cold ROM
profile avoids the configuration error and reports no desktop errors.

## Source and packaging changes

The full source pins and original/current hashes are in
`manifests/desktop-startup-inputs.json`; see `patches/desktop-startup/README.md`
for the reviewable patches. The assembly gate compares two ordinary builds
and an observer build, rejects unresolved symbols/relocations and independently
audits ARM2 integer instructions, code/data boundaries, direct branches and
processor-state settling. Filer help is regenerated with the public tokeniser.

The kernel is byte-for-byte unchanged from the established baseline. The ROM
contains 25 public-source modules, 1,306,428 used bytes in a 2 MB container.
Messages retains its executable prefix and registers the extended real
ResourceFS data. Desktop occupies loaded module index 9 (after UtilityModule
and eight base providers), matching the kernel's existing Language 10 default.
All other module bytes match their independently assembled artifacts. No guest
success stubs, host module loading or guest-code injection are used in the cold
ROM test. The emulator has no changes in this milestone.

The initial later-machine TaskManager accounting displayed zero total memory.
Selecting its existing MEMC page-map path fixes the defect; the test inspects
the actual total-memory record and requires 4 MB. The welcome title is ArcLibre;
original source notices and the original Acorn copyright line remain intact.
See LICENSING.md for the selected fonts, sprites, templates, artwork and mixed
FPEmulator licences.

## Evidence and limits

`build/arclibre/acceptance.json` records three cold boots with identical
observations and rendered screen memory. Each `cold-N` directory contains the
configuration, task/SWI observations, screenshots, instruction traces, CMOS and
a machine snapshot. All observed undefined exceptions must match an explicitly
classified Wimp or FPEmulator software-FPA instruction. Abort and address exception counts must be zero. Floppy reads must produce
real WD1772 read-sector accesses and FIQ transfers; the earlier idle-desktop
assertion of zero FIQs no longer applies. The test image is write-protected,
and the controller log must contain no write-sector or write-track commands. Sampled ROM instructions are matched to the
independently decoded source artifacts; this is not exhaustive path coverage.

The retained lower-level suites remain separate: reset/MEMC/CAM, exception
vectors, keyboard, filing/media-change/controlled writes, rendering, fonts,
software FPA, the single Wimp task and real two-task slot/context switching.
The source patches must reverse to pinned originals and reapply with zero fuzz.

## Remaining work and next milestone

The matching public ADFSFiler 0.83 and ShellCLI 0.28 are now in the ROM, with
pinned source and asset hashes and patch 0007. ADFSFiler creates the floppy icon
and uses the real ADFS/FileCore path. ShellCLI supplies F12 and exits on an empty
Return. Sharing remains unavailable without ShareFS; its original presence check
and menu shading are retained. The small authored ShareD header defines only
published SWI numbers, not a runtime replacement.

The cold-boot gate exercises these through real mouse/key events:

- Open the floppy icon and verify the five root entries drawn by Filer.
- Double-click Docs and Deep; verify the nested window titles and file names.
- Press F12; observe the fifth (temporary) ShellCLI task in USR26.
- Catalogue the disc and display RootText, checking actual text output.
- Submit an unknown command and verify the real translated error.
- Read the nested Leaf file after that error, then run and exit the original
  test fixture Hello from disc through ShellCLI's real application handler.
- Press empty Return; verify four desktop tasks, click the floppy again and verify
  resumed polling by all four (ADFSFiler suppresses idle null events).

Screenshots, Wimp/ShellCLI observations, sampled instruction paths, generated
sprite instructions and WD1772 access logs accompany each cold run. The fixtures
are project-authored test data, not extracted ROM resources or a test of an
unmodified historical application. The input is the D-format DA.adf generated
by tests/build_fixtures.py (SHA-256
6f770c2b9a63d77a02057e8263c128d30464ef3287bba1bbaf040fea98c73d52).

This is still an experimental distribution. Filer launching, DragASprite,
original-machine sound and bounded Zarch play now have separate passing gates.
[FilerAct and the original C runtime](../desktop-c/RESULTS.md) add real
copy/move/delete and write-protected-disc recovery. TaskWindow, formatting,
backup, recursive/cross-volume operations, printing and ARM3 execution remain
unverified. Edit, Draw, Paint and configuration applications are not bundled.

Next: broaden desktop filing/error cases, restore TaskWindow and select the
matching desktop applications/settings with reviewed dependencies. Retain the
filing-write backlog (interruption, dirty-media changes and delayed errors).
Continue unmodified 3.11-era application/game checks; the public 3.60
implementation is not a changed compatibility target.


## Pointer correction

The first desktop ROM (`c4c5883c…`) accepted real mouse input but showed no cursor.
The earlier acceptance tests checked clicks and screen RAM, which excludes the
VIDC hardware cursor overlay. They did not establish pointer visibility.

The corrected ROM includes the matching original SpriteExtend. Without it,
SpriteOp 36 returns through the kernel's original DoesNowt entry; Wimp's pointer
request never defines a shape. With it, shape 1 contains 11 rows and the cursor
DMA points at &7B800, matching the physical mapping of &1F03800. The test verifies
69 nontransparent cursor pixels against the actual VIDC-composited frame before
and after movement, rather than only checking mouse coordinates.

`PointerProbe` reproduces the failure with SpriteExtend omitted from an otherwise
matching ROM. All three corrected cold boots require a visible moving pointer. An additional
isolated module-loading run reproduces the original “Disc drive not known”
startup dialogue and verifies a visible moving pointer there too; its evidence
is separate from the natural ROM boot gate.
The original C area validator supplies an independent oracle for 29 bounded
valid/corrupt cases against the ARM2 translation. The retained assembly renderer
is enabled; JPEG and the C-generated renderer are outside this build profile.
The supported scope is documented in patch 0005. Broader sprite operations still
need their own compatibility tests. The earlier startup-only run executed no generated renderer code. The filing
gate now also records and independently decodes emitted ARM2 instructions in
the SpriteExtend code buffer. This covers the observed paths, not all possible
generated sprite renderer variants.

To reproduce the additional startup-dialogue check after the main gate:

```sh
build/harness-patched/release/DesktopProbe build/desktop-baseline/artifacts/floppy.rom build/arclibre/checker-natural/supervisor-entry.macarch-state build/desktop-startup build/arclibre/boot-warning-check
build/harness-patched/release/PointerProbe inspect build/desktop-baseline/artifacts/floppy.rom build/arclibre/boot-warning-check/boot-warning.macarch-state build/arclibre/boot-warning-check/pointer
```

The splash now reads “ArcLibre”, “© Acorn Computers Ltd, 1995” and
“Derived from the RISC OS open-source release” on separate lines. The original
copyright is retained. Patch 0008 measures and centres the added provenance
line and includes its width in the welcome-panel bounds. Each cold-boot evidence directory
also includes `welcome.png`, captured after the genuine welcome routine returns.
See BUILD.md for automatic copying to a local MacArch ROM and the new GUI
configuration import/export commands; older MacArch builds cannot import JSON.

## Desktop application launch

The next gate adds Obey 0.33 and BufferManager from the pinned cleaned-3.60
cohort. Filer sees an original `!ArcTest` application directory, executes its
`!Boot`, and a real mouse double-click runs `!Run`, a nested Obey file and an
on-disc ARM2 executable. The program prints its marker and exits; Space dismisses
the genuine command window and the four desktop tasks remain responsive.
No application code or success result is injected into guest memory.

BufferManager supplies the kernel's configured `MouseBufferManager` contract:
UtilityModule registers the nine-byte mouse event buffer through
`Service_BufferStarting` and `Buffer_Register`. Without the runtime, a quick
second click can arrive during an application-icon redraw and be lost. The
restored module claims InsV/RemV/CnpV and queues the events. Its legacy module
header double-counted the SWI base with the exported modern allocation aliases;
patch 0010 uses the canonical `BufferManagerSWI_Base` (&42940). The build checks
this emitted header explicitly. Other changes are relocatable AREA, the existing
KernelEntry macro spelling and explicit ARM2 processor-state settling NOPs.
The pinned kernel remains byte-identical.

`tests/run_desktop_rom.py` includes three cold application-launch runs alongside
all earlier desktop gates. `launch-N` contains screenshots, traces, actual mouse
events, CLI/variable operations and independent instruction verification. The
application image is generated by `tests/build_desktop_app.py`; the existing
filing fixture remains byte-identical. Obey is required in launch traces;
ShellCLI is required separately in the F12 trace gate.

The user's own Zarch E-format floppy is a separate, unmodified private
test asset. Its loader executes after a desktop double-click, but requests
SoundDMA, SoundChannels, SoundScheduler, WaveSynth and Percussion. Missing these
causes its fallback reconfiguration/reset path. This observation is not a
successful game run. Private image bytes, disassembly and snapshots remain in
ignored build output and are excluded from release archives.

The [sound and Zarch gate](../sound/RESULTS.md) now supplies those real sound runtimes and verifies bounded game launch, input and sound across three cold boots.
