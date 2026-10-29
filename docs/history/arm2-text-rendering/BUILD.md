# Reproduce the font-alignment repair

Keep `arm2-restoration`, `arm2-first-boot` and this `arm2-text-rendering` directory as siblings. The earlier milestones are read-only inputs. Their source cohort, headers, generated help and tests are reused without revision changes.

The local tools are the same working AsAsm and observer used by the restoration. Defaults:

```text
../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm
../arm2-restoration/toolchain/asasm/src/asasm
```

Set `ASASM` and `ASASM_OBSERVER` to absolute tool paths to override them. For a new host, follow the companion restoration's `BUILD.md` to build those tools and the observer first. The evidence archives deliberately exclude native tool binaries. No tokeniser rerun is needed here: the exact generated help is copied from the frozen restoration baseline. Headers are exported afresh from the matching source files and checked against the original export hashes.

From the project root, assemble and run the full bounded reproduction:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-text-rendering/scripts/run.sh
```

The host recipe uses local SwiftPM dependencies, native build backend and temporary compiler caches, as in the first boot experiment. It checks the recorded MacArch commit and that the core has no tracked changes. App UI changes elsewhere in the checkout do not affect this harness.

The script creates an isolated candidate source tree, applies the alignment change, assembles twice and once with the observer, runs the unchanged static/routine checks, exercises the alignment assertion's negative control, boots three fresh ARM2 A440/1 machines, captures baseline/fixed text tests, verifies pixels and reruns the hardware decoder. Individual commands in this recipe were executed successfully; the wrapper provides their sequential reproduction.

Expected candidate hashes:

```text
kernel.bin      ef6ae405391eb569b5ee04d28338f2e424f465530063abb949d2b1232b0b581d
kernel-only.rom 7d7835feaf0b31f5ea6ebdaf8a2798079c270979ac931ede7420e273315e2859
```

To assemble and validate without repeating emulator execution:

```sh
python3 experiments/arm2-text-rendering/scripts/build.py
python3 experiments/arm2-text-rendering/scripts/verify.py
python3 experiments/arm2-text-rendering/scripts/finalize.py
```

The latter two commands read the supplied runtime captures; they do not claim a new boot occurred. The build uses the original `-cpu=ARM2 -apcs 3/26bit -ABSolute -aof` options with A440/2048K definitions. Detailed commands and tool hashes are in `artifacts/*assembly-result.json`.

To load in MacArch, select `artifacts/kernel-only.rom`, A440/1, ARM2, 4 MiB and standard monitor, and cold reset with default CMOS/Delete. Expect legible **CAM Map Corrupt** error text, not completed OS startup. The MCP execution records demonstrate this with existing diagnostics; no extension is required.

The additional source patch can also be applied to a fresh copy of the already-restored tree with `patch -p1 -F 0 -i /absolute/path/to/0012-align-system-font.patch`. It is patch 12 after the original eleven, not a replacement for their source cohort. The builder regenerates the same patch from the frozen input and checks it by replay.

The evidence bundle contains this experiment and the unchanged first-boot evidence archive, which itself contains the original restoration archive. Extract the nested archives into a common parent to obtain the three sibling directories. Compiler caches and host executables are excluded.

Regenerate the evidence archive after the checks pass:

```sh
python3 experiments/arm2-text-rendering/scripts/package_evidence.py
```

This produces `experiments/arm2-text-rendering-evidence.tar.gz` and its `.sha256` sidecar, with member-by-member byte verification and a per-file `SHA256SUMS` inside the experiment.
