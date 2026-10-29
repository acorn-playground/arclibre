# Reproduce the CAM transition repair

Keep this directory beside the existing `arm2-text-rendering`, `arm2-first-boot` and `arm2-restoration` directories. All earlier milestones are read-only inputs. The builder copies the exact font-repaired cohort, exports matching headers and applies only patch 13.

From the project root:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-cam-transition/scripts/run.sh
```

This recipe performs the repeated normal/observer assemblies, existing static/routine checks, three cold boots, the old-ROM negative control, three natural startup continuations, three real SWI page-transfer suites, framebuffer/font checks and complete pre-module hardware decoding. Each operation in the recipe was executed successfully; the wrapper supplies their sequential reproduction.

The default normal AsAsm and observer are the working tools from the prior milestones:

```text
../arm2-kernel/toolchain/gccsdk/tools/asasm/src/asasm
../arm2-restoration/toolchain/asasm/src/asasm
```

Set `ASASM` and `ASASM_OBSERVER` to absolute paths to override them. To reconstruct tools on a fresh host, follow the companion restoration's `BUILD.md`, including its isolated observer build. Generated help is copied byte-for-byte from the frozen cohort; exported headers are regenerated and checked against the original export hashes. No proprietary assembler or ROM input is required.

The native Swift harness uses the unchanged local core at commit `550bee4842e45eafdf331f0d06e11df1368403e8`. It checks tracked core changes, uses the previously tested native SwiftPM build backend and places compiler caches under `/tmp`. App UI changes elsewhere in the checkout are not part of this dependency.

To rebuild and check the candidate against the supplied execution evidence without rerunning the guest:

```sh
python3 experiments/arm2-cam-transition/scripts/build.py
python3 experiments/arm2-cam-transition/scripts/verify.py
python3 experiments/arm2-cam-transition/scripts/finalize.py
```

The latter two commands inspect saved captures; they do not claim a fresh emulator run. Expected output hashes:

```text
kernel.bin      ed7bf3d62598017e30d826bf41d08b2efaeae9bcbb2a9f1713343ebdafcd9245
kernel-only.rom 3d8bce380345b4a0dc5117e09c8f5de2d3dfd62f7cbe7c5e75cf1b578622f250
```

To review/apply the source change separately, copy the previous font-repaired `work/` tree and run `patch -p1 -F 0 -i /absolute/path/to/0013-legacy-cda-control-flow.patch`. The original twelve patches remain prerequisites. No source revision or workspace/header cohort changes here.

Load kernel-only.rom in MacArch as A440/1, ARM2, 4 MiB, standard monitor, no media, with default CMOS/Delete at cold power-on. The tested result is the clean Supervisor prompt shown in frame.png. File services and desktop functionality are not provided.

To regenerate the evidence bundle:

```sh
python3 experiments/arm2-cam-transition/scripts/package_evidence.py
```

It writes `experiments/arm2-cam-transition-evidence.tar.gz` and a SHA-256 sidecar. The bundle includes this experiment and the unchanged preceding evidence archive, with earlier archives nested inside it. Extract those archives into a common parent to obtain the sibling input directories. All archive members are verified byte-for-byte; native build products are excluded.
