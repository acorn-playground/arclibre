# Build and reproduce the keyboard milestone

Keep this directory beside the existing `arm2-cam-transition`, `arm2-text-rendering`, `arm2-first-boot`, `arm2-restoration` and `arm2-kernel` directories. They are immutable inputs. The build copies the preceding restored work/source trees, regenerates and hash-checks the original exported headers, then applies the two source transformations recorded as patches 14 and 15.

From the project root:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-keyboard/scripts/run.sh
```

The native harness requires the unchanged MacArch core at commit `550bee4842e45eafdf331f0d06e11df1368403e8`, the same macOS/Swift toolchain as the preceding milestone, Python 3 and the working normal/observer AsAsm tools. `ASASM` and `ASASM_OBSERVER` can override their absolute paths. Defaults are `experiments/arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm` and `experiments/arm2-restoration/toolchain/asasm/src/asasm`. Follow the restoration's `BUILD.md` to reconstruct these tools. No proprietary ROM or assembler input is used.

The wrapper performs three assemblies, static/routine checks, three fresh cold boots, three natural continuations and CAM fixture suites, three keyboard suites, retained font/pixel comparisons, independent evidence checks, full boot hardware-write decoding and final source/core checks. Native build products stay under this experiment's `build/`, with caches under `/tmp`. The keyboard suite only drives the real host keyboard API; it does not inject commands via guest RAM or alter guest registers.

Expected hashes:

```text
kernel.bin      cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
kernel-only.rom c8128177ca866eda984c920eb543f6f1320f9e9a23d149187de164ee5c3a1745
```

To validate saved evidence without rerunning the emulator:

```sh
python3 experiments/arm2-keyboard/scripts/verify_regressions.py
python3 experiments/arm2-keyboard/scripts/verify_keyboard.py
python3 experiments/arm2-keyboard/scripts/finalize.py
```

For manual patch review, copy `arm2-cam-transition/work/`, then apply the files listed in `patches/series`, in order, using `patch -p1 -F 0`. They are incremental patches after the original thirteen; the builder performs equivalent transformations and the finalizer checks exact patch replay.

Load `artifacts/kernel-only.rom` in MacArch as A440/1, ARM2, 4 MiB, standard monitor, no media, with default CMOS/Delete held at cold power-on. Type at Supervisor. Full Help output currently requires missing MessageTrans, as documented in `RESULTS.md`.

`python3 experiments/arm2-keyboard/scripts/package_evidence.py` creates and verifies the source/ROM/evidence archive and SHA-256 sidecar. It includes the preceding evidence archive, whose earlier dependencies are nested; extract them into a common parent when reconstructing the sibling directories. Native build products and assembler binaries are excluded.
