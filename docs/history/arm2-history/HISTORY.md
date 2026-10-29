# Historical dependency findings

All dates below are recorded Git/CVS-import dates. “First visible” means the first corresponding code in the inspected reachable history, not necessarily its original authoring or public-release date. Full pins and patches are retained locally.

## Timeline

| Dependency or loss of coherence | First visible evidence | Integration / meaning |
|---|---|---|
| ARM600 memory-management selection alongside old MEMC paths | Kernel `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc`, 1996-11-05, cleaned 3.60 import | Already in the earliest substantial import. Conditional ARM600 support itself is not a defect; inappropriate references in the original-machine selection are. |
| System-heap setup uses `PageFlags_Unavailable`; query code uses `RawMachineID` | Same 3.60 import | Both are already incompatible with the selected MEMC1/NewSpace configuration. No earlier kernel implementation is available in these refs to date the original changes. |
| AMB included; hard reset calls `AMBControl_Init` and `L1L2PTenhancements` | StrongARM/3.70 import `fd98e2a10aa9986fc7baaa5375bc4f53a231d49d`, 1996-11-06 | Merged trunk `10073caf45e22ddb3fd3a637762a9e78ddb0bc31`, 1997-01-21. Import patch, merge patch. |
| Reset writes `ResetType`, absent in old workspace | SrcFiler import `c3d9625b85fa7e073e3d4a6e2e7593c470dfe23d`, 1996-11-21 | Also present in NCOS import `d8f0c84eaccd6dec66c31ab550665331a14c7fa6`, then January 1997 trunk merge. Patch. |
| Original A440 machine header removed from main HdrSrc line | `a6e338ef2fdb7ab1ec0d0cd507e90244ab1bb04f`, 1996-12-17 | Old header survives in earlier branches; deletion is not destruction of its history. Commit. |
| IOMD part-ID query, `OS_ReadSysInfo 8` | Ursula `b2c0554784089095310b7a0b92ffc94f96b4d804`, 1998-09-24 | First patch adds reason 8 and the IOMD table. Later Ursula_RiscPC changes and trunk `b85d7d81d8d76e95440b6db1c39399eaa6a8945b`, 2000-02-02, reproduce it. Branch patch, trunk patch. |
| Published registration-header history begins | HdrSrc `403c6dd8bce92d0629634cbf57f68f43b2f30d38`, 2008-03-21 | Public cleaned imports of SWIs/CMOS/errors/services and related exports; historical versions are not present. Commit. |
| Published BuildSys history begins | `2102c23e711b48e507481bace0d81a4ef0a845dd`, 2008-10-14 | Clean reimport of build environment; no recovered matching 1995/1996 product build lock. Commit. |

There are no finer-grained commits for the original ARM600/page-flag/RawMachineID introduction before the 3.60 import. Workspace comments mention RawMachineID in December 1993 and AMB comments describe earlier development, but comments are not exact integration dates. Reporting an exact earlier date would overstate the evidence.

## Why the 3.60 import is not coherent for A440

The recovered Version calls itself 3.60, dated 13 April 1995. The import date is 5 November 1996. Neither date makes this a RISC OS 3.11 source release.

The original A440 header explicitly includes A440/1 and selects ARM2, IOC-A1, MEMC1a, MEMC1, VIDC1a, WD1772 and the A1 keyboard. GetAll selects `Old/NewSpace` for this memory manager and makes `NewCDA`, `ExpandedCamMap` and `UseFreePool` false.

Nevertheless, NewReset:1461 sets `r1` to `AP_SysHeap :OR: PageFlags_Unavailable`. The sole flag definition is ChangeDyn:1732, inside ` NewCDA`. It is therefore unavailable on MEMC1. This is more precise than calling it simply a missing workspace member: it is a **conditional definition/use mismatch**. The MEMC1 branch of `AddCamEntries` at NewReset:91 ignores the incoming access-flags value and constructs the original packed CAM entry itself. A narrowly justified conditional correction looks plausible, but must be reviewed against the memory/protection contract rather than defining the unavailable flag as zero globally.

[Middle:1161 unconditionally loads `RawMachineID` for `ReadSysInfo_Code` reason 2; reasons 4/5 also use it. The original NewSpace has no such allocation. The newer `KernelWS` and `Old/VickySpace` do, but importing their offsets is not safe: they describe a different workspace layout. Neither a later header constant nor a guessed new allocation restores an established ABI.

The source still includes later-machine test-monitor paths and has an incomplete feature profile for A440. These are additional restoration concerns; the two independent mismatches above already disqualify the untouched configuration.

## Branch candidates checked

| Candidate | Companion evidence | Finding |
|---|---|---|
| Black / cleaned 3.60 `3da129d…` | HdrSrc `c9113ab…` and eleven module imports with the same cleaned-360 provenance | Best minimal restoration base. No AMB/L1L2 call, but existing flag/workspace mismatches and missing global headers. |
| Spin_xx / SrcFiler `c3d9625…` | HdrSrc Spin_xx `effbc507f1ffb9bd9e4599c7131730621770590b` retains A440 | Still the same old workspace; adds ResetType references. Historical globals still absent. |
| Spinner / NCOS through `44a58444350577240f5bee8beb5a00406e9ebad9` (1998-11-06) | HdrSrc Spinner `41701aee1a375de3d317686fa4dba3e863c9969f` has Falcon/Morris/Omega/Peregrine machine headers, no A440 | Later AMB-free branch, not a recovered original-machine product. Same page-flag/RawMachineID mismatches and old workspace. |
| StrongARM / cleaned 3.70 and merged trunk | `fd98e2a…`, `10073ca…` | Adds AMB/page-table assumptions; does not repair original workspace. |
| March 2000 candidate `24044755…` | Prior experiment | Includes the later assumptions plus IOMD query; failed architecture closure already documented. |
| Other advertised branches and later descendants | Full history matrix and refs | No alternate `Old/NewSpace` content was found. Later snapshots cannot be promoted to A440 candidates merely because old files remain in their trees. |

The single old-workspace blob is `50f3233530f782e3cb8e78f3d8a3befe7493c868`. Matrix, summary and path history support this observation. Three revisions retain the selection text while lacking the old workspace file; those are not usable configurations.

## Publication and history caveats

The parent of the 3.60 kernel import, `53da419a39cfe088ca200b71658997fad3175020`, contains a cleaned `hdr/RISCOS`, not an earlier buildable kernel. Its message explicitly records a real commit date of **28 March 2008**, despite the backdated Git timestamp. See root evidence. The “matching cohort” is therefore the matching **published cleaned import cohort**, not authenticated byte-for-byte original 1995 build media.

Several `cvs2git` commits manufacture branches or track vendor snapshots. Their apparent additions/deletions of AMB are not independent engineering introductions. Transition records retain them; the timeline above uses the substantive imports/patches and distinguishes first branch appearance from trunk integration.

The cleaned public HdrSrc import explicitly excludes earlier registration history. The nine absent exports have individual addition histories under `evidence/header-*-history.txt`; `Register` and `s/DoSWIs` have no commits in the inspected history. A 2008 header may provide a usable constant for a deliberate restoration after review, but it cannot serve as proof that a complete matching 1996 header set was recovered.
