# ArcLibre: cooperating tasks and application slots

The gate passes on three independently cold-booted A440/1 ARM2 machines. The
baseline ROM and emulator are unchanged. Run:

```sh
ARCLIBRE_OUTPUT="$PWD/build/desktop-baseline" make multitask-test
```

`tests/fixtures/multitask` contains new Apache-2.0 diagnostic programs, not guest
OS replacements. The master enters through OS_Module reason 2. It starts two real
Absolute files through Wimp_StartTask, FileSwitch and ResourceFS. Both execute at
logical address &8000; MEMC maps their code to different physical pages (&40000
and &60000) and their data markers to &48000 and &68000. Each child performs 20
Wimp polls, checks its private marker and all eight FPA registers plus FPSR, and
sends a completion message. The master receives both and all three tasks close.
The private diagnostic message action is not asserted to be a public allocation.

The three runs produce identical acceptance results in
`build/multitask/acceptance.json`. Per-run `result.json`, `tasks.json`, instruction
traces and snapshots preserve the observations. This proves the tested slot,
cooperative scheduling and floating-point context paths; it does not establish
arbitrary application compatibility or desktop readiness.

During harness development, jumping directly from Supervisor into user mode
left a live Supervisor stack frame and correctly prevented callbacks. Entering
the diagnostic as a real module application restores the genuine kernel entry
contract. No kernel callback bypass or manual processor-stack repair is used.

The ultimate compatibility target remains unmodified RISC OS 3.11 applications
and games. The recovered 3.60 source cohort is an implementation baseline, not a
substitute compatibility target.
