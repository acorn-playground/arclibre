# Open Archimedes ROM — Source Audit and Feasibility Study

**Agent hand-off specification**  
**Date:** 25 October 2026  
**Phase:** 0 — investigation only  
**Status:** Do not implement until the findings have been reviewed.

## 1. Mission

Investigate whether it is technically and legally practical to produce a **freely redistributable, open-source ROM image for the original Acorn Archimedes family**, allowing people to use contemporary software in emulators (initially **MacArch**) without having to source a proprietary Acorn RISC OS ROM.

The non-negotiable compatibility target is **RISC OS 3.11 as experienced by existing Archimedes applications and games**. The ROM must ultimately run the established RISC OS 3.11 software library on ARM2/ARM3 machines using the original MEMC/VIDC/IOC chipset, without requiring proprietary Acorn ROMs or assets. Merely booting, presenting a shell, or behaving like a generic later RISC OS release is **not** an acceptable end state.

This is a **preservation and accessibility project**, not a commercial product and not an opportunity to redesign RISC OS. Keep it independent of MacArch so other emulators and, ultimately, real hardware can use it.

The initial task is **source archaeology, licence assessment and an actionable feasibility report**, not development. Do not start implementing a kernel, modifying the emulator or promising compatibility. Treat **binary/application compatibility with RISC OS 3.11** as the primary decision criterion throughout, rather than a secondary feature to add after successfully booting.

## 1A. Mandatory compatibility contract — RISC OS 3.11, not merely a booting ROM

**RISC OS 3.11 is the reference specification for observable behaviour.** The aim is to support existing, unmodified application and game binaries normally used under RISC OS 3.11. RISC OS 3.10 may serve as a supporting historical comparison, but **do not substitute it for the 3.11 target**. Later RISC OS 3.5x/4/5 compatibility does not demonstrate that 3.11 software works on the original MEMC-based machines.

For the Phase-0 audit, define and assess at least these compatibility tiers:

| Tier | Expected behaviour | Use in decision |
| --- | --- | --- |
| 0 — Boot | Reset, initialise original hardware, display an error or prompt | Engineering milestone only; not project success |
| 1 — Core OS | SWIs, OS vectors, `*` commands, VDU, module handling, memory APIs, system variables and errors respond like 3.11 | Necessary foundation |
| 2 — File/software loading | ADFS/FileSwitch, filetypes, `!Run`/`!Boot` conventions, absolute binaries, modules and disc images work | Necessary for real software |
| 3 — RISC OS 3.11 desktop | WIMP, Window Manager, Filer, icon bar, sprites, fonts, tasking, menus, drag/drop, window events and desktop application startup work | Necessary for mainstream 3.11 applications |
| 4 — Established software library | Representative unmodified games, utilities, BASIC programs and desktop applications behave correctly | **Actual project success criterion** |

Distinguish **documented API compatibility**, **observed 3.11 implementation quirks** that applications rely on, and **direct hardware access** by games. Existing software may depend on all three. Do not treat theoretically compliant SWI implementations as proof that applications will work.

The final goal does **not** require the replacement ROM to be internally identical to RISC OS 3.11, to copy the desktop artwork, or to falsely claim to be an official RISC OS release. It *does* require ABI-level and practical compatibility. Investigate whether the visible OS version number, module names/versions, errors, memory map, service-call ordering, fixed addresses or timing need compatibility shims for programs that test them. Do not hard-code `3.11` as a blanket lie if essential behaviour is still absent: document the practical trade-offs and how tests would catch regressions.

For every proposed port path, ask **not only “can it boot?” but “what specifically prevents a typical 3.11 application from running?”** If the answer includes missing desktop modules, changed memory semantics, incompatible resource handling or later-only assumptions, these are first-class blockers in the report.

## 2. Critical distinction: two implementation routes

Evaluate these separately. Do **not** conflate an open-source derivative with a clean-room reimplementation.

### Route A — Port openly licensed RISC OS code (preferred starting hypothesis)

