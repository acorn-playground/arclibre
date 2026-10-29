# Boot experiment results

## Outcome

The restored kernel executes from the genuine reset vector and reaches **`ModuleInit=&0380419C`**, stopped before its first instruction. The binary is unchanged from the successful restoration milestone. No emulator modification was necessary.

MacArch was configured as **A440/1, ARM2, 4 MiB RAM, standard monitor, no mounted discs, no hard-disc images**, with Delete held at cold power-on to initialise CMOS. The external repeat harness uses the unchanged core at Git revision `550bee4842e45eafdf331f0d06e11df1368403e8`. The MCP server started without a ROM and was explicitly given this experimental image; no proprietary ROM was loaded or read.

| Requirement | Measured result |
|---|---|
| Actual reset-vector execution | At instruction count 0: PC=0, PSR=`0C000003` (SVC26, IRQ/FIQ masked). One `LDR pc,[pc,#&110]` loads the word at `&118`, reaching `CONT=&0380DCDC` at instruction count 1. |
| MEMC and RAM discovery | Real InitMEMC writes `&036E010C`. MemSize returns R0=`8000`, R1=`400000`, R2=`036E010C`: 32 KiB pages and 4 MiB RAM. Timer-based CPU measurement records `MemorySpeed=&11F40`, comprising the source's MEMC1a flag and 8000 kHz. |
| Fixed workspace mappings | Logical `0`, `01C00000`, `01F00000` map to physical RAM offsets `80000`, `88000`, `78000` respectively. An independent reconstruction checks all 8,192 emulator page descriptors against the captured CAM addresses and ordering. |
| Stack installation | IRQ SP=`01F0136C`; SVC stack remains within `01C00000–01C02000`, ending at `01C01FF8` at the pre-module boundary. |
| Vectors and copied code | Processor pointer table/pre-veneers, 116-byte SWI dispatch, 752-byte IRQ block and SWI return branch match their ROM source bytes exactly. Seven live vectors contain `E59FFF88`; the original three-word unclaimed FIQ path follows. |
| Exceptions during boot | 164 real SWIs and 50 IRQs; zero undefined, prefetch-abort, data-abort, address-exception or FIQ entries. SVC26 remains the checkpoint mode. The FIQ and abort handlers are installed but have not been deliberately exercised. |
| Pre-module boundary | PC=`0380419C`, instruction count **15,369,106**, clock **183,078,399 master ticks**, or **7.628266625 emulated seconds**. Module_List and ROMModuleChain are still zero. ModuleInit's first instruction has not executed. |
| Repeated cold resets | Three newly constructed machines produce identical checkpoint registers, hardware summaries and exported device/memory state. The independent harness's full uncompressed final snapshot also equals the MCP-driven snapshot. |
| Reset button | An additional MCP `press_reset` run re-enters through the reset vector, restores workspace/exception setup and reaches the same pre-module PC without fault breakpoints firing. This is the emulator's physical reset action, not a certified keyboard/software Break path. |

The boot verification, repeatability report and MCP/harness parity contain the measured assertions. The exception counter's initial reset value is 2 because the core initialises/resets the CPU during machine construction and power-on; it is not two executed reset-vector instructions. The trace and instruction counters prove the single observed vector instruction.

## Encountered dependency and failures

There was **one unavailable module SWI**: `XColourTrans_InvalidateCache` (`&60750`, base number `&40750`), issued at `&0381A830`. The real unknown-SWI/error path sets V, returns, and the existing VDU mode initialisation proceeds. This is an optional cache-invalidation notification before ColourTrans exists, not an implemented ColourTrans service and not a dummy success handler. Its caller and error-return trace are retained. No other unavailable SWI was observed before the stopping point.

There were no observed kernel or ROM integration faults requiring a source patch. Host harness construction initially encountered an unwritable default compiler cache and an Xcode-build-system dSYM operation denied by the execution sandbox. The final recipe places caches under `/tmp` and uses SwiftPM's native build system. Those are host build adaptations only. An existing core warning in floppy-image format detection is recorded; no floppy image is loaded in this experiment and the emulator source remains unchanged.

The MCP debugger's 1,000-entry log cannot retain the whole boot by itself. The external harness uses the existing public debugger API, drains it after at most 500 instructions and checks for loss. Its largest drain contains **75 entries**. All **1,916,545 hardware writes** are captured and independently decoded; most are IOC timer-latch operations during CMOS/I²C delays. No MCP extension was required.

## Remaining issues

1. **No runtime modules have been initialised.** This component contains the kernel's built-in Utility module and the original chain terminator, but no external module implementations. Full OS startup, filing systems, message/territory services, sound modules and command-shell completion are untested. The next phase must identify and supply genuine required modules, not treat assembler closure as runtime coverage.
2. **No desktop/application/game compatibility result exists.** The source retains its 3.60 identity. RISC OS 3.11 SWI, OS_Byte/OS_Word, module, VDU, palette, font, timing and memory-management contracts remain the acceptance target.
3. **Exception installation is stronger than exception coverage.** Ordinary boot exercised SWI and IRQ entry/return. FIQ, deliberate faults, nested interrupts and application callbacks still need execution fixtures; no claim is made that installed handlers alone prove those behaviours.
4. **Emulation is not physical-hardware validation.** Real MEMC/IOC/VIDC timing, DMA, keyboard electrical behaviour and ARM3 operation remain separate tests. This run used ARM2 only.
5. **Trace scope is explicit.** Every hardware write is retained for one fresh cold boot; the other two repeat its counts and full state. Instruction traces are rolling windows around checkpoints, plus all SWI events, not a complete transcript of all 15 million instructions. The initial interactive MCP hardware ring overflowed normally; the subsequent complete capture demonstrably did not.
6. **Software Break is not certified.** The additional reset-button run passed, but a keyboard/software Break path through the RAM reset indirection has not been tested as such.

The recommended next phase is [bounded kernel runtime/exception validation followed by genuine minimal-module closure](NEXT_PHASE.md). Do not begin desktop integration yet.
