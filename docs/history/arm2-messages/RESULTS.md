# MessageTrans and resources results

## Outcome and scope

The experimental ROM boots to the genuine Supervisor prompt and prints complete `*Help` output, including all four special keywords, then returns to input. MessageTrans also expands parameterised errors correctly. Three independent cold boots produce identical keyboard/Help evidence, and three client suites verify the real resource and translation interfaces.

The 145,152-byte keyboard milestone kernel remains byte-identical as an input. Its source and executable code are unchanged. Packaging replaces its final four-byte module-chain terminator at ROM offset `&236FC` with the first added module's length, appends four actual modules, and writes a new zero terminator. The 2 MiB container uses 236,964 bytes. `artifacts/rom-layout.json` records every module address, length and hash.

## Pinned sources and dependencies

All four runtime additions use the matching **Import from cleaned 360 CD** sources:

| Component | Commit |
|---|---|
| FileSwitch | `93c7e2e094c314940237f6256e77edae2486419b` |
| ResourceFS | `fce5556d0ea1b7456b9c534038a3e437293ef90c` |
| MessageTrans | `2a006cd1d002bda2d7454764fe4b93f734f17598` |
| Messages/resource registration module | `210c2af5b84654d9fa7e7ab179ef18834852f3e4` |
| Kernel UK messages | `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc` |
| Squash header only | `a21ce91e3d0a1a8c04f3e0dd72683a6d7fa2ab76` |

The Squash interface is required to assemble the genuine compressed-file path; no Squash module or compressed resources are included. The previously approved public allocation-header revision `403c6dd8bce92d0629634cbf57f68f43b2f30d38` supplies the missing `Messages` and `FileTypes` declarations. This is an explicit public-interface recovery, not a replacement runtime cohort. Original files and hashes are in `manifests/source-files.json`; repository URLs and pins are in `manifests/cohort.json`.

MessageTrans opens its message files using OS_Find, OS_FSControl and OS_Args. Thus FileSwitch and ResourceFS are genuine dependencies. The Messages module registers the resources through ResourceFS_RegisterFiles and its original service entry; no success stub or direct guest-memory resource injection is used for startup.

The container order after UtilityModule is FileSwitch, ResourceFS, MessageTrans, Messages. The unchanged kernel early-initialises the first module after UtilityModule via its generic OS_Module AddArea path, historically intended for Podule. Here that module is FileSwitch. The real module chain, registrations and service callbacks complete successfully. Early FileSwitch/ResourceFS attempts to open messages precede MessageTrans; their original failure-tolerant paths and later resource notifications recover. The steady-state Help test has no missing MessageTrans calls.

## Reviewable modifications

**Patch 16 — assembler dialect.** Rename ENTRY macro uses consistently with the existing restored shared headers; replace unsupported LEADR with a zero-origin, position-independent module assembly; express literal backslash characters numerically; prevent comment backslashes from swallowing the next line; replace the RISC OS environment-variable include path with the generated local resource filename. The LowFSI and FileSwitch control-block fields now retain their original intended offsets: get = 12 and GBPB = 40, with FS header size 48. Assertions verify these values independently.

**Patch 17 — ARM2 settling.** Add conservative flag/register-preserving `MOV r0,r0` delays after PSR changes and user-bank loads in the new modules and their isolated shared-header copy. The independent audit checks all 64 emitted sites. No changes are made to the preceding kernel's header tree or artifact.

**Patch 18 — ResourceFS registration.** Use the published full `ResourceFSSWI_Base = &41B40`. The old expression added the system base to an allocation index that already included it, advertising `&81B40` while callers used `&41B40`. The first trial consequently failed resource registration and printed `TokNFnd`. The exact failed ROM (`009369df…`) and its diagnostic snapshot are retained as `initial-resourcefs-base-failure.rom` and `first-modules.macarch-state`; they are investigation artifacts, not the successful image. The final ROM registers at the correct base and complete Help works.

Every patch replays without fuzz. There are no fabricated workspaces, replacement runtime implementations or emulator changes.

## Resource contract

The host resource packer follows the public `Messages/Utils/c/ScanRes` and ResourceFS structure: next-record offset, load address, execute address, byte length, attributes, terminated/aligned filename, length-plus-four word, original file bytes and alignment padding. All resources use deterministic text-file metadata (`load=&FFFFFF00`, execute/timestamp zero, attributes 3); ResourceFS itself is read-only. No metadata or data is extracted from ROM images.

The seven files are:

- `Resources.MsgTrans.Messages`
- `Resources.FileSwitch.Messages`
- `Resources.ResourceFS.Messages`
- `Resources.Kernel.Messages`
- `Resources.Global.Messages`
- `Resources.Kernel.Dictionary`
- `Resources.Help.Messages`

Their bodies are copied byte-for-byte from the pinned public sources. The supplied dictionary and help tokens are retained with their matching cohort; no new dictionary entries or token indices are invented. No squash compression or retokenisation is needed for this bounded payload. The Messages module embeds the pack and supplies its original terminating zero record.