Study the RISC OS Open source tree and the independent **RO26 / “twentysix”** effort. Determine whether the published, suitably licensed source can be configured or adapted for ARM2/ARM3 and the original MEMC/VIDC/IOC chipset. Establish the engineering work required to produce a bootable ROM and the licensing provenance of **every included component and asset**.

This is a port/derivative, **not clean-room development**. The premise that released sources are generally Apache-2.0 licensed is a starting hypothesis; verify licences at file/component level rather than assuming all artifacts, historic branches, fonts, applications and build tools carry the same terms.

### Route B — Independently implemented compatible ROM

Assess the fallback: a newly written kernel and compatible RISC OS interfaces, relying on published hardware and OS specifications plus lawful black-box behavioural testing. Include a legally disciplined clean-room protocol: one role writes interface specifications and test cases from permissible sources, another implements from those specifications; no unlicensed source, disassembly, protected resources or original ROM bytes in the new implementation. Identify specialist legal questions needing advice.

Estimate this route separately. It may offer stronger independence but is likely much more work.

**Do not decide between the routes based on ideology.** Base the recommendation on source availability, compatibility, licensing, ROM size, build dependencies, and work required to boot real software.

## 3. Scope and priority platforms

### Primary technical target

- **Acorn A440/1**, baseline ARM2, with an ARM3-upgraded configuration as a second variant.
- Classic 26-bit ARM execution model and exceptions.
- MEMC/MEMC1a, VIDC1/VIDC1a and IOC peripherals; keyboard, display and timing at minimum.
- **RISC OS 3.11** observable behaviour as the authoritative compatibility baseline; 3.10 is a secondary historical comparator only (neither is permission to copy implementation).
- **MacArch** is the initial testbed. Inspect its actual hardware configurations, ROM loading, debugger and test facilities instead of assuming particular capabilities.

### Secondary compatibility targets

A3000, A5000 and other original Archimedes models. Record chipset and ROM-format differences, notably ARM250-integrated machines (A3010/A3020/A4000) and original A305/A310/A440 ROM-carrier requirements. Do **not** assume a single image works across all models.

### Out of scope for Phase 0

- Building or patching the OS or emulator.
- Distributing proprietary ROMs, boot applications, fonts or other binaries.
- New GUI design, modern APIs, networking, graphics acceleration or novel OS features.
- Flashing original hardware or ordering ROM boards.
- Claiming that a Risc PC-compatible 26-bit ROM automatically supports ARM2/ARM3.

## 4. Starting sources — verify availability, contents and provenance

Explore these sources before searching random ROM archives:

1. **RO26 project home:** https://www.marutan.net/ro26/  
   26-bit build assembled from released RISC OS sources, principally targeting Risc PC/A7000-era systems. Find its documentation, source links, reported hardware requirements, known issues and release history.
2. **RO26 release discussion:** https://stardot.org.uk/forums/viewtopic.php?t=28331  
   The author reported in June 2024 that source had been published in the **`twentysix`** branch at **https://gitlab.4corn.co.uk/explore**. Discover the exact repos and commit IDs; do not invent them. The same discussion notes potentially important constraints involving StrongARM and 4 MB images.
3. **RISC OS Open:** https://www.riscosopen.org/  
   Find source repositories, build documentation, licences, source archives, machine build configuration, historical revisions and ROM build tools. The server may be rate-limited or require alternate access; record exactly what could or could not be obtained.
4. **RISC OS build guide:** https://www.riscosopen.org/wiki/documentation/show/Developer%27s%20guide%20to%20RISC%20OS%20builds  
   Use as a starting point for phase structure, dependencies and toolchain questions.
5. **RISC OS 3.1 platform reference:** https://riscos.com/riscos/310/index.php  
   Historical model/ROM compatibility (treat vendor historical claims as documentation, not licensing permission).
