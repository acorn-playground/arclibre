# Independent static verification

The combined acceptance report passes. “Independent” here means an independently implemented AOF parser, ARM2 decoder and bounded instruction interpreter, not a second assembler or a separate human certification. They do not use AsAsm's encoder/disassembler or MacArch code. Source/symbol observations still come from AsAsm and are cross-checked against its ordinary object bytes and mapping symbols.

## Instruction and code/data gates

inspect_image.py reads the ordinary absolute AOF directly. It rejects imports, relocations, Thumb and 32-bit APCS area attributes. It compares the ordinary object with the observed build byte-for-byte, and every observed emitted byte with the object. The instruction-emission set must agree with the ordinary object's `$a`/`$d` mappings.

Two explicit classifications require explanation: the IRQ branch emitted with DCD is real executable code; one zero word aligned after `VduGoVec` lies in a code mapping and is conservatively decoded as ARM2 `ANDEQ r0,r0,r0` padding. Video expansion constants such as `P1BTab` remain data, even when their bit patterns resemble instructions. The complete range map, decoded listing, emission trace and symbol observations expose those decisions.

All **27,751** identified instruction words, including the branch and padding, pass the independent decoder. It rejects post-ARM2 encodings, invalid multiply aliases, PC byte transfers/writeback and coprocessor instructions. Deliberate MRS, MSR, SWP, BX, BLX, halfword, long-multiply, CLZ and register-restriction failures prove the rejection gate works. This matters because AsAsm's CPU selection alone can leave unsuitable instructions as warnings.

There are **5,040** direct B/BL targets, all landing in identified code after modulo-26-bit arithmetic and the eight copied/template runtime mappings. The indirect-control-flow inventory retains the remaining PC-writing sites for later runtime review. This inventory is not a claim that every indirect target has been proven.

## Processor and exception review

The selected mode values are USR/FIQ/IRQ/SVC = 0/1/2/3, with flags and interrupt masks in PC/PSR. ARM2's bank-selection restriction after PSR-changing test instructions is addressed with a flag/register-preserving settling instruction; user-bank loads receive the same conservative treatment. The independent check covers **198 emitted settling sites** and one documented same-SVC dispatcher exception. ARM2's banked-register caveats and return conventions are described in the original [assembler application note](https://www.riscos.com/support/developers/prm/asmappnote.html) and [instruction reference](https://www.riscos.com/support/developers/asm/instrset.html).

| Path | Reviewed resident flow and boundary |
|---|---|
| Cold reset / Break | Reset alias loads through `&118`; physical `CONT` calls the selected MEMC1 InitMEMC, real RAM sizing, VIDC and IOC setup. The RAM reset word is changed to CONT_Break by the original reset code. The existing non-POST path avoids the incompatible external test monitor; reset itself is not skipped. |
| IRQ during reset | RAM vector `&18` branches to IRQ_Test_CTRL_or_R_Pressed using a verified 26-bit wrapped displacement. The A1 keyboard/reset handler remains selected. |
| Normal IRQ | The installed vector loads ProcVec_IRQ, whose default is Initial_IRQ_Code; the real default dispatch block is copied into its unchanged 752-byte RAM allocation. Source retains saved PC/PSR and IRQ return conventions. |
| Unclaimed FIQ | Exactly three words load IOC, clear the FIQ mask, then `SUBS pc,lr,#4`. A subsequently claimed FIQ routine is external client code and not certified here. |
| SWI / return | The 116-byte relocated dispatcher, SWI table and dirty return branch retain their fixed addresses. The normal return uses saved LR with `MOVS pc,lr`; callback and error paths retain their real handlers. The dispatcher PSR instruction forces SVC from an already-SVC SWI entry, so it does not switch register banks. |
| Undefined / prefetch / data / address exception | Vector pointers lead to the four RAM pre-veneers, then environment slots. The default handler table resolves to UNDEF, ABORTP, ABORTD and ADDREX. They mask interrupts, preserve/dump registers through DumpyTheRegisters, flatten the SVC stack through UNDEF1 and retain the real error-generation path. They are fatal/default error paths, not invented retry handlers. |
| Callback | `callback_checking` tests the saved return mode/mask and postponement rules. `Do_CallBack` retains the real callback-chain and old-style paths, saves user registers and uses the existing CallAd/CallBf contract. Default NOCALL and resident entry instructions are checked; installed client callbacks remain outside this component. |
| Branch through zero | Original RESET1 register-dump/error flow remains. Both instruction templates copied to address zero are decoded using that destination. |

The machine-readable exception routes, PSR sequences and checkpoint symbols tie this review to the emitted image. All resident code is checked, a superset of its reachable instruction encodings. Arbitrary client-supplied vector targets, hardware fault timing and full control/data-flow correctness require later execution; no formal whole-kernel reachability proof is claimed.

## Bounded emitted-code tests

routine_checks.py interprets actual object instructions using a small fail-closed ARM subset. It is a test fixture, not a new emulator or a ROM boot:

- 10,240 BangCam cases: 128 physical pages × 4 page sizes × 5 logical addresses × 4 protections.
- One BangCamUpdate case verifies the packed four-byte soft CAM entry and the hardware write.
- Twelve AddCamEntries cases verify page-zero, heap and cursor entries at each page size.
- OS_ReadSysInfo reasons 2/3/4/5 reach the real shared SWI return boundary with the expected unavailable-hardware results, without writes or accesses to absent device addresses.

The fixture stops at genuine routine boundaries. It does not substitute handlers or claim to run the complete SWI exit, reset or interrupt subsystem. Detailed results are in routine-checks.json.

## RISC OS 3.11-facing contract

| Area | This milestone's evidence | Remaining 3.11 requirement |
|---|---|---|
| CPU and exceptions | ARM2-only emitted encoding, 26-bit modes and PC/PSR returns | Nested IRQ, exception and callback execution under application workloads |
| Module/SWI ABI | Public allocation constants, original module tables and fixed dispatcher retained | Real 3.11 module entry/register/error semantics and runtime provider coverage |
| OS_Byte / OS_Word / vectors | Existing implementations retained; interface references pinned | Behavioural regression cases, including undocumented game assumptions |
| Application slots / dynamic areas | Original MEMC1 CAM packing and workspace; no ARM600 manager | Slot resizing, moving memory, protection, application launch/exit and heap stress |
| VDU / palette / pointer / font | Original VIDC1a selection and publicly licensed source font | Pixel, mode, palette, cursor and glyph comparisons with 3.11 specifications/test expectations |
| Sound / keyboard / timers | Original 8-bit sound/IOC/A1 keyboard configuration; instruction checks | Latency, DMA, keyboard/mouse protocol and game timing tests |
| Identity queries | Honest unavailable-hardware result; no invented machine ID | Confirm applications tolerate the original-board values; do not add later-machine capabilities |
| CMOS / messages / version | Explicit public definitions and real error paths; source version retained | 3.11 defaults, error contracts and version-sensitive software; no false “3.11” banner |
| Desktop and utilities | No integration undertaken | Separately licensed original-compatible desktop/services/assets and regression suite |

The existing project [compatibility test plan](evidence/COMPATIBILITY_TEST_PLAN.md) remains the broader acceptance framework. Restoring the 3.60 kernel is a means of obtaining lawful, testable original-machine code, not evidence that later RISC OS behaviour can replace the 3.11 target.
