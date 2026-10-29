# Container changes and source provenance

## Packaging

The only target-image operation is deterministic padding:

```text
offset 000000–022B43: original 142,148-byte restored kernel, unchanged
offset 022B44–1FFFFF: 1,955,004 zero bytes
```

The ROM's reset instruction is the kernel's original selected non-POST entry, not an injected trampoline. The Utility-module chain word at SysModules_Info already points to EndOfKernel, whose zero word at `&03822B40` terminates the chain. The builder verifies that relationship. No synthetic module header, success handler, checksum bypass, changed origin, private ROM resource or extra executable instruction was introduced. Padding matches the kernel's `OSROM_ImageSize=2048` KiB configuration and gives a power-of-two contiguous ROM container.

MacArch's existing ROM loader accepts this LDR-to-PC reset form. Its normal ROM mapping and reset overlay are used unchanged. No linker, joiner executable or proprietary build tool is needed for this container.

## Preserved source and changes

The kernel remains the exact restored artifact with SHA-256 `6fb97a29134f6cea155d4b1ec0e9ca80f3c9f8e61672dd238eea32585a6851f1`, based on Kernel `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc` and its approved cohort. All original restoration patches, dependencies, licence records and tests remain in the companion restoration evidence package. baseline-preservation.json verifies all **524** files in its original checksum manifest.

This phase's patch series is intentionally empty: **zero kernel and zero emulator source patches**. Real new files comprise the ROM builder, external host harness, capture decoders/checkers and documentation. Host build adaptations are recorded in [RESULTS.md](RESULTS.md).

## Licensing

The kernel and its identified source inputs retain the restoration phase's Apache-2.0 notices and provenance. This phase carries `LICENSE`, and the evidence bundle includes the original restoration archive with upstream notices, source snapshots and patch series. The padding, new scripts and harness source are supplied under Apache-2.0. The container adds no third-party payload beyond the already reviewed kernel.

MacArch is a separate GPL-covered host tool; its supplied GPLv3 text is retained. The external harness links its unmodified core only on the host. No emulator runtime is linked into the target ROM. The evidence archive excludes native harness/emulator executables, build products and compiler caches; it records the source commit and build recipe instead. Distribution of a combined native harness binary would require the applicable GPL corresponding-source/notices obligations, rather than treating that binary as an Apache-only program.

No proprietary ROM was available to or used by the MCP session. No ROM was extracted, disassembled, copied or consulted. All snapshots and trace memory derive from this source-built kernel and the configured emulator's own RAM/device initial state. No external application, desktop asset or precompiled target module was added.

This identifies the experimental image's inputs and distribution terms. It does not clear the future full ROM's module/desktop/application asset set or establish the ultimate RISC OS 3.11 compatibility requirement.