6. **Programmer's reference manuals and hardware documentation:** https://www.4corn.co.uk/archive/docs/  
   Locate precise ARM chipset, memory mapping, module, SWI, FileSwitch and WIMP references. Treat archived manuals as research sources, not automatically redistributable assets.
7. **Pyromaniac (independent behavioural reference, not an ARM ROM):** https://pyromaniac.riscos.online/  
   Assess whether its RISC OS compatibility approach or published API documentation can help; verify its release/source status independently.
8. **Cross-check emulator behaviour, if helpful:** https://github.com/RichardBrown384/Eichhoernchen and https://github.com/andrewtimmins/rpcemu-extended  
   These are reference environments for different hardware generations, not substitutes for the target MacArch configuration.

When these pages disagree or are inaccessible, distinguish **verified facts**, **source-author statements**, **inferences** and **unknowns**. Prefer actual file evidence to forum recollections.

## 5. Research work packages

### WP1 — Repository and licence archaeology

- Locate actual RISC OS Open repositories, historic/pre-HAL kernel revisions and RO26's `twentysix` branches; document clone/access instructions and exact commit or release IDs.
- Determine whether RO26 is a complete reproducible tree, branch set, patch series or binary-only release; determine where its components come from.
- Identify source licences and third-party exceptions for every likely ROM component: kernel, modules, desktop, command shell, FileSwitch/ADFS, fonts, sprites, international resources, BASIC, libraries, boot assets and tools.
- Classify components: **clearly redistributable**, **conditional/notice-required**, **unclear**, **proprietary/not redistributable**, or **not found**.
- Check if the build requires proprietary DDE/Norcroft/assembler tools; distinguish a non-free *build-time dependency* from a non-free *ROM payload*. Look for credible fully redistributable build alternatives.
- Establish whether a non-proprietary image can be redistributed **with all required attributions/notices and without ROM/resource fragments of unknown provenance**.

**Deliverable:** `SOURCE_AND_LICENSES.md`, with repository URLs, refs, file paths and component-by-component evidence. Highlight hard blockers, not just inconvenience.

### WP2 — Original-machine hardware support audit

Search for implementations, conditional assembly, interfaces and historical remnants associated with:

- ARM2 and ARM3 startup, 26-bit PC/status semantics, processor modes, SWIs, IRQ/FIQ, vectors and abort handling.
- MEMC/MEMC1a: physical/virtual mapping, page sizes, RAM detection, ROM mapping, DMA and reset state.
- VIDC1/VIDC1a: video modes, framebuffer, palette, cursor, sound and screen memory arrangement.
- IOC: timers, interrupts, keyboard, mouse, peripheral address decoding and device discovery.
- Machine-specific identification and settings/CMOS assumptions.
- Floppy, ADFS, ST506, IDE, SCSI and other storage drivers (identify minimum needed to load one disk image).
- Module loader, RMA and memory layout assumptions.

For each subsystem document: **exact path + symbol/conditional or branch + what it actually does + whether usable unchanged, adaptable or missing**. A constant named `MEMC` is not evidence of a working MEMC driver. Distinguish historic Acorn prototypes, Risc PC IOMD/VIDC20, StrongARM and ARM250 paths from the A440/1 hardware.

**Deliverable:** `HARDWARE_COMPATIBILITY_MATRIX.md`.

### WP3 — Boot sequence and ROM packaging

Trace the actual boot path from reset vector to a working CLI and then to desktop. Identify:

- Reset vector, ROM placement, startup stack and earliest memory mapping.
- CPU compatibility of earliest executed instructions, including ARM2-incompatible instruction variants.
- RAM detection and MMU/MEMC table setup; exception and SWI dispatch.
- ROM module directory, module initialisation order, service calls, ROM filesystem and required resources.
- VDU initialization, keyboard input and console output.
- FileSwitch/ADFS and desktop prerequisites.
- ROM checksum/header/relocation/interleave expectations as implemented by target emulator and real ROM sockets.
- **ROM footprint**: actual baseline RISC OS 3.1 ROM size, RO26 image size, the hardware's achievable mapping/capacity, options to omit components or expand physical storage. Do not simply assume a 4MB image can be fitted into 2MB hardware, nor assume ROM bank switching exists.

