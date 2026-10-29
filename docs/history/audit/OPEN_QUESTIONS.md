# Decisions, unresolved evidence and next investigations

25 October 2026. **Conditional continuation of research; no approval to implement or distribute implied.** This file separates an uncertain result from an impossible one. Findings are grounded in [SOURCE_AND_LICENSES](SOURCE_AND_LICENSES.md); no compatibility test has run.

## Three implementation pathways

Ratings are qualitative engineering judgement (**I**), not measured probabilities. “High” under fitness/confidence is favourable; “High” under risk/effort is unfavourable. Unknown is not Low.

| Criterion | 1. Port/trim current RO26 | 2. Pre-conversion original-machine kernel plus selected open components | 3. Independent compatible implementation |
|---|---|---|---|
| Licence confidence / redistribution hard gate | Medium for inspected code; **Unknown for complete image**, not cleared | Medium for inspected historical code; **Unknown for chosen hybrid/assets**, not cleared | Unknown until original code/assets and legal method exist; independence does not grant third-party asset rights |
| Actual source availability/fitness | High availability; Low hardware fitness as selected | Medium–High candidate availability; best original-chipset evidence | Low existing implementation availability; specifications partially available |
| Earliest credible milestone | Medium prospects after replacing startup/memory assumptions; current image is not an ARM2 shortcut | Medium prospects for assembly/reset investigation; exact pre-conversion source provides a focused test | High feasibility of a tiny original checkpoint, but this says almost nothing about OS compatibility |
| ARM2 execution | Low as selected: later mode transitions | Medium candidate: guarded old-CPU paths survive; emitted code unverified | Medium technical feasibility; every primitive must be implemented/tested |
| MEMC/VIDC/IOC support | Medium remnants, mismatched selected integration | Medium–High candidate source, not validated | Low existing implementation in this route; hardware design/documentation available |
| ROM/RAM footprint | High risk: 4 MiB selection and later stack | Unknown; potentially better control through selective versions/omissions, no linked measurements | Unknown; new implementation can target size, full desktop/runtime cost remains |
| Tier 1 core compatibility | Medium candidate code breadth, semantic differences | Medium candidate, integration and 3.11 quirks unresolved | Low initially; large documented and observed contract to reproduce |
| Tier 2 loading/BASIC/modules | Medium code availability; old storage and later-runtime assumptions | Medium; source exists, source/version combinations need testing | Low initially; substantial loader/filing/BASIC/runtime work |
| Tier 3 desktop | Medium availability; later WIMP/resource/memory semantics | Medium availability; original-memory options useful, not a 3.11-certified desktop | Low initially; likely dominant implementation and compatibility burden |
| Tier 4 desktop utilities/applications | Unknown; no qualified runs | Unknown; no qualified runs; potentially better basis for matching old memory semantics | Unknown long-term; low near-term confidence |
| Tier 4 BASIC applications | Unknown; later BASIC is available but not tested against target programs | Unknown; runtime/VDU/error contracts must be matched | Low near-term unless an independently licensed suitable BASIC is integrated (then classify that dependency honestly) |
| Tier 4 games/direct hardware | Low as selected on wrong chipset; Unknown after port | Unknown; best chipset-source match, timing/quirks still blockers | Unknown; OS ABI plus faithful hardware access must both work |
| Toolchain risk | High: old proprietary build tools, source syntax/integration | High: historic/current include and assembler compatibility | Medium: modern tools may be used, but ARM2 and 26-bit ABI support must be demonstrated |
| MacArch testability | High for explicit core ROM input; importer constraints | High same core path; no candidate yet | High for core-path checkpoints; complete OS testing absent |
| Second emulator | Medium, use A3000/MEMC common subset; RPCEmu not target proof | Medium same limitation | Medium same limitation |
| Overall complexity / order of effort | High: substantial kernel restoration plus desktop regression work | High: substantial source integration and compatibility programme, plausibly multi-year to broad library quality | Very high: new kernel, filing, desktop, runtimes, resources and quirks; multi-year team effort is a reasonable order-of-magnitude risk |

The effort language is an inference from the subsystem scope, not an estimated schedule or commitment. A meaningful delivery estimate requires the assembly experiment, a linked size/RAM map and a qualified reference corpus. A boot milestone may be much earlier than useful application compatibility on every route.

