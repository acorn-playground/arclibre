# Reproduce the first ROM boot

## Package the exact kernel

From the project root:

```sh
python3 experiments/arm2-first-boot/scripts/build_rom.py
```

The script verifies the restored kernel's SHA-256, checks the existing Utility-module chain reaches EndOfKernel's zero terminator, preserves all kernel bytes and pads to the configured 2 MiB. It also produces debugger labels and contract symbols. No assembler/linker step modifies the kernel in this phase.

Expected ROM hash: `651ad2015c8c3f427ab070c124c6282c2e1d717d421f518545a04710d152c2bb`. Expected kernel hash: `6fb97a29134f6cea155d4b1ec0e9ca80f3c9f8e61672dd238eea32585a6851f1`.

The preceding restoration's exact AsAsm rebuild instructions and all tests remain in `../arm2-restoration/BUILD.md`. baseline-preservation.json verifies every file listed by that phase's original SHA256SUMS, including its sources, patches and tests. This phase reuses its proven artifact; it does not silently rebuild from another revision.

## MCP execution

Use absolute paths for `rom` and `path`. These are sequential MacArch MCP tool calls, not guest commands:

```json
{"tool":"power_cycle","args":{"rom":"<experiment>/artifacts/kernel-only.rom","model":"A440/1","cpu":"ARM2","ram_kb":4096,"hard_discs":[],"monitor":"standard","cmos_reset":true,"max_seconds":0}}
{"tool":"set_real_time","args":{"on":false}}
{"tool":"load_symbols","args":{"path":"<experiment>/artifacts/kernel.labels","clear":true}}
{"tool":"trace","args":{"enable":10000}}
{"tool":"set_breakpoint","args":{"address":"&4"}}
{"tool":"set_breakpoint","args":{"address":"&C","end":"&14"}}
{"tool":"set_breakpoint","args":{"address":"ModuleInit"}}
{"tool":"step","args":{"kind":"instruction","count":1}}
{"tool":"step","args":{"kind":"to","address":"&0380DD3C","max_seconds":1}}
{"tool":"step","args":{"kind":"to","address":"SetUpKbd","max_seconds":1}}
{"tool":"step","args":{"kind":"to","address":"ResetPart1Done","max_seconds":10}}
{"tool":"step","args":{"kind":"to","address":"VduInit","max_seconds":1}}
{"tool":"continue","args":{"max_seconds":2}}
{"tool":"registers","args":{}}
{"tool":"memory_regions","args":{}}
{"tool":"save_state","args":{"path":"<experiment>/artifacts/reproduced-pre-module.macarch-state"}}
```

Inspect each stop rather than blindly continuing through an exception. An execute breakpoint at `&8` stops ordinary SWIs and is not a fault detector. `max_seconds:0` loads/resets without executing guest instructions; `step` and `continue` explicitly resume the debugger. The headless server does not run between calls. Existing debugger breakpoints survive power cycles, so remove only your previous experiment breakpoints if rerunning in a reused session.

Optional diagnostic breakpoint at `NoHighSWIHandler` will stop on the missing ColourTrans notification. The captured run stepped out through the real error handler and continued successfully. No `set_register`, `poke`, alternate SWI handler or guest instruction replacement is needed.

All actual MCP calls and text responses are preserved in numbered traces. The final MCP session was left stopped at ModuleInit after the reset-button repeat.

## Complete hardware capture and three cold starts

The external harness uses the same public `Machine`, `Debugger`, `snapshot`, `stateSections` and memory-inspection APIs used by MacArch's diagnostics. It does not modify the emulator. Point `MACARCH_CORE` at the public core source within the exact emulator checkout:

```sh
export MACARCH_CORE=/absolute/path/to/macarc/Packages/ArchimedesCore
sh experiments/arm2-first-boot/scripts/run_boot.sh
```

The script checks Git revision `550bee4842e45eafdf331f0d06e11df1368403e8`, builds the host harness, performs three independent fresh-machine boots and validates captured state. It uses a fixed RTC epoch of 770428800 (the core default), Delete at power-on, standard monitor and no media. It never changes CPU registers or guest RAM to force progress.

The measured host is Apple Silicon macOS 27.0.1 with Apple Swift 6.4.0. SwiftPM uses local source only, with no remote package dependency. Build products remain in this experiment's `build/native`; compiler caches are placed under `/tmp`. The tested command uses `--build-system native` because the default Xcode build backend's dSYM stage failed in this sandbox. Native SwiftPM currently emits a deprecation notice; it successfully built this pinned project. The successful build log is harness-native-build.log.

The harness emits `artifacts/repeats/cold-1`, `cold-2` and `cold-3`. Run verification separately without executing the guest:

```sh
python3 experiments/arm2-first-boot/scripts/verify_boot.py
python3 experiments/arm2-first-boot/scripts/decode_hardware_log.py
python3 experiments/arm2-first-boot/scripts/check_parity.py
```

`check_parity.py` compares a new harness run with the supplied original MCP snapshot, which contains this project's ROM-derived state only. To compare a newly captured MCP run, replace the input snapshot path explicitly; do not rename a different image's capture into the evidence set.

## Extracted evidence bundle

The boot evidence archive includes this experiment and the original restoration archive. Extract both into the same parent directory so `arm2-first-boot` and `arm2-restoration` are siblings. The default MacArch source path in the manifest reflects the recorded workspace; use `MACARCH_CORE` on another machine. Native harness/tool binaries are not included. ROM construction and the existing static reports can be inspected without building MacArch.

To regenerate the evidence bundle after successful checks:

```sh
python3 experiments/arm2-first-boot/scripts/finalize.py
python3 experiments/arm2-first-boot/scripts/package_evidence.py
```

The packager writes `SHA256SUMS`, excludes host build products, includes the unchanged original restoration archive, and checks every archive member byte-for-byte. It creates `experiments/arm2-first-boot-evidence.tar.gz` and its `.sha256` sidecar.