Produce a dependency graph with the **smallest credible path to a prompt**, another for **running an existing `.Absolute` program**, and a third showing what must be present to launch a typical **RISC OS 3.11 desktop application**. Treat the CLI as an intermediate milestone, not the end goal.

**Deliverable:** `BOOT_PATH.md` with evidence and diagram (Mermaid acceptable).

### WP4 — RISC OS 3.11 application/binary compatibility gap (principal product requirement)

Define a representative **RISC OS 3.11** baseline for actual shipped games and desktop software running on ARM2/ARM3. The report must explain the functional gap between a booting ROM and a practically useful replacement capable of running existing 3.11 programs. Examine requirements such as:

- RISC OS **3.11-era** OS SWIs and their register, flags, error, callback and side-effect contracts; `*` commands, system variables, VDU behaviour, BBC BASIC runtime assumptions.
- FileSwitch, ADFS, RMA, Relocatable Modules, resource file paths, filetypes, application directories, `!Boot`, `!Run`, `!Sprites` and relevant desktop startup conventions.
- The **3.11** WIMP, Window Manager, Font Manager, SpriteOps, Draw facilities, Filer, icon bar, menu/events, inter-task messaging and desktop tasking. Flag modules/interfaces absent from 3.11 rather than mistakenly making later APIs mandatory; treat Toolbox as version/extension-dependent.
- Legacy code that reads/writes hardware directly, patches vectors, relies on fixed addresses, undocumented behaviours or timing.
- ARM2/ARM3 instruction compatibility, 26-bit address model, memory constraints, loaders/copy protection and version-detection behaviours.
- RISC OS 3.11 module inventory and boot/desktop resource dependencies, checked against candidate open-source versions, including changes in API contracts and memory maps.
- Whether failures stem from missing OS features, altered semantics, unsupported hardware behaviour, insufficient ROM space, or unlicensed dependencies. Report these categories separately.

Propose a **small, reproducible, 3.11-anchored compatibility corpus**, with coverage and increasing difficulty:

1. Self-authored ARM2 assembly/SWI/VDU/exception and memory tests with precise expected results.
2. A self-authored BASIC test and a command-line utility exercising FileSwitch and modules.
3. A self-authored WIMP program testing window creation, redraw, messages, menus, icon bar and basic multitasking.
4. A representative set of **existing unmodified 3.11-era programs**: several desktop applications/utilities, BASIC applications and games covering WIMP, filing, sprites, palette/modes, sound, timing, keyboard/mouse and direct hardware access. Make a proposed *selection* with rationale; do not claim tests were run or rely on one game as proof.
5. A deliberate negative/compatibility-boundary set: known RISC OS 2-specific or later-version software, to document expected exclusions rather than silently broadening the promise.

Only use test software that the user can lawfully supply. A valid reference run requires a user-provided/licensed original 3.11 ROM; **do not bundle or fetch proprietary binaries**. Public regression suites should contain only original tests and redistributable fixtures.

Tests must capture **observable RISC OS 3.11 behaviour**, not extracted operating-system implementation. Be explicit about side effects, registers, error semantics, flags, output, file-system results, UI events and timing where material. Recommend a baseline comparison harness in MacArch using a legally obtained 3.11 ROM, debugger/MCP hooks, deterministic snapshots and repeatable inputs; **do not implement the harness yet**.

Design a pass/fail scorecard by compatibility tier and software category: **boots / reaches CLI / executes binary / runs WIMP desktop / launches target application / correct behaviour over a representative session**. Report crashes, missing functionality, rendering defects, incorrect sound/input, file corruption and non-deterministic failures separately. Every claimed 3.11-compatibility milestone must be backed by actual application-level testing, not a ROM version string or SWI-count percentage.

