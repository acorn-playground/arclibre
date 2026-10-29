# Isolated ARM2 Window Manager task

**PASS:** the restored Wimp runs an original diagnostic task in USR26 on the original MEMC kernel. Three fresh cold boots produce identical task/event results and framebuffer hashes. Real keyboard and mouse input reaches the task; a window redraws, moves and closes; genuine task messages and FPA save/restore work. This is an isolated task milestone, not a joined desktop ROM.

## Execution and memory contract

The fixture dynamically loads the statically audited FPEmulator, ColourTrans, Draw, SuperSampler, Hourglass, FontManager, ROMFonts and WindowManager modules through `OS_Module`. Installed bytes are compared with their artifacts. Original public message, template, sprite and font resources are registered with ResourceFS. No dummy service, host floating-point implementation or success handler is substituted.

The client occupies application space beginning at `&8000`, with a user stack at `&1F000`. It establishes the actual current-application pointer through `OS_ChangeEnvironment 15`, then changes to USR26 with guest instructions. This is necessary: the starting Supervisor snapshot has no running application, so leaving that environment unchanged correctly permits Wimp to reclaim/protect the application's pages. The harness does not change CAM permissions or write Wimp's private structures to evade that contract.

The task requests Wimp API version 310, preserving the 3.11-era interface boundary; the implementation reports version 366. Every task SWI returns in user mode. Read-only inspection using the assembled workspace symbols confirms Wimp selects its original MEMC path (`medusakernel = 0`). This first task retains its existing application space. Multiple application slots, task switching and memory-pressure behaviour remain unverified.

## Genuine source defect fixed

[0003-wimp-message-list.patch](../../patches/desktop-source/0003-wimp-message-list.patch) repairs `markinitialised` in the pinned `Wimp02` source. The routine saves R0–R4, uses R3 for `task_datasize` when allocating a task, then interprets R3 as the caller's message-interest list without restoring it. The original build reads low memory instead of the caller's list and silently rejects the requested diagnostic message.

The fix restores R3 from its existing saved stack slot immediately before list processing. No workspace layout, message policy or interface is invented. The module grows by one ARM2 instruction, to **81,548 bytes**, with 17,673 independently decoded integer instructions and the same 21 explicitly classified FPA instructions. Both ordinary assemblies and the observation build are identical, with zero unresolved symbols or relocations.

The regression verifies the actual copied list and then sends/delivers its message through the real queue. A reproducible negative control replaces only the restored `LDR R3,[SP,#12]` at module offset `&28D4` with a NOP. It registers `&89C` instead of `&4F415243` and fails the message-contract assertion, without a processor fault. The deliberately defective candidate stays under `build/wimp-stack/negative-input/`; it is never packaged as a usable module.

[Assembly hashes](reports/assembly.json), [negative-control evidence](reports/negative-control.json) and the original/modified manifest hashes identify the change. Reversing the complete desktop patch series restores every pinned source hash; applying it again restores the maintained tree without fuzz.

## Runtime evidence

Each cold run performs 74 explicit harness SWI calls and verifies:

- Window creation, open requests, redraw rectangles, null events and pointer enter/leave events.
- Keyboard focus and a genuine `a` key event through the IOC/keyboard path.
- Relative physical mouse movement, a Select click at `(400,412)` in the work area, and a real close-button request. The client handles the request with `Wimp_CloseWindow`.
- A private diagnostic message, explicitly registered in the task's interest list, delivered through `Wimp_SendMessage` and `Wimp_Poll`. Its action number is test data, not a claimed public SWI/message allocation.
- Real FPA instructions seed all eight extended registers and FPSR. Polling with the save-FP flag creates Wimp's genuine 100-byte save block; its contents and the restored registers match exactly. ARM2 undefined traps enter the software emulator on every poll. This covers one task's state preservation; independent FP contexts are also tested by the separate FPE gate, but two Wimp tasks are not yet covered.
- The client converts its work coordinates using the real redraw block and paints visible text inside the clip (404 checked ink pixels). Moving the window preserves **43,806 interior pixels exactly** at the expected translated coordinates. Closing it restores all **163,840 pixels** to the uniform desktop background.
- Window deletion, task closure, module finalization and resource release. No abort, address exception or unexpected FIQ occurs. Undefined traps are expected FPA execution, not masked failures.

Sampled instruction traces match emitted module bytes and their independently classified code offsets. They include 1,059 distinct Wimp instructions and 236 FPEmulator instructions, with 30 observations of the real undefined vector. Sampling does not prove complete path coverage; several loaded providers are outside the retained trace windows and have their own earlier runtime gates.

[Acceptance](reports/acceptance.json), [runtime calls/events](reports/runtime.json) and [trace audit](reports/trace-verification.json) are retained. Full phase traces, snapshots and framebuffer bytes remain under `build/wimp-stack/`.

## Appearance and dependencies

The selected source enables tiled colour-1 work areas. The speckled background comes from the reviewed public `tile_1` sprite and the real tiling code; it is not framebuffer corruption. The title furniture also uses the selected 3.60 assets. These are explicit visual differences to assess against 3.11, not proof of 3.11 identity.

The exercised mode-12 sprite and tiling paths work without a separate SpriteExtend runtime. That does not establish that every sprite operation, mode or Wimp configuration is independent of SpriteExtend. The earlier Super component is SuperSampler, not SpriteExtend.

The generated message-resource load addresses also now consistently encode text filetype `&FFF` (`&FFFFFF00`), correcting the earlier `&FF0` metadata. Payload bytes and module binaries are unaffected by that packaging correction, and all four runtime suites are repeated with the corrected records. No new upstream component or asset is introduced here. The existing [desktop licensing assessment](../../licenses/desktop/ASSESSMENT.md) and [FPEmulator assessment](../../licenses/FPEmulator-assessment.md) continue to apply. New diagnostic code is Apache-2.0. The baseline ROM, kernel and MacArch core are unchanged.

## Reproduce and next milestone

```sh
make wimp-test
```

This rebuilds the exact baseline, candidates and diagnostic client, verifies the source patch series, then performs the three cold runs and the negative control. `make test`, `make fpe-test`, `make renderer-test` and `make font-test` remain separate retained gates. Optional `python3 tools/wimp_preview.py` creates a mode-12 preview using Pillow.

Next, exercise two genuine application tasks, independent Wimp slots, inter-task messages and FP state under actual scheduling. Then pin/review the Desktop, Filer and TaskManager runtimes and their startup dependencies before joining an experimental desktop ROM. General applications, games, ARM3 behaviour and full **RISC OS 3.11 compatibility** remain separate acceptance work.
