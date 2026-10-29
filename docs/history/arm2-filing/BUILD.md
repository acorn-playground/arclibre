# Reproduce read-only filing robustness

This experiment retains the exact ROM from `../arm2-floppy`. Its complete rebuild recipe, source pins, patch series and licenses remain in that directory and its evidence archive. No ROM source or binary changed here. The diagnostic client and test discs are original generated content.

Requirements: macOS with Swift 6.2 or later (recorded compiler Swift 6.4), Python 3 with tarfile extraction filters, `patch`, and the previously built normal AsAsm at `../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm`. Keep the prior experiment directories alongside this one. Unpack the nested evidence archives into the same `experiments` parent to reconstruct those prerequisites. No commercial ROM/disc or network download is used.

Full recipe:

```sh
sh experiments/arm2-filing/scripts/run.sh
```

The recipe:

1. Assembles `sources/CheckFile.s` twice with normal AsAsm, ARM2/APCS 26-bit flags; compares hashes and independently decodes the executable instructions.
2. Generates four 800 KiB D/E discs, nested directories, fragmented data and ten fault variants. Every file is generated locally; there is no ROM extraction.
3. Extracts the bundled public MacArch core at `550bee4842e45eafdf331f0d06e11df1368403e8` into `build/baseline/ArchimedesCore` and `build/replayed/ArchimedesCore`. Applies `patches/macarch-original-disc-change.patch` with zero fuzz and checks before/after hashes. The external MacArch checkout remains untouched.
4. Builds baseline and patched harnesses separately, runs four synthetic device tests, and performs three patched cold boots from reset through the pre-module boundary.
5. Continues genuine startup, runs retained CAM/keyboard/message/territory/IntKey/floppy/display regressions and fourteen filing scenarios from each cold-derived Supervisor state.
6. Reproduces stale media on the baseline core, demonstrates explicit dismount recovery, and independently checks saved evidence.

Development executed these stages individually. The compiled isolated `build/patched/ArchimedesCore` source tree was compared in full with the clean replay; `artifacts/emulator-provenance.json` records that comparison. The full recipe uses the equivalent replayed tree.

For saved evidence only:

```sh
for name in regressions keyboard messages territory selection floppy filing; do
  python3 "experiments/arm2-filing/scripts/verify_$name.py"
done
```

A single scenario can be rerun without rebooting; this is a saved-state test, not another cold boot:

```sh
experiments/arm2-filing/build/native-patched/release/FilingProbe \
  experiments/arm2-filing/artifacts/floppy.rom \
  experiments/arm2-filing/artifacts/natural-1/supervisor-entry.macarch-state \
  experiments/arm2-filing/artifacts/discs \
  /tmp/arm2-filing-check media-change
```

Other selectors are `DA`, `EA`, `empty-drive`, `media-change-baseline`, and each fault filename without its extension. `all` excludes the intentional baseline-defect scenario. All mounts explicitly use write protection and assert empty write overlays.

The snapshot extension is an optional JSON field, `floppyDiscChanged`, containing four per-drive latches. Binary device sections and version 2 remain unchanged. The patched reader accepts old snapshots with false latches; it still asserts the selected empty-drive signal. Old readers ignore the extension and cannot preserve its new latch semantics. Tests cover old and new snapshots. Later IO models and A3000 wiring are deliberately unaffected by this patch.

Manual use of the unchanged ROM still starts with `dir adfs::0.$`, then `cat`. The generated `DA.adf` and `EA.adf` add `Docs`, `RootText`, `Zero`, `Hello` and `CheckFile`. The patch was subsequently applied to the MacArch checkout at the user’s request (HEAD `6409c6c0b74174d19be6755197c28f2c1f8f2755`). The installed application and MCP server binaries were not rebuilt: rebuild/restart them to use the new rapid-swap behavior. The native harness uses existing public APIs and needs no MCP extension.

To package the verified evidence:

```sh
python3 experiments/arm2-filing/scripts/package_evidence.py
```
