# TaskWindow and FilterManager restoration

The real cleaned-3.60 TaskWindow 0.53 and FilterManager 0.11 sources now build
as resolved ARM2/26-bit components. Six cold runtime tests pass on ROM
`bb9d384592b076b630c95ac174ca1985a97fe18dc70025985bae80f34a3063cf`.
They are included in the normal build and installed MacArch ROM. This image
also contains the subsequently verified [sound-period correction](../sound/RATE_FIX.md)
and [public menu-message correction](../menu-messages/RESULTS.md).
Retained full-release regressions are recorded in the integration report.

## Sources and adaptations

The exact public inputs are listed in
[task-services-inputs.json](../../manifests/task-services-inputs.json):
TaskWindow `9d0a32bfcc51b43840d28ef8a23713061834b6f2` and Filter
`0728a78f554bdc46cac5043ba8a21941e6da3775`. All selected sources, UK messages,
headers and Apache-2.0 notices are preserved under `src/TaskWindow` and
`src/Filter`. No proprietary ROM or new artwork is used. See
[LICENSING.md](../../LICENSING.md#taskwindow-and-filtermanager).

The reversible [patch series](../../patches/task-services/series) separates:

1. Explicit relocatable areas, AsAsm include/operator/macro spelling, alignment
   before the SendNewTaskMessage label, explicit ARM2 PSR settling slots, and
   R12-relative Filter workspace addresses. Filter's original old-style SWI
   calculation is replaced by the exported `FilterSWI_Base` constant; with the
   recovered headers the old expression incorrectly produced &82640 instead
   of &42640. No SWI is renumbered or implemented by a dummy handler.
2. A real TaskWindow exit-path defect: the original Code_ExitHandler falls
   through into the `Cli$Prompt`/`*` strings before Code_NewCommand. The first
   functional test appeared to pass because those bytes happened to fail their
   ARM condition checks, but the independent trace audit rejected execution
   through data. An explicit branch skips the strings. The static gate now
   rejects fall-through at every code/data boundary, permitting only actual
   transfers, non-returning OS_Exit, and OS_WriteS's checked inline-string
   continuation.

## Build and workspace contract

With the existing maintained desktop/toolchain prerequisites:

```sh
python3 tools/build_task_services.py
python3 tools/verify_candidate_patches.py
ARCLIBRE_INSTALL_ROM=0 python3 tools/build_arclibre_rom.py --with-task-services
```

Each component's two normal assemblies and observer assembly must agree.
The independent AOF reader rejects unresolved externals and relocations; the
instruction decoder rejects unsupported ARM2 forms, direct branches into data,
missing PSR settling slots, and now code fall-through into data. Filter is
2,224 bytes; TaskWindow is 9,576 bytes. Together with their actual messages,
the integrated image uses 1,907,080 bytes, leaving 190,072 bytes in 2 MiB.

`build/task-services/workspace-contract.json` checks SvcTable,
BranchToSWIExit, redirection bytes, DomainId, SVCSTK and SysHeapStart against
the actual restored kernel symbols. TaskWindow's &FF8 domain cell agrees with
the existing Wimp writes in Wimp02/Wimp07. TaskWindow's global SWI-table veneers
and per-task RMA workspace remain its original implementation. Its original
redirection detection retains OS_ChangeRedirection as the real modern-kernel
path, rather than requiring any old ROM address to contain substitute code.

No kernel or emulator code is changed by this port. TaskWindow uses real
callbacks, vectors, user/SVC state, Wimp slots and messages; FilterManager uses
the existing Wimp_RegisterFilter interface.

## Runtime acceptance

The disk-loaded public parent/filter/child fixtures exercise callback order,
masking, claimed events, deregistration (including removal from inside a filter),
TaskWindow identity, a busy child with no SWIs in its loop, concurrent parent
progress, register/USR26 preservation, input, suspend/resume, real errors and
kill/exit cleanup. The independent trace verifier also checks the parent AIF,
its resolved C-library veneers, the child code and the module instruction maps.

An additional UI gate starts the original Edit, launches BASIC through
TaskWindow, reads the actual Edit text buffer, and tests keyboard input, busy
execution, Escape, recovery and quit. All three protocol and three Edit/BASIC cold machines pass with identical
observations and independently verified traces. The child preserves all eight
software-FPA registers over pre-emption; its 16 FPA traps are classified. The
missing-modules control fails with the genuine `SWI &43380 not known` error.
See [acceptance evidence](reports/acceptance.json). A passing module inventory or a visible task
window alone is insufficient, and complete RISC OS 3.11 compatibility remains
the wider project target.

Run `python3 tests/run_task_services.py` after a normal build. The optional
`--verify-existing` repeats the evidence checks without rerunning the positive
machines; it still executes the missing-modules negative control. Filter cleanup
coverage is explicit deregistration and self-removal, not automatic removal of
filters left behind by a crashed owner. Complete command/redirection semantics
and arbitrary child programs remain broader compatibility work.

## Follow-up: character-stream error return

The stream gate exercises the original SleepNoMore path, beyond the original
task milestone. It found and corrects the lost-error vector return in
`0002-claim-sleepnomore-error.patch`; see [the stream results](../streams/RESULTS.md).
The original release hashes and evidence above remain historical.
