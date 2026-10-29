# Roadmap to RISC OS 3.11 desktop compatibility

The target remains unmodified RISC OS 3.11 applications and games on original
ARM2/ARM3 Archimedes hardware. The public 3.60 cohort supplies implementations;
its version number does not establish 3.11 compatibility.

The desktop is running. Kernel restoration, software floating point, rendering,
fonts, Wimp input and multitasking, Filer, Pinboard, original-machine sound,
ADFS floppy/ST506 filing, and native Draw/Paint/Edit editing have defined passing
gates. SpriteUtils now supplies the original sprite commands needed by Nevryon.
Zarch has bounded flight/fire/input coverage; Nevryon reaches its title screen.
These remain scoped tests, not complete applications or games certification.

The [standard-service audit](../system-audit/RESULTS.md) now compares the actual
ArcLibre ROM with all 88 modules observed in the user's RISC OS 3.11 ROM. It
replaces the earlier assumption that no usable reference module roster existed.
That audit recorded 44 matching titles and 43 absent titles. The restored
task, stream, RAM filing and standard utilities bring this to 54 matching titles, 33 absent titles,
and ArcPalette as one partial replacement. Hardware-dependent and historical patch modules are identified
separately; those counts are not a compatibility percentage.

1. **TaskWindow and FilterManager — implemented.** The pinned implementations
   pass real CPU-bound pre-emption, integer/software-FPA context preservation,
   parent/child messaging, Edit/BASIC input/Escape/exit, cleanup and filter
   ordering/masking/claim/self-removal gates. See [results](../task-services/RESULTS.md).
2. **Character streams and RAM filing — implemented.** DeviceFS/SystemDevices,
   PipeFS and RamFS/RAMFSFiler/Free pass real blocking/EOF, device lifecycle,
   resizing, full-media errors, icon opening and live free-space gates. DOSFS
   remains separate: resolve its [boot-sector and header-tool review](../dosfs/RESULTS.md)
   before importing runtime assets, then test FAT12/FAT16 access and formatting
   against an independent parser. Preserve the ADFS/ST506 gates throughout.
3. **Bundled utilities and settings.** Review the actual assets and coherent
   dependencies for Alarm, Chars, Help and Configure. Complete Palette workflows,
   and resolve original Calc provenance without substituting SciCalc silently.
   ScreenBlanker and StringLib now have functional cold-boot gates. Next restore
   Squash's public SWIs and the original Chars/Help applications; bring up
   RTCAdjust/IIC before claiming Alarm or clock-setting coverage. Test real
   compression workspaces/errors, help messages, character insertion and
   application lifecycle, not just icon-bar presence.
4. **Printing and original-machine hardware contracts.** A genuine printer
   pipeline with independently checked output; serial/parallel, podule and IIC
   interfaces; ARM3 cache/control behaviour. Do not use the ARM600-only ARM
   module as ARM3Support. Network services require an explicit profile and tests.
5. **Wider software and physical-hardware validation.** Longer game sessions,
   more unmodified applications, SWI/error/timing coverage, dirty-media and
   interrupted-write recovery, and actual ARM2/ARM3 hardware. A visible desktop
   is not the final compatibility gate.

Measure code/resources before each integration; the [current release report](../archimedes-desktop/RESULTS.md)
records occupancy. Compiler optimisation saved 23,660 bytes and every original
editor remains in the 2 MiB ROM. Plan ROM versus support-disk residency explicitly, retain
provenance and licences, and never replace missing services with success stubs.
Every milestone keeps existing cold-boot, memory, exception and instruction gates.

Current evidence: [compatibility checklist](../maintained-tree/COMPATIBILITY.md),
[application editing](../graphics-apps/EDITING.md),
[SpriteUtils](../spriteutils/RESULTS.md),
[service and command inventory](../system-audit/RESULTS.md).