## Validation

| Gate | Result |
|---|---|
| Assembly | Two normal plus one observer assembly per module yield identical objects; zero unresolved symbols or relocations |
| Independent ARM2 decoding | 12,584 new instructions, 2,934 direct branch targets and 64 settling sites pass |
| Kernel preservation | Exact kernel artifact/source unchanged; earlier static and emitted-routine evidence remains valid and checksum-verified |
| Public workspace | Module constants agree with the actual kernel for stacks, heap, scratch space, domain ID, IRQ semaphore and dispatch tables |
| Real cold reset | Three runs pass ARM2/26-bit state, 4 MiB RAM detection, MEMC/CAM mappings, stack/vector setup and pre-module boundary |
| Boot hardware | All 1,916,550 writes from the first pre-module run independently decoded |
| Natural continuation | All five actual modules present; FSCV points into FileSwitch rather than the default kernel vector |
| CAM and dynamic areas | Three retained real heap/RMA fixture suites pass, including partial-shrink errors and preserved page content |
| Keyboard and Help | Three identical suites pass all prior typing/editing/modifier/Escape/repeat checks, plus complete Help text |
| MessageTrans client | 37 real client calls per run: 35 MessageTrans calls plus genuine RMA claim/free; all three runs agree |
| Resource reads | All seven FileInfo/OpenFile results point at the expected ROM data and match every source byte |
| Translation | Plain lookup, `%0` substitution, dictionary expansion and direct Dictionary access pass |
| Errors | ErrorLookup preserves `&12345678` and returns `SWI &DEADBEEF not known` with V set; a missing token returns `Message token NeverDefinedToken not found` |
| Lifetime | Close/reopen repeated successfully with a valid client block and filename in real RMA |
| Text regression | Original 1,792-byte soft font, 95 glyphs and two 163,840-pixel comparisons pass |
| Exceptions | No undefined, prefetch/data abort, address or FIQ exceptions in the tested paths |

The keyboard suite uses actual key-down/up events with no guest PC or RAM injection. The separate MessageTrans client fixture places a small ARM2 program in test-owned application RAM and calls genuine SWIs; descriptor/name storage is allocated in RMA through OS_Module as the API requires. It does not install or replace handlers. This distinction is recorded in its source.

`artifacts/keyboard-{1,2,3}/` contains key/character/hardware-access logs, workspace states, complete snapshots and screenshots. `artifacts/messages-{1,2,3}/` contains all client input/output registers and flags, SWI and instruction traces, actual returned resource bytes, expanded Help and raw machine state. `verify_messages.py` independently checks resource addresses/content, results and repeatability. `artifacts/module-audit.json` and per-module instruction/symbol files record static results. AsAsm's BIN directive leaves the preceding code mapping active; the auditor explicitly classifies only the original Messages resource range as data after byte-checking it against the pack.

## Remaining issues and next milestone

Territory_UpperCaseTable (&43058) and Territory_LowerCaseTable (&43057) remain absent. The original modules tolerate this for the tested exact resource names, but case-insensitive filename matching, locale character classification and broader filing behavior have not been established. Podule, ColourTrans, sound services and Portable also remain absent. Escape still attempts Sound_QInit; the first idle wait still probes Portable_Speed. These are recorded, not disguised by handlers.

FileSwitch and read-only ResourceFS are present; disc filing systems, persistence, BASIC and the desktop are not. Compressed resource loading is untested and has no Squash provider. No Break/reset, mouse, ARM3, physical-machine or application/game compatibility claims are made. The previous negative CAM control is retained as immutable evidence rather than rerun as this payload.

The recommended next milestone is the matching public **TerritoryManager and UK territory implementation**, with case-conversion/character-property and mixed-case ResourceFS tests. That closes the observed text/filing dependency before adding disc services or a language runtime. Preserve the current full Help/error and all earlier regressions. This remains preparation for unmodified **RISC OS 3.11** desktop applications, games and utilities; the restored 3.60 identity does not establish their compatibility.

## Licensing and preservation

The pinned module sources, UK resources, dictionary, headers and tools' source notices carry the public Apache-2.0 licensing recorded in their original LICENSE files. New source changes, packer and harness source are Apache-2.0. Squash contributes only a public header; it contributes no blob or compressed binary implementation. No proprietary ROM code/resources were used. Historical source snapshots may contain upstream build utilities, but no prebuilt upstream executable is used by this build; resource packaging is performed by the supplied Python code.

AsAsm remains a host build dependency. MacArch core at `550bee4842e45eafdf331f0d06e11df1368403e8` is an unchanged GPL-covered host test dependency; its license and source-hash provenance are retained. No emulator executable is packaged or linked into the ROM. The user's pre-existing app UI edits remain untouched. Checksums verify all 4,302 manifest-listed files from the five preceding milestones. No MCP extension was necessary.
