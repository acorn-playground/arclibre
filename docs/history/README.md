# How ArcLibre was restored

ArcLibre began as "Open Archimedes ROM": could the public cleaned RISC OS 3.60
sources be built into a ROM for the original Archimedes? 3.60 was written for
the Risc PC's ARM6 processors and IOMD; the Archimedes has ARM2 or ARM3,
MEMC1 and IOC. These are the write-ups of that work, in order.

- [audit/](audit/FEASIBILITY_AUDIT.md): the feasibility audit: sources and
  licences, the boot path, hardware, and the test strategy.
- [arm2-history](arm2-history/README.md): looking for a coherent
  original-machine source set in the public history (there wasn't one), and
  the restoration plan that followed.
- [arm2-kernel](arm2-kernel/README.md): the first attempt to assemble the
  kernel for the A440/1, which failed at its pinned revision.
- [arm2-restoration](arm2-restoration/README.md): the restoration patch
  series, the public interface definitions, the memory contract, and the
  first reproducible ARM2 kernel.
- [arm2-first-boot](arm2-first-boot/README.md): the first cold boot in
  MacArch, as far as module initialisation.
- [arm2-cam-transition](arm2-cam-transition/README.md): repairing MEMC1's
  CAM page mapping, reaching the Supervisor prompt.
- [arm2-text-rendering](arm2-text-rendering/README.md): the system font,
  misaligned for ARM2.
- [arm2-keyboard](arm2-keyboard/README.md),
  [arm2-messages](arm2-messages/README.md),
  [arm2-territory](arm2-territory/README.md),
  [arm2-intkey](arm2-intkey/README.md): the keyboard, MessageTrans and
  `*Help`, TerritoryManager and the UK territory, and the international
  keyboard.
- [arm2-floppy](arm2-floppy/README.md), [arm2-filing](arm2-filing/README.md),
  [arm2-filing-mcp](arm2-filing-mcp/RESULTS.md): ADFS and FileCore reading
  floppies through the 1772, 42 read-only filing scenarios, and the MacArch
  disc-change fix. Writing came next, in the maintained tree
  ([filing writes](../filing-writes/RESULTS.md)).

The last of these became the frozen baseline that `make baseline` still
rebuilds exactly; the desktop and everything after it is in the component
results in [docs/](../README.md).

These documents are kept as they were written, with two changes: links to
files that are not in this repository are plain text, and local paths are
removed. The experiments' scripts, source snapshots, logs and evidence
archives they refer to are in the project's development archive, not here;
the restored sources themselves are in `src/`, with every change in
`patches/`.
