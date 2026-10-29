# A440/1 memory and workspace contract

The selected public `Machine/A440` header explicitly covers A440/1. The checked configuration is ARM2, IOC-A1, VIDC1a, MEMC1a hardware with the MEMC1 memory-manager implementation, WD1772 (`FDC1772`) and the original A1A500 keyboard. NewCDA, ExpandedCamMap, MorrisSupport, Dallas ID and IOEB are false. No AMB, ARM600 page-table or RawMachineID layout is selected.

The original Old/NewSpace is **byte-for-byte unchanged**. The assembled values and copy regions are in workspace-contract.json. All addresses below are hexadecimal, with exclusive interval ends.

## Hardware map and processor modes

| Address / value | Contract |
|---|---|
| `03800000` | ROM read base and MEMC CAM programming write space |
| `02000000` | Physical RAM base |
| `03200000` | IOC |
| `03400000` | VIDC |
| `03600000` | MEMC control/address registers |
| `0, 1, 2, 3` | USR, FIQ, IRQ and SVC 26-bit modes |
| `08000000`, `04000000` | IRQ and FIQ mask bits in combined PC/PSR |

ARM2 instruction addresses wrap within 26 bits. Exception return state remains in PC/LR; no CPSR/SPSR, ARM600 translation table or 32-bit exception-mode design has been imported.

## Fixed regions

| Range / address | Purpose and checks |
|---|---|
| `00000000–00000028` | Copied processor vectors plus the three-word unclaimed FIQ handler |
| `00000118` | Reset indirection word; ROM alias and RAM copy distinguish cold reset from Break |
| `00000164–00000564` | Initial packed CAM table, 256 four-byte entries |
| `00000564` | CamEntriesPointer; indirection is retained for original large-memory arrangements |
| `00000C28` | Page_Size word |
| `00000C34–00000F24` | DefaultIRQ1V, exactly 752 bytes; ends at CallBack_Vector |
| `00000F64–00000F6C` | Existing eight-byte UniqueMachineID; zero means unavailable on this board |
| `00000F90–00000FAC` | Processor-vector pointer table |
| `00000FAC–00000FBC` | Four processor pre-veneers; ends before the legacy tool words at `FEC` |
| `00001000–00004000` | VDU workspace, size `3000` |
| `00004000–00008000` | Scratch workspace, size `4000`; application workspace starts at `8000` |
| `01C00000–01C08000` | Initial 32 KiB system-heap chunk; SVC stack top `01C02000` |
| `01F00000–01F08000` | Cursor/system chunk, with original subdivisions and protections |
| `01F0136C` | Original IRQ stack top |
| `01F03388–01F033FC` | SWI dispatcher/return block, exactly 116 bytes |
| `01F033FC–01F037FC` | 256-entry, 1,024-byte SWI table |
| `01F037FC` | Relocated branch to the SWI exit path |

`TopOfPageZero=&200` is a **local scratch-overlay offset**, not the extent of the low 32 KiB workspace. It must not be used to claim that the later workspace members overlap application memory.

The full original workspace contains deliberate aliases/overlays. The verification checks the unchanged source plus critical interval boundaries and fixed copy sizes; it does not claim that every overlapping symbol is an error or that a new complete allocator layout was derived.

## MEMC packed CAM

The selected `BangCamUpdate` stores one word per physical page: logical address plus protection in bits 28–29. `AddCamEntries` retains the original non-expanded representation. For page-zero and the heap it stores PPL 0; the cursor chunk stores PPL 1. The stale `PageFlags_Unavailable` argument belongs to the unselected NewCDA path and is now conditional. No eight-byte ARM600 entry or fabricated per-page flags were added.

`BangCam` converts the physical page number according to the 4/8/16/32 KiB page-size permutation, splits the logical address into the MEMC address fields and writes the actual CAM programming address. The independent emitted-code fixture covers all 128 MEMC1 physical pages, all four page sizes, five logical addresses and four PPL values. The expected values use direct bit placement rather than the kernel's lookup tables. This checks programming encodings; physical protection enforcement is a hardware/boot-test obligation.

For the intended **4 MiB A440/1**, the original reset path uses 32 KiB pages. Its fixed physical mappings are:

| Logical interval | Physical interval | Initial protection |
|---|---|---|
| `00000000–00008000` | `02080000–02088000` | PPL 0 |
| `01C00000–01C08000` | `02088000–02090000` | PPL 0 |
| `01F00000–01F08000` | `02078000–02080000` | PPL 1, original user-write-protected chunk |

These intervals are distinct. The source also retains its genuine 512 KiB special-case mapping; the 4 MiB table is not substituted into that logic. RAM sizing, later dynamic remapping and allocation ownership still require runtime validation.

## Copies and exceptional control flow

Eight runtime regions are identified in runtime-regions.json: processor vectors, pre-veneers, SWI dispatch, SWI exit branch, two zero-vector templates, normal IRQ vector template and default IRQ dispatch. The independent decoder evaluates PC-relative branches at their **execution destination**, not merely their location in the ROM object. The relocation patch for the early IRQ vector is checked using the decoded signed displacement from RAM `&18`.

Adding settling instructions must not enlarge the fixed SWI or IRQ allocations. Both sizes are asserted from final symbols. The one SWI-dispatch PSR write is exempt from an extra settling instruction because its preceding `ORR r10,lr,#3` retains SVC mode after SWI entry; no bank change occurs there.
