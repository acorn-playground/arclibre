# Reproducing the experiment

The supplied source snapshots and scripts reproduce a **failed kernel assembly**, not a bootable image. The final measured status is recorded in assembly-result.json. No external RISC OS installation, DDE, aasm binary, ROM, image stamp tool or linker was used.

## Recorded host

macOS 27.0.1, build 26A434, Apple Silicon; Apple Clang 21.0.0 (`clang-2100.3.34.2`), Python 3.14.0. Exact native tool versions, Git revision, download hashes and executable hashes are in toolchain.json. This is a native cross-assembly setup, not a RISC OS guest build.

## Repeat from this workspace

From the project root:

```sh
sh experiments/arm2-kernel/scripts/run-experiment.sh
```

The script validates the original snapshot hashes, exports the headers, applies the recorded adaptations, builds/runs the tokeniser, runs the assembler smoke tests, and attempts the real kernel. **Exit 1 is the documented unresolved result.** Each invocation stores a timestamped log and updates the final status JSON. It removes any partial target object on failure. Do not treat a zero status from the negative *tool* fixture as success: AsAsm only warns about its deliberately unsuitable instructions.

`prepare.py` normally consumes the supplied snapshots offline. Its optional `--recover` mode and `recover.py` document how the original audit caches were read with `git show`; those recovery modes require the local Phase-0 Git caches and are not needed to rebuild from the delivered snapshots. Original `o/`, `rm/` and other prebuilt target binaries were excluded from the recovered inputs.

## Host bootstrap

The already-built tools are local in `toolchain/`. To reconstruct them, fetch the three GNU release archives listed with SHA-256 and official URLs in `manifests/toolchain.json`. Verify those hashes, unpack under `toolchain/`, and build M4, then Autoconf, then Automake, each using:

```sh
./configure --prefix="$experiment_root/toolchain/host"
make -j4
make install
```

Here `experiment_root` must be the absolute experiment directory. Before building Autoconf and Automake, put that prefix's `bin` first in `PATH`; use the local M4. The exact successful build logs are `logs/m4-build.log`, `logs/autoconf-build.log` and `logs/automake-build.log`. Existing GNU Libtool (`glibtoolize`), its macros under `/opt/homebrew/share/aclocal`, Apple Clang and the macOS SDK are host prerequisites. No package manager installation is performed by these scripts.

The GCCSDK source was obtained from its project's public Git conversion:

```sh
git clone --filter=blob:none --sparse https://github.com/riscos-dot-info/gccsdk.git "$experiment_root/toolchain/gccsdk"
git -C "$experiment_root/toolchain/gccsdk" checkout 212d4567f007e7d30f4af3d6e1919a3d8a115b1c
git -C "$experiment_root/toolchain/gccsdk" sparse-checkout set tools/asasm tools/decaof tools/elftoolchain
```

The initial observed checkout used `--depth 1` while that pin was the branch head; a fresh reconstruction should fetch the explicit commit as above rather than assume a current head still matches. `tools/asasm/elftoolchain` is a repository symlink to `tools/elftoolchain/current-trunk`, which must be present.

Then run the tested host build recipe:

```sh
sh "$experiment_root/scripts/bootstrap-tools.sh"
clang -I"$experiment_root/toolchain/compat" "$experiment_root/scripts/check-host-layout.c" -o "$experiment_root/toolchain/host/bin/check-host-layout"
"$experiment_root/toolchain/host/bin/check-host-layout"
sh "$experiment_root/scripts/run-experiment.sh"
```

The host bootstrap includes the Darwin adapters, real Git version identity and static ELF libraries. It does not install the assembler globally. `logs/asasm-autoreconf.log`, `asasm-configure.log`, `asasm-build.log` and earlier named failure logs record the work.

## Evidence limits

The final include report is extracted from the verbose assembler trace and records the actual contents used, including the generated wrapper and help text. It is not a source scan that assumes all possible GET branches are selected. The trace traverses all first-pass sources before second-pass resolution fails.

`scripts/diagnostic-asasm.py` can rebuild with a larger error budget for debugging, but it changes the local tool binary and was **not** used for the final normal result. Do not run it when simply reproducing that result. The attempted `--pass-one` command also demonstrates a tool assertion after traversal; it is not a successful standalone build target.

No successful object exists to extract, disassemble or link. The source addresses in `configuration.json` and the assembler's tentative first-pass sizes must not be presented as a verified byte-range map, complete footprint or executable safety certificate.
