# Inputs, public interfaces and licensing

## Exact sources

The kernel remains pinned at `3da129d209b2c78d19f6c28d9a8f15cd6f1c3bfc`, and HdrSrc at `c9113ab79d9ca2ccc49a9b7518911132ca9ffa1b`. The 13-component cohort supplies matching headers from Buffers, Colours, FileSwitch, FontManager, MsgTrans, Podule, Portable, Serial, Sound0, TerritoryManager and Wimp. These are the public cleaned 3.60 import revisions approved in the restoration plan.

The nine explicitly missing public registration headers are taken from HdrSrc `403c6dd8bce92d0629634cbf57f68f43b2f30d38`: SWIs, CMOS, Services, FSNumbers, NewErrors, UpCall, Pointer, DevNos and PaletteV. Their originals and root licence are preserved in `sources/PublicInterfaces/`. No later machine, CPU, kernel workspace or private structure header overrides the cohort.

The actual-input manifest records 113 selected inputs, original/restored hashes, generating status, revision and licence. Original cohort hashes, public header hashes, header exports and the assembler's dependency file distinguish supplied files from actual selected inputs.

## Explicit public-interface acceptance

public-interface-consumption.json records each of the **303** consumed later definitions: name, value, exact definition, revision, real caller locations, contract and decision. The compact CSV supports review. Definitions merely registered by their own macros are excluded from the consumption count. The frozen review set makes a new name or changed value fail verification rather than silently accepting it.

| Header | Consumed definitions | Restoration decision |
|---|---:|---|
| SWIs | 28 | Full allocated bases and module names feed the cohort's AddSWI/name macros; original offsets and register interfaces remain in cohort headers. OS groups are `0`, `40`, `C0`, `100`; examples include Font `40080`, Wimp `400C0`, ColourTrans `40740`, MessageTrans `41500`, Territory `43040`. Conflicting legacy zero-base aliases are explicitly removed, not used to renumber calls. |
| CMOS | 78 | Byte offsets, masks and OS_Byte selectors fit the existing byte-addressed CMOS calls/default table. They allocate no workspace. Later monitor/default values are retained as explicit 3.60 behaviour requiring a future 3.11 comparison. |
| Services | 33 | Preserve public service numbers and International subreasons used by the actual original broadcasts. No service handler is supplied by a number definition; register payloads remain in the recorded original callers. |
| NewErrors | 139 | Preserve numeric errors and token:fallback strings consumed by the original error-block/translation machinery. The real ModeNotAvailable block is shared with its existing numeric-mode caller; BadFileName's case typo is corrected. Exact 3.11 message wording remains unproven. |
| DevNos | 16 | Original IOC device numbering 0–15 matches the selected real dispatch tables. No IOMD interrupt model is imported. |
| PaletteV | 7 | Reasons 0–6 feed existing VIDC palette/flash/default/blanking implementations. No handler is stubbed. |
| UpCall | 2 | MovingMemory `101` and Claimed `0` retain the original moving-memory/vector negotiation. |
| FSNumbers, Pointer | 0 | Headers are included by the original include chain but none of their definitions is consumed in the selected assembly. They do not add a runtime payload. |

These are explicit restoration acceptance decisions based on the pinned public allocations and the original caller shape. Symbol provenance and a successful build do not prove all 3.11 behaviours. The per-entry decisions deliberately preserve that distinction.

For original-machine identity, the published [OS_ReadSysInfo contract](https://www.riscos.com/support/developers/prm/vdu.html) describes absent hardware/identity results. This board has no Dallas ID or IOEB/LC/combo ASIC. The restored producer zeros the already-existing UniqueMachineID storage, reason 2 reads it, reason 4 uses the genuine no-Ethernet-address return, and reason 5 returns no raw ID. The source's own later reason-5 convention is preserved; it is not evidence that 3.11 applications require later query reasons. No arbitrary serial number, MAC address or chip workspace was fabricated.

## Licences and distribution considerations

All 14 target source groups have a preserved Apache-2.0 root licence, recorded with hashes in licences.json. Embedded notices remain in original/restored sources; modified source files carry change notices. The component, patches and original glue are delivered with `LICENSE`. This does not relicense upstream tools.

The selected bitmap font is **this cohort's** `s/vdu/vdufontl1`, bearing the public Acorn copyright/Apache notice. It was not taken from a ROM, nor copied from the previous experiment's later font revision. It is not certified as glyph-identical to 3.11. Help is generated from the cohort's Apache-covered HelpStrs/Tokens by public tokenise; the generated file records that provenance.

| Host dependency | Pin / terms | Target relationship |
|---|---|---|
| AsAsm 2.01 | [GCCSDK `212d4567f007e7d30f4af3d6e1919a3d8a115b1c`](https://github.com/riscos-dot-info/gccsdk/tree/212d4567f007e7d30f4af3d6e1919a3d8a115b1c/tools/asasm), GPL-2.0-or-later; COPYING | Host assembler; no runtime linked into kernel. The observation patch remains GPL-covered. |
| ELF toolchain / decaof dependency | Same GCCSDK tree; retain per-file BSD-style and other supplied notices | Host object-writing/inspection support only |
| tokenise | Public Tools/Sources/tokenise `d6ea854482663935562dc4c1bc2cde4bf3b570aa`, Apache-2.0; delivered source and licence | Generates text from the identified target inputs; two host C type fixes preserve its algorithm |
| GNU M4 / Autoconf / Automake / Libtool | Official archive/version/hash evidence in toolchain manifest; their supplied licences retained upstream | Local host bootstrap only |
| Apple Clang / macOS SDK | Existing installed host developer tools | No SDK or host runtime bytes linked into target |

The evidence archive excludes native tool binaries and external tool checkouts. It includes pins, host adapters, tokeniser source/patch and observation patch. Shipping tool binaries later requires their applicable corresponding-source/notices obligations. Tool licences do not automatically replace the kernel source licence.

No proprietary ROM image, ROM code, extracted asset, precompiled target module, DDE/aasm binary or proprietary guest environment was used. Available notices support redistribution of this identified component/source package under their terms; this is not clearance of a future full ROM's other modules, desktop assets, trademarks or applications. The full-payload licence gate remains open.
