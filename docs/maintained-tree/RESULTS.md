# Maintained source-tree migration

## Result

The maintained build reproduces the exact existing ARM2 kernel, every appended module and the 2 MiB ROM. Both complete runtime suites passed: the maintained checkout and an independent source export with no experiments directory or Git metadata. The clean export rebuilt its host tools from the supplied source archives and passed `make test`, including all three cold boots and 42 filing scenarios. All 831 build/test input files match the final maintained tree byte-for-byte. See [acceptance](reports/acceptance.json), [clean-export verification](reports/clean-export-verification.json) and the other reports in `reports/`.

```text
ROM    bf5ca56ebd6f7fd7dc4149360d97f76f009abed8879693470421998d59f11791
Kernel cd2c3eb18de6ffab8fabb59406efb50eafd6851c305a58e88e2cc554facfcc30
```

No guest behavior or ROM payload was added in this migration. The target remains RISC OS 3.11 compatibility; the cleaned public 3.60 source cohort remains the implementation baseline, not a replacement compatibility requirement.

## Layout and build changes

`src/` is now the authoritative, editable source tree. It contains the restored Kernel and real modules, their public headers and source resources, plus the shared header dependencies. The existing restoration patches are already applied. The original component names and assembly organization are retained; this was not an assembly rewrite or a module-boundary redesign.

`tools/` holds one build recipe, normal/instrumented assembly, the independent instruction decoder, module audit, workspace/routine checks, public-interface review, resource packing and source export. `tests/` holds the shared native harnesses, original generated-media sources and independent result verifiers. `manifests/` records component origins, source import hashes, header mappings, tool dependencies and the frozen migration ROM hashes.

Host tools and all generated files now live under ignored `build/`; release exports live under ignored `dist/`. The build regenerates kernel/module help, the compressed TerritoryManager sprite and the Messages pack rather than copying them from an experiment. Neither building nor testing imports an earlier experiment's working directory, ROM, kernel object, compiled tool, snapshot or trace.

The kernel and module header maps are explicit. The restored FileSwitch LowFSI header is shared rather than maintaining two copies whose ENTRY spelling differed. The module-specific Generic26 settling header remains an explicit export override. Exact target hashes demonstrate that this consolidation preserves the current configuration.

## Preserved checks

The kernel has 145,152 bytes and 27,870 independently decoded instruction words. Two normal assemblies and the observer assembly must produce identical AOF objects. The kernel and all modules have zero unresolved symbols and zero relocations. The independent ARM2 decoder, modern-instruction negative controls, 26-bit mode checks, MEMC workspace contract, settling checks, direct branch validation and bounded routine tests remain.

The original review of 303 consumed public interface definitions remains enforced. It checks accepted names, header origins and values, and regenerates caller evidence. The unchanged original MEMC workspace source has a separately frozen hash.

The runtime suite retains three cold boots; natural initialization and CAM page-transfer cases; resident keyboard, MessageTrans, territories and IntKey tests; font and active-pixel comparisons; original floppy reads and sampled FIQ entry/return instruction checks; and fourteen expanded filing scenarios per cold run, for 42 scenarios overall. All filing media remain write-protected, with empty overlays and exact data comparisons.

Two failure controls are executed afresh. The unpatched pinned MacArch core must reproduce stale media after swapping discs. A separate kernel-only negative ROM replaces only the restored CDA skip branch with a NOP, preserving addresses while reintroducing the old fall-through; it must reach the genuine CAM failure. The defective negative ROM is test output only, never the delivered ROM. This replaces a dependency on historical saved negative-control results with an actual repeated test.

Historical preservation checks that opened old experiment SHA256SUMS during every runtime test are no longer build dependencies. The original files remain unchanged in Git, and the migration provenance records where each maintained file came from. The standalone runtime tests check their current build artifacts and frozen contracts directly.

## Host toolchain and licensing

The normal AsAsm, observation-only AsAsm and tokeniser were rebuilt locally. Bootstrap uses pinned public GCCSDK and official GNU source archives, supplied Darwin layout headers and installed Apple/GNU developer prerequisites. The fresh bootstrap needed both GNU Libtool's own aclocal directory and the host prefix's aclocal directory so pkg-config macros were available. No assembler instruction-encoding change was made.

MacArch is still a separate host dependency. Its pinned core and the already-verified device patch are extracted into isolated test build directories; the installed application/server and external checkout were not changed by this migration.

Original source notices and licences remain. 129 restored source inputs received prominent ArcLibre modification notices; these are comment-only changes. Their imported and maintained hashes are separately recorded. Generated help/resource data is absent from the maintained source and rebuilt on demand. Upstream Git-control files were omitted from `src/` so their ignore rules cannot conceal maintained inputs; the original snapshots retain them.

The expanded root LICENSING.md identifies exact public repositories/revisions, explains what recovered sources and retained assessments mean, distinguishes project modifications, and describes the UK message-resource qualification and BSD/GPL host dependencies. It makes no blanket licence claim for future desktop assets or applications.

## Reproduction and next work

Use `make rom`, `make baseline` or `make test` as described in BUILD.md. `make source-package` exports the maintained build inputs and licences without the experiments or compiled tools.

The milestone delivered the source package and the clean-tested ROM, with SHA-256 sidecars, and an evidence archive of the full clean-run artifacts and logs. The final source export adds these reports and documentation to the tested inputs; no build input changed after the clean run.

The next implementation milestone can now work directly in `src/`: controlled filing writes on disposable generated images, with the existing read-only and boot suite retained. No write functionality, desktop integration or general application compatibility work began during this migration.
