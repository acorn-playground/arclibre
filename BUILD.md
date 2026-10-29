# Building and testing ArcLibre

## Prerequisites

**macOS:** Apple Clang and the SDK (Xcode's command-line tools, which also
supply Bison and flex), Swift 6.2 or later with the macOS 26 SDK, Python 3.12
or later, Make, `patch`, and GNU Libtool providing `glibtoolize` and its
aclocal macros (Homebrew's `libtool`), with pkg-config's aclocal macros in the
same prefix. Tested with Swift 6.4, Apple Clang 21 and GNU Libtool 2.5.4.

**Linux:** Swift 6.2 or later (its toolchain supplies the `clang` the build
uses), Python 3.12 or later, Make, `patch`, GNU Libtool (`libtoolize`), Bison,
flex, GNU M4, pkg-config's aclocal macros and the zlib headers. On Ubuntu:

```sh
sudo apt install make patch libtool bison flex m4 pkgconf zlib1g-dev
```

Tested on Ubuntu 26.04 (x86-64) with Swift 6.4.1, Clang 21, glibc 2.43, GNU
Libtool 2.5.4, Bison 3.8.2 and flex 2.6.4. Windows has not been tried.

Everything else is built from pinned source archives in
`third_party/archives/`, whose SHA-256s are checked before extraction: GNU M4,
Autoconf and Automake; GCCSDK's AsAsm, decaof and ELF tools; GCCSDK's GCC
3.4.6 for the C modules; and the MacArch emulator core the tests run on. The
build downloads nothing and installs nothing outside `build/`.

## Building the ROM

```sh
make arclibre-rom
```

builds the host tools (once, about 6 minutes), every component, and the 2 MB
ROM in `build/arclibre/arclibre.rom`, with its module layout in
`build/arclibre/rom-layout.json`. Other products:

| Command | Output |
|---|---|
| `make arclibre-rom-4m` | the 4 MB ROM, `build/arclibre-4m/arclibre.rom` |
| `make extras-disc` | the 2 MB ROM's floppy, `build/extras-disc/arclibre-extras.adf`, joined from the three below |
| `make dosfs-disc` | DOSFS as a disc-loaded module, `build/dosfs/arclibre-dosfs.adf` |
| `make alarm-disc` | !Alarm, `build/alarm-disc/arclibre-alarm.adf` |
| `make printing-disc` | !Printers and its modules, `build/printing-disc/arclibre-printing.adf` |

Every assembly and link is done twice and compared; each component is
statically verified (ARM2-only instructions, 26-bit modes, no unresolved
symbols, workspace and interface contracts) before the ROM is joined.

## Releasing

Every release ships two variants, named with the version in
`manifests/release.json`, which also sets the version and date the ROM
reports in `*FX 0` and `*Help`:

| File | For |
|---|---|
| `arclibre-VERSION-2mb.rom` | any Archimedes |
| `arclibre-VERSION-2mb-extras.adf` | the 2 MB ROM: DOSFS, !Alarm and !Printers on one 800K floppy |
| `arclibre-VERSION-4mb.rom` | the A5000, A3010, A3020 and A4000: everything in ROM |

with the source archive, the record of rebuilding it, the evidence archive,
MacArch machine files (`machines/`), a README.txt and `SHA256SUMS`.

```sh
# 1. Set "version" and "date" in manifests/release.json.
ARCLIBRE_INSTALL_ROM=0 make release-test
# 2. Record it: the summary and release record, with every report's hash.
python3 tools/record_desktop_release.py --milestone 'What changed' --date YYYY-MM-DD
# 3. Commit (packaging compares the archives with HEAD), then:
make release
```

`make release-test` builds the 2 MB ROM and the extras disc, runs the release
suite on them (`tests/run_release.py`: 32 steps in three parallel lanes,
about 40 minutes), then builds the 4 MB ROM and runs its gate. The 4 MB build
relinks the shared C modules at its own addresses, so it comes after every
2 MB gate.

`make release` refuses unless all of that passed for the recorded hashes and
the tree is committed. It exports the source archive, rebuilds it from
scratch in a new directory into both ROMs and the disc and compares them byte
for byte, audits the archives against the commit
(`tests/check_release_archives.py`), and writes `dist/arclibre-VERSION/`.

The full gate reports go into the evidence archive (`evidence/reports/`);
the repository keeps the summary,
`docs/archimedes-desktop/reports/integration.json`, and the release record,
`manifests/arclibre-desktop-release.json`, both with each report's SHA-256.

## Test tiers

| Command | Use | Runs |
|---|---|---|
| `make check` | every change | the ROM build and static checks, the desktop smoke gate, and the gates for the paths that changed, each with one cold boot |
| `make check-full` | risky changes between releases | every gate, with three cold boots and negative controls |
| `make release-test` | a release | the release suite, then the 4 MB ROM's build and gate |

`tests/run_checks.py` maps changed paths (uncommitted and untracked, or since
`--since REF`) to gates; changes to shared foundations (the kernel, Wimp,
filing stack, headers, ROM builder, toolchain or harness) select every gate.
`--gate NAME` adds one. Any gate also runs alone, and takes `--probe` for one
cold boot without its negative control. Probe runs write `probe.json`, never
`acceptance.json`, so only the full suite produces records a release accepts.
Don't run `check-full` after the release suite: its ROM build rebuilds the
shared stacks and clears records packaging needs.

## The gates

Each gate boots ROMs in the MacArch core (`tests/harness`, a Swift package of
probes), types and clicks at the real desktop or command line, and checks the
result on the host. The emulator core is the pinned public one, with one
recorded patch (`third_party/patches/macarch-original-disc-change.patch`) and,
off macOS, a host portability patch that changes no emulation.

| Gate | Covers | Results |
|---|---|---|
| `tests/run.py` | the frozen kernel/filing baseline: boot, keyboard, messages, territories, floppy reads and writes | [maintained tree](docs/maintained-tree/RESULTS.md) |
| `make desktop-test multitask-test` | renderers, fonts, FPEmulator and Wimp in isolation; real multitasking | [renderers](docs/renderers/RESULTS.md), [fonts](docs/font-stack/RESULTS.md), [FPE](docs/fpemulator/RESULTS.md), [Wimp](docs/wimp-stack/RESULTS.md), [multitask](docs/multitask/RESULTS.md) |
| `run_desktop_rom.py` | the desktop, pointer, Filer, F12 command line | [desktop startup](docs/desktop-startup/RESULTS.md) |
| `run_palette.py`, `run_menus.py`, `run_sprite_commands.py` | appearance and !Palette, menus, sprite commands | [desktop](docs/archimedes-desktop/RESULTS.md), [menus](docs/menu-messages/RESULTS.md), [SpriteUtils](docs/spriteutils/RESULTS.md) |
| `run_sound.py` | the sound stack and DMA timing | [sound](docs/sound/RESULTS.md) |
| `run_desktop_actions.py`, `run_filer_actions.py` | drags, Pinboard, file copy/move/delete, the C runtime | [actions](docs/desktop-actions/RESULTS.md), [C desktop](docs/desktop-c/RESULTS.md) |
| `run_desktop_apps.py`, `run_graphics_apps.py`, `run_app_workflows.py`, `check_apps_build.py` | Edit, Draw, Paint: editing, saving, reopening, interchange | [apps](docs/desktop-apps/RESULTS.md), [graphics](docs/graphics-apps/RESULTS.md), [editing](docs/graphics-apps/EDITING.md) |
| `run_task_services.py` | TaskWindow, FilterManager | [task services](docs/task-services/RESULTS.md) |
| `run_streams.py`, `check_stream_sleep_negative.py`, `run_ram_filing.py` | DeviceFS, PipeFS, RAMFS, Free | [streams](docs/streams/RESULTS.md), [RAM filing](docs/ram-filing/RESULTS.md) |
| `run_standard_utilities.py`, `run_squash.py`, `run_basic_utilities.py` | ScreenBlanker, StringLib, Squash, Chars, Help, Calc, Configure, Alarm | [utilities](docs/standard-utilities/RESULTS.md), [desktop utilities](docs/desktop-utilities/RESULTS.md) |
| `run_clock.py`, `run_debugger.py`, `run_arm3.py` | IIC, the clock, the Debugger, ARM3 cache control | [clock](docs/clock/RESULTS.md), [debugger](docs/debugger/RESULTS.md), [ARM3](docs/arm3/RESULTS.md) |
| `run_format.py`, `run_dosfs.py`, `run_dosfs_formats.py` | FileCore formatting, DOSFS on 720K, 1.44M, 360K and FAT16 | [FileCore](docs/filecore/RESULTS.md), [DOSFS](docs/dosfs/RESULTS.md) |
| `run_network.py`, `run_netfs.py` | Econet, NetFS against a host file server, NetFiler | [network](docs/network/RESULTS.md) |
| `run_hardware.py`, `run_new_io.py` | expansion cards, serial, parallel; the A5000 family's I/O | [hardware](docs/hardware/RESULTS.md), [new I/O](docs/new-io/RESULTS.md) |
| `run_printing.py`, `run_extras.py` | printing to dot-matrix, LaserJet and PostScript; the shipped extras disc | [printing](docs/printing/RESULTS.md) |
| `run_rom_4m.py` | the 4 MB ROM | [4 MB ROM](docs/rom-4m/RESULTS.md) |

## How the build works

1. **Host tools** (`make bootstrap`, `make c-bootstrap`): M4, Autoconf and
   Automake, then AsAsm (and an observation-only copy that records every
   emitted word and symbol lookup), Tokenise, and GCCSDK 3.4.6 with its
   recorded patches (`manifests/c-toolchain.json`).
2. **The frozen baseline** (`make baseline`): the first restored ARM2 ROM,
   kernel and filing modules, rebuilt exactly. It must reproduce

   ```text
   ROM    bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791
   Kernel cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
   ```

   which checks the toolchain and the maintained tree; `tests/run.py` is its
   regression suite.
3. **Component stacks**: each group of modules (desktop, fonts, Wimp, sound,
   the C runtime and applications, networking, printing, ...) is built from
   `src/` into its own `build/` directory and verified.
4. **The ROM** (`tools/build_arclibre_rom.py`): the delivered kernel, built
   with `ArcLibreDelivered` (the fixes that make it behave as 3.11) and the
   version from `manifests/release.json`, joined with the modules in 3.11's
   order, the C modules linked at their ROM addresses, and ResourceFS.

`src/` holds the sources with every patch already applied; the build copies
them into `build/` and never writes into `src/`. `patches/` records each
change against upstream, and the manifests record upstream and maintained
hashes for every file; `tools/verify_candidate_patches.py` checks them on
every build. `ARCLIBRE_OUTPUT` selects another output directory for the
baseline build.

## Host portability

The macOS hosts once supplied three things implicitly; they are now explicit:

- **Case-insensitive names.** RISC OS names are case-insensitive and the
  sources rely on it (`GET s.vdu.VduGrafA` for `s/vdu/vdugrafa`).
  `third_party/patches/asasm-portable-host.patch` and
  `gccsdk-3.4.6-case-insensitive.patch` fall back to a unique
  case-insensitive match when an exact name is missing.
- **No-break spaces.** macOS's UTF-8 locales count 0xA0 as blank and glibc's
  don't; the AsAsm patch counts it as blank on every host.
- **Link order.** Object lists are fixed in the build scripts rather than read
  from a directory, whose order differs between filesystems.

## MacArch

A git-ignored `arclibre.local.json` makes every successful `make arclibre-rom`
install the 2 MB ROM into MacArch:

```json
{
  "macarch_rom": "/absolute/path/to/MacArch/ROMs/ArcLibre.rom",
  "installed_sha256": "SHA-256 of the file there now, if any"
}
```

`tools/install_macarch_rom.py` replaces that file atomically and refuses if
it was changed by something else. `ARCLIBRE_INSTALL_ROM=0` skips it. MacArch
keeps a loaded ROM in memory across Power Cycle: close and reopen the machine
to load a new one.

A release's `machines/` folder has MacArch machine files for the tested
configuration: an A440/1 with an ARM2, 4 MB of RAM and the standard monitor,
its CMOS, and demonstration hard discs. Import one with **Machine → Import
Machine Configuration…**.
