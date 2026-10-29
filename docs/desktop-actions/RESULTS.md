# Desktop drag restoration

DragASprite 0.11 from the pinned cleaned3.60 cohort now builds and executes in the ARM2 desktop. Three cold boots show a real Filer drag, a moving drag image, a Pinboard shortcut, double-click execution of the original diagnostic application from that shortcut, and return to four responsive desktop tasks. Screenshots and observations match across resets. This does not establish FilerAct copy/move/delete support.

## Reproduction

```
make arclibre-rom
python3 tests/run_desktop_actions.py
```

The builder is `tools/build_desktop_actions.py`; the gate writes `build/desktop-actions/acceptance.json`. Each `cold-N` directory contains screenshots, framebuffer bytes, mouse/Pinboard observations, instruction traces and an independently verified trace report. The normal desktop and sound gates remain required.

## Source and changes

Original repository: https://gitlab.4corn.co.uk/RiscOS/Sources/Desktop/DragASprit.git, revision `31057aec4e4f93497ac66d5f8c83ede58d08322e`. File hashes are in `manifests/desktop-action-inputs.json`. The Apache-2.0 licence and per-file notices are retained. No proprietary ROM resources are used.

`patches/desktop-actions/0001-drag-arm2.patch` adds the explicit code area required by AsAsm, disambiguates the shared KernelEntry macro, retains the ARM2 processor-mode settling instruction, and uses the canonical DragASprite SWI base `&42400` instead of adding the user-SWI bit twice. Reverse/forward patch verification recovers the exact original/maintained file hashes without fuzz.

Three independent assemblies produce identical AOF bytes and a 4,352-byte component with no unresolved symbols. Every emitted integer instruction is decoded independently; branches, code/data mapping and mode changes are checked. Runtime traces match the assembled bytes; all undefined exceptions are accounted for by the existing software floating-point implementation. No abort/address exceptions occur. The emulator is unchanged.

A suspected backdrop rendering problem was ruled out: both the captured video pixels and guest framebuffer retain the expected grey background. No speculative emulator or kernel patch was made.

## Remaining desktop work

The separate [C desktop gate](../desktop-c/RESULTS.md) now supplies the real matching C/RISC_OSLib runtime and FilerSWIs, with copy/move/delete and protected-media recovery tests. Dragging to Pinboard alone is not file copying. Longer Zarch sessions, TaskWindow, settings and the broader 3.11 application matrix remain separate milestones.
