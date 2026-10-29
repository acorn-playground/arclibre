# Dependencies, modifications and reproduction

## Exact source cohort

All thirteen selected component commits have the subject **“Import from cleaned 360 CD”**. Matching import provenance is stronger evidence than selecting unrelated commits merely because their dates are close. It still does not establish complete source closure: registration files and a matching product build environment are missing from the published cohort, and some published files were cleaned/reintroduced later.

| Component | Revision |
|---|---|
| Kernel | `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc` |
| HdrSrc | `c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b` |
| Buffers | `be2e051d01382492b65a1685d1f33e8ef4935444` |
| Colours | `873e823dc654dcd2deb964c69651e43db6221c77` |
| FileSwitch | `93c7e2e094c314940237f6256e77edae2486419b` |
| FontManager | `f883f98662b95d16a03129835883f79a935910fd` |
| MsgTrans | `2a006cd1d002bda2d7454764fe4b93f734f17598` |
| Podule | `b33cb3fa32376b243c94d3870b33697f30cd9a70` |
| Portable | `e5f03547d739b9b5a5f58f719f769e7a9916fbf4` |
| Serial | `4d0e504f000ea706a6d07c69e35d82380b02c797` |
| Sound0 | `9bd59f38c9b7caff055eff8ff308cce832e52b47` |
| TerritoryManager | `e2654fe5c068ae403d13cb09f03e5162895a736f` |
| Wimp | `530acd4a18ffa97ce7a6b5b20fdef0a4db3ef647` |

Repository URLs and pins, all recovered file hashes, export ownership. The recovery selects kernel source/header/test-source/help/version/recipe/licence files and module header/recipe/licence files. It does not copy prebuilt `rm` or `o` objects, complete module payloads or ROM images. This is a bounded source recovery, not a claim that the entire future include graph has been traversed.

The historical Kernel Makefile names `aasm`, `tokenise` and native RISC OS export commands. A matching historical AAsm executable was not recovered or required for this probe. The prior working **AsAsm 2.01**, GCCSDK pin **`212d4567f007e7d30f4af3d6e1919a3d8a115b1c`**, is invoked as a native host tool. Its exact binary SHA-256 is recorded in the result JSON. Host build adaptations and tool licensing remain documented in [the prior experiment](../arm2-kernel/BUILD.md) and [licensing record](../arm2-kernel/LICENSING.md).

The previous Apache-licensed `tokenise` source pin `d6ea854482663935562dc4c1bc2cde4bf3b570aa` remains available for a restoration. It was **not run** during this probe: input closure failed before a complete kernel build. `TMOSHelp` generation must use this cohort's published `Tokens`/`HelpStrs`, not a binary extracted from a ROM. Neither a later BuildSys revision nor the 2008 global interface headers is an assembly input in this phase.

## Modifications

- **Recovered source modifications: none.** Every retained source file matches its Git blob; copies in the build/export tree are unchanged.
- Added only investigation scripts, reports, manifests, evidence snapshots and logs under `experiments/arm2-history`.
- Exported available headers into an isolated namespace, rejecting duplicate ownership. This convenience export collects available header files; it is not a recreated official product build.
- Supplied `MACHINE=A440`, `IMAGESIZE=2048K`, `HDR_PATH` and AsAsm flags. The image-size setting is a header selection, not an achieved ROM size.
- No guessed flags/workspace, stubbed functions, later-header fallback or architectural source patch was introduced. The failed output is removed.
- The prior experiment and toolchain were read/reused without modification. MacArch was not modified or tested. No ROM joining or desktop integration occurred.

## Reproduction

Run from the project root. Python 3, Git and the existing native AsAsm are required. Fetching uses public network access and caches beneath `/tmp`; that step may require the environment's network approval.

```sh
python3 experiments/arm2-history/scripts/fetch-history.py
python3 experiments/arm2-history/scripts/analyse-history.py
python3 experiments/arm2-history/scripts/probe-cohort.py
python3 experiments/arm2-history/scripts/collect-evidence.py
python3 experiments/arm2-history/scripts/verify.py
```

`fetch-history.py` retrieves all advertised branches/tags for Kernel/HdrSrc and mirrors the twelve related repositories. The recorded refs are the scope of this completed investigation; a future fetch may expose additional commits. `analyse-history.py` records lexical candidate/transition evidence. `probe-cohort.py` uses immutable source pins, so the cohort itself is stable even if advertised branches move. It intentionally records assembler failure as data and exits successfully after recording it; consult `artifacts/cohort-assembly-result.json` for the actual assembler return code. It does not turn an assembler abort into a pass.

The captured failed command is in the result JSON, together with its working directory and environment. Reproducing this probe should demonstrate missing historical inputs; it cannot produce a kernel without further restoration. The archive includes sources/evidence and scripts, not the large prior toolchain or temporary Git repositories. Restore/build the toolchain using the prior experiment if it is unavailable.

## Licensing and provenance

All thirteen cohort roots carry an **Apache License 2.0** text in the published Git trees. Original source notices and root licence files are retained unchanged; licence manifest records their hashes. Comparison snapshots also retain their component licence. These are facts about the published cleaned sources, not a claim that the original 1995/1996 releases were licensed under Apache at that time or that the recovered files equal original installation media.

Some individual files, such as `Version`, rely on the component's licence rather than repeating a notice. Do not strip component notices when sharing this evidence. New investigation scripts and reports are provided under the included Apache-2.0 licence; upstream copyrights remain with their respective holders.

The missing historical registration files are **not treated as legally recoverable merely because a later public version exists**. Their absence is recorded. A later restoration may use appropriate published definitions with their notices and a documented semantic review; it must not reconstruct excluded third-party allocations from proprietary material. No proprietary ROM code, ROM image, extracted resource or proprietary assembler was used.

This package contains no resulting executable kernel and makes no clearance claim for an eventual full ROM, desktop, third-party application payload, trademark or artwork. Those remain separate provenance and compatibility questions for the ultimate freely redistributable 3.11-compatible system.
