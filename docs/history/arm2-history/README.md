# Historical source-coherence investigation

25 October 2026. Original A440/1, ARM2 and 26-bit RISC OS. Kernel only.

**No internally coherent, publicly recoverable original-machine source set was established in the examined history.** The oldest substantial kernel import already has original-workspace inconsistencies; matching historical global headers were omitted from the public history. Later branches do not supply a repaired original workspace.

- [Results and stop decision](RESULTS.md)
- [Dependency introduction timeline and branch findings](HISTORY.md)
- [Specific restoration plan and estimates](RESTORATION_PLAN.md)
- [Dependencies, reproduction and licensing](DEPENDENCIES.md)
- Exact source cohort, file hashes, repository coverage
- AsAsm result and complete diagnostic log

The strict 3.60-cohort probe failed input closure and AsAsm subsequently aborted. **No valid kernel binary exists.** The recovered source files, history evidence and restoration design are the artifacts of this phase. This is not a claim that an ARM2 restoration is impossible, nor that the public mirror exhausts every possible archive.

The eventual acceptance target remains high **RISC OS 3.11 application compatibility**, including its original desktop, games and utilities. A 3.60 source baseline is a restoration candidate, not a replacement compatibility target. No ROM joining, MacArch testing, emulator changes or desktop integration occurred.
