# RISC OS 3.11 compatibility checklist

The target remains existing, unmodified RISC OS 3.11 desktop applications and games on ARM2/ARM3 original Archimedes hardware. A restored 3.60 kernel/module cohort is an implementation baseline, not a substitute compatibility target.

The following table records the initial controlled filing gate. Later integrated
desktop coverage is listed below.

| Interface or behavior | Evidence in the initial filing milestone | Limit |
|---|---|---|
| OS_File 5 / 255 | Case-folded metadata and exact whole-file loads | Generated files only |
| OS_Find 0 / &40 / &80 / &C0 | Read/output/update handles and close; closed handle gives &DE | Controlled D/E fixtures only |
| OS_Args 0 / 2 / 3 / &FF | Pointer/extent, truncation, explicit flush and close persistence | No sparse growth or delayed-flush failure coverage |
| OS_GBPB 1 / 2 / 3 / 4 | Positioned/sequential reads and writes, transfer pointers/counts, read EOF and bounds | No interrupted-write or partial-error transfer coverage |
| OS_GBPB 9 | One-entry pagination, wildcard and nested directory enumeration | Two directory levels, D/E only |
| OS_BGet / OS_BPut | Read EOF and byte append persisted before truncation | Basic generated stream only |
| OS_File 0 / 4 / 6 / 8; OS_FSControl 25 | Save/overwrite, access change, delete, mkdir and rename; raw image verification | No directory exhaustion or full access-control matrix |
| Write error recovery | Read-only file &C1; write-protected disc &108C9; disc full &108C6 without image changes; later save succeeds | No write-time I/O faults, power loss or dirty-media removal |
| FileSwitch paths | Lowercase lookup, `@`, `^`, explicit ADFS drive 0 | No path variables or other filing systems |
| D/E disc layout | Real old/new maps, shared-object offsets and three noncontiguous extents | One-zone 800 KiB E fixture; not arbitrary E/F/L media |
| Read error recovery | Missing sector, ID/data CRC, directory/map damage; remount recovery | Synthetic controller faults; no physical-drive timing claim |
| Media change / removal | Baseline stale-data regression; patched IRQB4/latch reset behavior | Pinned original-A440 headless core with recorded patch; installed application not exercised here |
| ARM2 application entry | Original 280-byte client loaded by OS_CLI at &10000, USR26, real file SWIs, checksum and OS_Exit | Diagnostic source written for this project; not a third-party app compatibility claim |
| Desktop, games, sound, graphics modules | Not exercised | Still required for the ultimate target |

See the [controlled filing-write results](../filing-writes/RESULTS.md) for physical image checks and limitations. That original write SWI client runs from Supervisor. The later Edit gate below also exercises actual user-mode desktop saving.

Historical presence of an interface and passing these calls are evidence toward compatibility. They do not establish every 3.11 flag, error, timing or workspace contract. The original gates did not use a commercial reference ROM. The later [module audit](../system-audit/RESULTS.md) uses user-supplied 3.11 ROMModules screenshots as inventory evidence only; this is not a behavioural differential test.


## Integrated desktop coverage

| Behaviour | Current evidence | Limit |
| --- | --- | --- |
| Desktop, Wimp, fonts and mouse | Cold startup, window/navigation/input checks, real software FPA and pointer tests | Not the complete desktop API |
| Filer operations | Actual copy, Shift-drag move, Delete and protected-disc Abort; three cold runs each | Generated old-map floppies; not every recursive/error case |
| ST506 hard disk and Edit | Six cold machines: open hard drive, launch Edit from Apps, type/save, restart and double-click document; real editor buffer and on-disk bytes match | One 20 MB old-map ST506 image on emulated A440/1 ARM2; no physical hardware or IDE claim |
| SharedCLibrary | Public APCS-26 C client checks varargs, heap, sorting, arithmetic and jump recovery across 33 frames | Bounded ABI cases, not every library function |
| BBC BASIC | Actual original Edit Export helper runs and supplies its tokenisation entry points | Not an exhaustive interpreter/assembler compatibility suite |
| Zarch | Unmodified privately supplied floppy launched through Filer; game entry and paired keyboard/thrust/steering/fire/sound checks across three cold boots | Three-second gameplay samples; not a complete game playthrough |

See [the original Edit milestone](../desktop-apps/RESULTS.md) for current hashes,
reproduction, artifacts and remaining scope. TaskWindow,
printing, broader disk-error cases and real ARM2/ARM3 machines remain unverified.


The original [Draw and Paint applications](../graphics-apps/RESULTS.md) now pass
three native save/reopen trials each (12 cold machines): completed rectangle
DrawFiles and mode-12 sprites containing actual painted pixels. Independent
media parsing and the original app buffers agree exactly after cold reopening.
This is basic artwork/persistence coverage, not a claim for all object types,
editing operations, JPEG, printing, clipboard or full 3.11 compatibility.


## Expanded editing and standard-service audit

[Draw, Paint and Edit editing/interchange](../graphics-apps/EDITING.md) now covers
18 independent cold write/reopen machines: object grouping/scaling and outline
text, real sprite import, Paint transformations/masks, and Edit selection-copy,
undo/redo and find/replace. Saved bytes and on-disk allocation are independently
checked. Printing and every possible object/file operation remain unverified.

[SpriteUtils](../spriteutils/RESULTS.md) supplies real SLoad/SChoose and the other
sprite commands, with public pixel/file/error tests. Nevryon now reaches its
title screen from the unmodified private disc; gameplay is not yet certified.

[The standard-service audit](../system-audit/RESULTS.md) compares all 88 entries
in the user's 3.11 ROMModules screenshots with the actual ArcLibre image:
44 matching titles, 43 absent titles, and one partial Palette replacement.
The detailed matrix distinguishes real missing services, optional hardware,
networking and historical patch identities. Its command inventory includes the
kernel system table and separates configuration/help entries from handlers.
This establishes presence, not complete interface compatibility.

TaskWindow/FilterManager now pass the [bounded runtime gate](../task-services/RESULTS.md):
CPU-bound pre-emption, all eight software-FPA registers, messaging, suspend/resume,
kill/error cleanup, filter ordering/masking/claim/self-removal and original
Edit/BASIC integration. This raises matching module titles to 46 and reduces
absent titles to 41; it does not establish arbitrary program compatibility.

Next gates are device streams and additional filing systems, utilities/settings,
then real printing and hardware-specific support. The reported fast sound also
exposed a [VIDC1 sample-period defect](../sound/RATE_FIX.md), with new rate tests
against elapsed time rather than non-silence alone.
The [current roadmap](../desktop-source/ROADMAP.md) replaces older future-work
statements in the historical milestone reports.

The [classic submenu gate](../menu-messages/RESULTS.md) checks a real Wimp 2.00
client with independent &400C0 message numbering. Impression's six top-level
submenus now open in a private MCP replay; its full editing/printing behaviour
remains outside this bounded verification.