**Recommendation:** pathway 2, still route A (a derivative), using RO26 as a source/integration catalogue rather than its current product as an ARM2-ready ROM. The explicit pre-conversion boundary is stronger evidence than choosing the oldest or newest source indiscriminately. [P1](SOURCE_AND_LICENSES.md#p1) [P2](SOURCE_AND_LICENSES.md#p2) [H2](SOURCE_AND_LICENSES.md#h2) The full 3.11 desktop/application goal remains unchanged.

This recommendation changes if: an independently reproducible and asset-cleared ARM2 RO26 configuration is demonstrated (favour pathway 1); the pre-conversion source cannot achieve lawful include/build closure or fit with the required desktop (weaken pathway 2); public historic files prove unsuitable and a well-funded independent implementation plus legal protocol becomes available (reconsider pathway 3); or ROM/RAM constraints preclude the required application corpus under acceptable hardware adaptations (NO-GO for the specified target, even if a larger emulator-only product works).

## Blocker register

| ID / priority | Question and current evidence | Next investigation / close condition | Needed from owner now? |
|---|---|---|---|
| Q1 / hard | Can the exact historic kernel and header combination assemble? No assembly run; source shows old reset/CAM paths. | Review and authorise the single [assembly experiment](FIRST_BOOT_EXPERIMENT.md); capture include graph, tool versions and ARM2 listing. | No input needed for Phase 0. Future implementation requires review. |
| Q2 / hard | Is every selected payload byte licensed and reproducible? Core code grants found, final assets/generated inputs unclosed. | Construct actual payload manifest; inspect font/sprite/locale/runtime/sample inputs and notices. Resolve rights ambiguity with maintainer/rightsholder or omit/replace the affected asset. | Only if a private entitlement or owned asset is proposed. |
| Q3 / hard | What exactly ships in the relevant 3.11 ROM/boot set? Public inventory query failed; no original ROM used. | Privately enumerate modules/versions/resources from a licensed reference; distinguish resident/unplugged/disc modules and locale. | Lawful ROM and boot/application media needed **for future reference work**, not this source audit. |
| Q4 / hard | What is the full 3.11 desktop semantic gap? Source coverage exists; Wimp RO310 still enables later behaviour. | Qualify corpus, measure memory/resource/service/event differences, then select source versions or narrowly tested shims. | Exact lawful app editions needed for later testing. |
| Q5 / hard | Does it fit 2 MiB while leaving useful 4 MiB RAM? No link map; current product selects 4 MiB. | Measure modules/resources/alignment/workspaces; preserve tier-4 corpus when trimming. Evaluate optional disc loading or physical storage separately. | Decision on acceptable hardware adaptations later, only after concrete alternatives exist. |
| Q6 / high | Can an ARM2-safe toolchain build it without copying prebuilt payload? Documented route uses purchased tools. | Inventory lawful DDE/aasm version, guest and tool/runtime licensing; evaluate AsAsm conversion separately if necessary. | Tool entitlement/access if that route is selected. No installation requested now. |
| Q7 / high | How much current ROOL history/provenance matches mirror? Live official Git/API unavailable. | Retry upstream and compare selected objects/notices; use official archives if published and identify exact versions. | None. |
| Q8 / high | Which storage profile passes? WD1772 implementation exists; ST506 has a BigDisc conflict. | Prove floppy path first; resolve ST506 addressing and shared transfer paths with data-integrity tests. | No extra media beyond original test fixtures at first. |
| Q9 / high | Is a later WIMP compatible with MEMC task slots and old kernel services? Distinct memory options survive. | Explicitly map kernel/WIMP interfaces and task-slot/page behaviour, including low-memory error cases. | None for source analysis. |
| Q10 / high | How does the pinned joiner footer match old POST? 0.03 code differs from modern documentation and contains a questionable CRC loop. | Verify source contracts and generated image checksum/header rules before any ROM boot test. | None. |
| Q11 / medium | What are the exact A440/1 ROM socket/carrier limits? Address window verified, board wiring not audited. | Obtain board-revision service schematic, verify address lines/width/access timing/voltage and carrier design; no manufacturing yet. | Board revision/photos only if physical deployment is later requested. |
| Q12 / medium | Does the second emulator accept candidate image layout and required timing? README only inspected. | Pin and inspect Eichhörnchen loader/hardware, then repeat common A3000 subset independently. | None. |
| Q13 / medium | What MacArch revision should host later work? Local checkout contains ongoing unrelated edits. | Select an immutable commit or record explicit working-tree patch hashes with the owner before runtime testing; current audit uses HEAD object contents. | No clarification needed for completed read-only inspection. |
| Q14 / low for experiment | Is inaccessible MIDIPlay needed? Not needed for kernel experiment; some optional product needs may differ. | Omit unless final corpus requires it, then obtain public source/permission and pin it. | None. |

## Phase-0 acceptance audit

| Question from the brief | Answer this evidence supports | Closed? |
|---|---|---|
| What exactly is in twentysix and where? | Complete manifest/ref snapshot, exact inspected core trees and product mapping; branches include placeholders and mixed-age code | **Ref/source discovery closed; full build reproduction open** |
| How much usable original hardware support survives? | Actual MEMC, VIDC, keyboard, WD1772 and old ARM2/ARM3 reset paths found and cited | **Source-level answer yes; usability untested** |
| What happens after reset and which parts are wrong? | Current POST/reset uses later modes/IOMD; pre-conversion original mappings exist; dependency trace supplied | **Static trace supplied; dynamic path open** |
| Does ROM capacity make it implausible? | 4 MiB current configuration exceeds baseline storage; MEMC address space does not prove a 2 MiB ceiling | **Footprint/board viability open** |
| Can all candidate contents be built and redistributed? | No blanket answer yet; code grants and exceptions recorded; assets/tools/closure unresolved | **Hard gate open** |
| What proportion of the 3.11 stack is available and what blocks ordinary apps? | Major functional source categories located; no exact denominator or byte/behaviour percentage; memory/resources/version semantics are blockers | **Exact inventory and integration open** |
| Is full 3.11 application ABI plausible? | Conditional source-based case for investigation, not a demonstrated product; no tier measured | **Open** |
| Smallest decisive experiment? | Assemble and inspect the pinned pre-conversion kernel for ARM2 with lawful include closure | **Plan supplied, not executed** |
| Would clean-room change the conclusion? | It changes provenance/dependency strategy but increases the implementation/quirk burden substantially | **Assessment supplied; legal feasibility not certified** |

The eight requested documents are delivered as an evidence-backed **Phase-0 research report with explicit open gates**, not as proof that every Phase-0 acceptance question has a definitive positive answer. No claim of application compatibility, fully free toolchain, image redistributability or hardware-ready packaging is made.
