# Restored public-interface provenance

The maintained kernel and matching header cohort are identified in [kernel-cohort.json](../manifests/kernel-cohort.json). The kernel is pinned at `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc`; matching HdrSrc is `c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b`. Their exported sources carry Apache-2.0 licences and Acorn notices.

Nine missing public registration headers use HdrSrc revision `403c6dd8bce92d0629634cbf57f68f43b2f30d38`: SWIs, CMOS, Services, FSNumbers, NewErrors, UpCall, Pointer, DevNos and PaletteV. Their original files and licence are in [src/PublicInterfaces](../src/PublicInterfaces); exact upstream hashes are in [public-interface-files.json](../manifests/public-interface-files.json). Additional public allocation headers needed by the modules remain in that component's `hdr/` directory with the same documented upstream pin.

These definitions supply public allocations, not substitute kernel workspaces or machine implementations. The maintained kernel enforces the original [303-definition review](../manifests/public-interface-review.json) through `tools/interface_manifest.py`: 139 error definitions, 78 CMOS definitions, 33 services, 28 SWI definitions, 16 device definitions, seven palette-vector definitions and two UpCall definitions. The report records original declarations, selected values, callers, contracts and acceptance decisions.

Actual header exports are explicit in [header-exports.json](../manifests/header-exports.json). The original MEMC workspace source has a separately frozen hash in [contracts.json](../manifests/contracts.json). ARM2, 26-bit processor and memory/workspace checks are independent build gates.

The original detailed interface/licensing investigation is in [docs/history/arm2-restoration/INTERFACES_AND_LICENSING.md](../docs/history/arm2-restoration/INTERFACES_AND_LICENSING.md). It is historical evidence, not a dependency of the maintained build. Preserving public interface values does not prove every RISC OS 3.11 behavior.
