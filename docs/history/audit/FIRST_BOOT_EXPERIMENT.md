# First implementation experiment: pre-conversion ARM2 assembly closure

**PLAN ONLY — do not execute until the Phase-0 findings have been reviewed.** This file retains the requested hand-off name; the audit recommends an assembly experiment before a boot experiment because the selected RO26 kernel is already known to contain unsuitable startup paths.

## One question

**Can the last published kernel before the April 2000 32-bit conversion be assembled for original A440/1 hardware using only identified, redistributable source inputs, with ARM2-safe reachable startup and exception code?**

This is exactly one experiment: produce and inspect the kernel component plus its assembly/include report. It does not attempt desktop integration, a CLI, a complete ROM or an emulator port. It can fail quickly on a missing public dependency or a non-isolatable architecture assumption, which would materially weaken the preferred derivative approach.

## Fixed source inputs

| Input | Exact revision | Use |
|---|---|---|
| `RiscOS/Sources/Kernel` | `24044755f08dc3b99779833a57eecf3899561ce6` | Candidate kernel, including `s/GetAll`, `s/NewReset`, `s/MEMC1`, POST and old workspace. This is the immediate parent of conversion commit `b4016e9c1087375ea105d5d5ad365d0f5afc0025`. |
| `RiscOS/Sources/Programmer/HdrSrc` | `c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b` | Original `hdr/Machine/A440`, ARM2, IOC-A1, MEMC1a/MEMC1, VIDC1a and WD1772 definitions. |
| `RiscOS/Sources/Programmer/HdrSrc` | `403c6dd8bce92d0629634cbf57f68f43b2f30d38` | Later public interface/header comparison only; do not let its Morris/ARM600 defaults override the original machine selection. |
| `RiscOS/BuildSys` | `5a1cb51c56a0c7c8b648c63d09f17ecae98d004a` | Reference for component/export mechanics, not proof of a compatible A440 product. |
| Other exported interface headers | Exact component pins in [SOURCE_AND_LICENSES](SOURCE_AND_LICENSES.md#inspected-repository-pins) | Add only if the kernel's include graph requires them, recording every chosen path/hash and its licence before assembling. Unresolved dependency = stop, not a guessed stub. |

Repository URLs and line-level support are [P1](SOURCE_AND_LICENSES.md#p1), [P2](SOURCE_AND_LICENSES.md#p2), [P3](SOURCE_AND_LICENSES.md#p3), [H2](SOURCE_AND_LICENSES.md#h2), [K12](SOURCE_AND_LICENSES.md#k12), [K19](SOURCE_AND_LICENSES.md#k19). These inputs are a **proposed hybrid**, not a known successful historical build. In particular, machine feature switches added after the old header need an explicit, reviewed setting from code/documentation; undefined symbols must not be silently set false.

## Procedure to hand to the implementing engineer

1. In a new isolated workspace, construct a text-only include/export manifest for the selected kernel entry source. Include generated message/help inputs and old workspace resolution. Record actual file search order and every licence. Stop if a required input has no lawful source.
2. Select the original A440 header and ARM2 path. Preserve the pre-conversion MEMC mapping, original-mode exception/startup branches and relevant hardware definitions. Do not transplant current RO26’s unconditional IRQ32 setup. Restore only necessary export/configuration glue, keeping a reviewable patch against the pinned inputs.
3. Use a lawfully available, version-recorded assembler compatible with the existing kernel recipe. The Makefile names **aasm**, but no runnable build command, assembler version or complete host/guest setup was validated in Phase 0. Resolve that prerequisite before running; do not claim an invented `make MACHINE=A440` command is sufficient.
4. Assemble the kernel component and produce a listing, symbols, selected-conditional report, include hashes and byte-range map. Check actual generated reachable startup, IRQ/FIQ/SWI and abort paths against ARM2 restrictions. Separate data tables from executable ranges, and review macros that emit words directly. Verify the selected memory layout/entry addresses against the original-machine configuration.
5. Record one pass/fail report and stop. Do not join/distribute a complete image, run an application or expand this into a desktop-port programme during this experiment.

## Exclusions and artifact assumptions

Exclude desktop/WIMP/Filer, application modules, outline fonts/desktop artwork, networking, Toolbox, option-ROM code and proprietary reference material from the artifact. The kernel’s embedded bitmap system font and other assembled tables are still payload: include their source/notice records, and stop if any selected input cannot be cleared. The inspected system-font source has an explicit Apache notice. [K20](SOURCE_AND_LICENSES.md#k20) Some of their public interface headers may still be legitimate assembler inputs; a header dependency is not inclusion of that module's payload.

The artifact is the kernel component produced by its source recipe, **not yet a MacArch-ready ROM**. The eventual logical ROM base is `0x03800000`, initial CPU execution is aliased at zero, and the candidate must establish safe mappings/stacks before use. A future joined image will require module-chain/footer agreement and board-capacity review. It is premature to pick a “tiny ROM” size from kernel source length. [K8](SOURCE_AND_LICENSES.md#k8) [M6](SOURCE_AND_LICENSES.md#m6) [M13](SOURCE_AND_LICENSES.md#m13) [B5](SOURCE_AND_LICENSES.md#b5)

**Required MacArch diagnostic hooks for this experiment: none.** Static assembly is the selected decisive test. The subsequent boot investigation would use trace-before-reset, execution checkpoints and MEMC/IOC/VIDC watchpoints through the existing core/headless path; that is a dependency note, not a second experiment or permission to change MacArch.

## Objective outcome

**Pass:** every included/generated input has recorded provenance; the real kernel assembles without unresolved symbols or borrowed binary inputs; selected original-machine code is visible in the listing; all reviewed reachable startup/exception paths use ARM2-compatible instructions and 26-bit mode conventions; mappings and workspace definitions are internally consistent; and no unexplained imported IOMD/VIDC20 dependency remains in those paths.

**Fail / stop classes:**

- Missing/unlicensed header, generator, resource or embedded fragment: source/licence closure failure; halt before distribution.
- Assembler unavailable or dialect unsupported: tooling blockage; do not conclude ARM2 hardware is impossible.
- Current-machine headers selected accidentally: configuration failure; report and correct within the experiment's narrow scope.
- Irreducible later-CPU/memory dependency in the selected kernel: architecture failure; reassess the historical revision or route before expanding work.
- No defensible executable-range analysis, unexplained output differences, or no stable build input manifest: inconclusive; not a pass.

Before sharing even this experimental binary, check all included file licences, generated tables and any tool-emitted runtime code; supply required Apache/BSD/other notices, mark modifications and keep reference ROM bytes/assets out. No binary release is authorised by this document.

**A pass proves only assembly/architecture closure for one component.** It does not prove reset reaches a prompt, nor FileSwitch, BASIC, WIMP or any 3.11 application works. Those remain the separate tier gates in [COMPATIBILITY_TEST_PLAN](COMPATIBILITY_TEST_PLAN.md).