**Deliverable:** `COMPATIBILITY_TEST_PLAN.md`, including a **3.11 feature/API coverage matrix**, representative software selection and explicit evidence-based acceptance thresholds (proposed, not invented measured results).

### WP5 — Toolchain, development cycle and distribution

Investigate whether a small first-boot experiment can be assembled from the released tree on a modern Mac/Linux host. Specify:

- Host/toolchain prerequisites and licences.
- Reproducible pinned revisions and exact build configuration (or explain missing information).
- ROM artifact format expected by MacArch; whether it can currently load custom, size-varied ROMs. Do not assume it can.
- Useful diagnostics: emulator reset trace, SWI trace, memory writes, IO logging and deterministic snapshots if available.
- Build validation and automated regression strategy.
- Route to testing against a **second independent emulator** before actual hardware.
- Physical ROM manufacturing constraints and safety risks as a later phase only.

**Deliverable:** `BUILD_AND_TEST_STRATEGY.md`.

## 6. Alternatives and decision criteria

Compare at least three pathways:

1. **Port/trim RO26 for A440/1** (or selectively backport published components).
2. **Build an original ARM2/MEMC configuration from other open RISC OS source revisions** (if distinct from 1).
3. **Clean-room implementation** of a minimal RISC OS 3.1-compatible ROM.

Score each qualitatively (Low / Medium / High / Unknown) and provide reasoning for:

- **Licence confidence and redistributability** (must be a hard gate).
- Availability and fitness of real source files.
- Earliest credible ROM boot milestone.
- Feasibility on **ARM2**, not just an ARM3/StrongARM or Risc PC.
- MEMC/VIDC/IOC availability.
- Size of original-machine ROM footprint and acceptable hardware adaptations.
- **Likely RISC OS 3.11 application/library compatibility** by tier and by representative software class (not generic RISC OS binary compatibility), including direct-hardware-access pitfalls.
- Toolchain dependency risk.
- Testability in MacArch and another emulator.
- Complexity, major unknowns, and likely order of effort (no invented precision).

Give the recommended route plus explicit **conditions that would change that recommendation**. State whether ROM compatibility for emulators could realistically be achieved before real-hardware compatibility; do not lower the final ambition silently.

## 7. First implementation experiment — plan only

Design exactly **one small, decisive first coding experiment**, not a broad multistage implementation programme.

The preferred **early engineering** test, *if the source audit supports it*, is:

> Produce a minimal independently redistributable ARM2-compatible ROM image which MacArch can reset into and which reaches an observable checkpoint (emulator serial/log signal or a simple VIDC text display), then advances to an interactive CLI if practical.

If the source audit shows this is the wrong experiment, propose a better falsifiable test (for example, isolating and assembling a candidate pre-HAL startup/kernel against ARM2 instruction restrictions).

For the experiment specify:

- Input source tree and exact base commits.
- Components intentionally excluded.
- Toolchain and commands **only if verified**.
- Expected ROM format and memory/entry-point assumptions.
- Required MacArch diagnostic hooks.
- Objective pass/fail signals and indicative failure classes.
- Legal/licence checks necessary before distributing even an experimental binary.
- Stop conditions and what a failure means (e.g. build toolchain defect versus architecture incompatibility).

Do not execute this experiment during Phase 0. Passing this boot experiment must **not** be reported as proving RISC OS 3.11 compatibility; the Phase-0 report must retain a separate path from that milestone through WIMP and real application acceptance tests.

## 8. Required final output

Create **new documentation files only**, e.g. under `docs/open-archimedes-rom-audit/` in a designated audit workspace; do not overwrite or refactor MacArch or the source repositories:

1. `EXECUTIVE_SUMMARY.md` — one-page verdict: **GO / CONDITIONAL GO / NO-GO**, recommended route, top five discoveries, biggest blockers and next action.
2. `SOURCE_AND_LICENSES.md` — provenance, licences and distribution blockers.
3. `HARDWARE_COMPATIBILITY_MATRIX.md` — architecture/chipset source inventory with paths and references.
4. `BOOT_PATH.md` — reset-to-prompt dependencies and ROM constraints.
5. `COMPATIBILITY_TEST_PLAN.md` — RISC OS **3.11-specific** compatibility matrix, legal baseline/differential testing strategy and real-software acceptance corpus.
6. `BUILD_AND_TEST_STRATEGY.md` — toolchain, emulator, physical-ROM and reproducibility plan.
7. `FIRST_BOOT_EXPERIMENT.md` — tightly scoped implementable next hand-off.
8. `OPEN_QUESTIONS.md` — blockers, evidence quality and suggested next investigations.

Every substantial finding must include a source URL and, for source-code claims, **repository + branch/commit + file path + relevant symbol/line range**. Include a traceable table of evidence and clearly mark anything not verified because access failed. Do not manufacture file names, commit hashes, commands, compatibility claims or licence grants.

## 9. Phase-0 acceptance criteria

The audit is complete only if another engineer can answer:

- What *exactly* is in RO26's `twentysix` source, and where?
- How much usable ARM2/ARM3 and MEMC/VIDC/IOC support survives in genuinely released, correctly licensed source?
- What happens after reset on an A440/1; which specific source modules are missing or wrong?
- Does the hardware's actual ROM capacity make a complete port implausible? If so, which viable alternatives exist?
- Can all content in a candidate image be built and legally redistributed without proprietary ROM bytes?
- What proportion of the 3.11 desktop/application stack is available with redistributable provenance, and which missing components block ordinary 3.11 software?
- Can the preferred approach plausibly provide the **RISC OS 3.11 desktop and application ABI**, not merely a boot prompt, within the original hardware constraints?
- What is the smallest experiment that could disprove the preferred approach quickly?
- Would the independent clean-room route materially change the conclusion?

A useful **NO-GO** finding with concrete blockers is more valuable than a speculative optimistic implementation plan.

## 10. Guardrails for the coding agent

- **Stop after research and writing the audit. Do not write kernel/emulator code yet.**
- Use existing public source, permissibly available documentation and licence-compliant research. Do not hunt down, copy, embed or publish proprietary ROM binaries or protected assets.
- Do not reverse-engineer by copying decompiled/disassembled proprietary code into the proposed replacement. For route B, keep interface analysis and implementation separate and seek legal review of the intended method.
- No changes to MacArch source or configuration, no automated changes to the developer's machine, no destructive shell operations.
- No publishing or pushing source, binaries or analysis to external services without instruction.
- If GitLab cannot be accessed, try documented archives or public mirrors, report which attempts failed, and continue with a partial evidence-based assessment; **do not silently infer the missing code's contents**.
- Do not let Risc PC/StrongARM success substitute for proof of ARM2/ARM3 compatibility.
- **Do not label an OS image a 3.11 replacement merely because it boots.** Every feasibility conclusion must address actual 3.11 software and desktop compatibility.
- Verify all licences of *resources as well as code*. An open kernel does not imply a redistributable complete ROM.
- Explicitly say what additional input from the owner is truly required (for example, a local MacArch repository path or a lawful original ROM for privately run baseline tests). Do not block source audit unnecessarily.

## 11. Suggested agent kickoff instruction

> Read this specification in full. Perform **Phase 0 only**. Begin by finding the exact published `twentysix` source branches and their relationship to the RISC OS Open tree, then audit ARM2/ARM3 + MEMC/VIDC/IOC support, licences and boot dependencies. Inspect MacArch read-only if its repository is available. Produce the eight Markdown reports listed here, with verifiable code references and a clear go/no-go recommendation. **Do not build a ROM or change implementation code.** Ask only if an essential permission or inaccessible private repository prevents a specific part of the audit; otherwise make progress with the available sources.

---

**End of Phase-0 brief.** A future Phase-1 build specification should be derived from evidence in this audit, not drafted in advance.
