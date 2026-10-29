# Boot evidence and interpretation

## Independent comparisons

verify_boot.py parses the captured diagnostic MEMC sections independently of the emulator. For each of three cold boots, at fixed-mapping, vector-installation and pre-module checkpoints, it reconstructs the entire logical page table from raw CAM programming addresses and write ordering. It compares all **8,192 descriptors per checkpoint**, the fixed 32 KiB mappings and the original packed software CAM. This is stronger than comparing a few zero-filled memory windows that could conceal aliasing.

At both vector-installation and pre-module checkpoints it compares the actual RAM bytes against the pinned ROM for:

- DefaultIRQ1V: 752 bytes at `&C34`.
- SWI dispatcher/return block: 116 bytes at `&01F03388`.
- Processor-vector pointers and pre-veneers: 44 bytes at `&F90`.
- SWI exit branch at `&01F037FC`.

It additionally checks all seven installed processor-vector words, the three-word unclaimed FIQ handler, RAM reset indirection, Page_Size, RAMLIMIT, MemorySpeed, CAM pointer, zero/unavailable machine identity, empty pre-module lists and final MEMC/video state. All checks pass. Original application and fixed workspace offsets remain unchanged; no workspace was invented for the experiment.

The hardware decoder reconstructs every selected store's address, width and value from its instruction word and debugger register capture. MacArch calls its data-access hook before the store/writeback, with PC already at instruction address +4; the decoder accounts for that. All **1,916,545** events decode as genuine STR/STRB writes in hardware address space. There are no unexplained stores or dropped log events.

| Hardware range | Writes |
|---|---:|
| IOC and I/O | 1,916,175 |
| VIDC | 94 |
| MEMC control/DMA | 20 |
| CAM programming | 256 |

Of the I/O writes, **1,791,770** latch timer 0 at `&0320004C`, and **124,314** write IOC control at `&03200000`. These account for the large CMOS/I²C delay trace. The first MEMC control write is `&036E010C`; the final workspace copy is `&036E058C`, with video DMA enabled and sound DMA disabled. Timer 0's programmed latch is 19999. Final VIDC reports 4 bpp, a 16 MHz pixel clock and a 640×256 display interval; this establishes actual programmed state, not visual or RISC OS 3.11 fidelity.

## Trace inventory

| Artifact | Contents |
|---|---|
| Numbered MCP records | Every experiment MCP call and its text response: reset, stepping, registers, memory inspection, failure/dependency stop, snapshots and reset-button repeat |
| Cold repeat log | Seven checkpoints for each newly constructed machine |
| Repeatability report | Registers, flags, exception counters, hardware state, timing and capture-loss checks |
| `artifacts/repeats/cold-*/<checkpoint>-instructions.log` | Up to 4,096 instruction records preceding each stop; register state and interrupt entries |
| Full raw hardware writes | Every hardware write from cold reset to ModuleInit entry, with registers and timestamps |
| Decoded hardware writes | Instruction address/word, target address, width and value for every captured write |
| Hardware summary | Per-address counts, first/last events and instruction sites |
| `artifacts/repeats/cold-*/swis.log.gz` | Every SWI number and issuing instruction address |
| `artifacts/repeats/cold-*/missing-swis.log.gz` | The single real missing ColourTrans notification per cold run |
| `artifacts/repeats/cold-*/<checkpoint>.macarch-state` | Complete versioned/compressed emulator snapshots of this project ROM's execution |
| `artifacts/repeats/cold-*/<checkpoint>-MEMC.bin` and other sections | Uncompressed diagnostic sections at the three memory-validation stages |
| MCP pre-module snapshot | Final state from the interactive MCP run |
| MCP reset-button snapshot | Final state after an additional physical reset action |

The debugger records an instruction before testing an execute breakpoint. Consequently, a trace's final ModuleInit instruction is a **pending** instruction, not evidence it executed. The stop PC, unchanged empty module lists and instruction count establish the intended boundary.

## Repeatability and observation limits

All cold-run checkpoint registers, device summaries and exported sections are byte/value-identical. check_parity.py also decompresses and CRC-checks the full MCP and harness snapshots: their entire machine-state bodies are identical, SHA-256 `7d7f9a5a499db638a477a7a8edaa0561eaea51a5820ff677fa79d860fa583e47`. This shows that the external capture harness did not alter guest state relative to the MCP-driven run.

The emulator source checkout was clean at the start and end, at the same recorded commit. The MCP executable's exact binary identity was not independently established; the pinned native harness build and full-state parity provide the stronger reproducible execution reference. The harness binary hash and host compiler version are in emulator.json.

MCP's initial rolling hardware log is incomplete after its retention limit; it is preserved as interactive debugging history, not presented as the complete write trace. The external capture drains the same existing debugger API after at most 500 instructions, checks every drain against the total-entry counter, and never exceeds 75 entries. Complete capture does **not** require an emulator source or MCP API change.

Instruction compatibility remains covered by the unchanged restoration suite (27,751 independently decoded words). The boot adds real execution of reset, RAM sizing, copied dispatchers, 164 SWIs and 50 IRQs. It does not exhaustively execute all kernel instructions or prove client-installed callbacks, FIQs, deliberate exception paths, memory protections under user workloads or later runtime module behaviour.
