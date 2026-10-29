# Classic application submenu messages

Impression's main menu opened on ArcLibre, but moving onto any submenu arrow
produced no submenu. The failure was reproduced through MacArch's existing
headless MCP controls with the user's unchanged application on a disposable
copy of its hard disc. No emulator or guest-memory patch was used.

A breakpoint at Wimp's internal message-send routine captured a 40-byte message
with action **&800C0**, placeholder **&8000**, and the correct menu selection
path. The application's expected public MenuWarning number is **&400C0**, as specified
in the [Wimp PRM](https://www.riscos.com/support/developers/prm/wimp.html).
[Pre-fix metadata](reports/pre-fix.json) records the observation without including
private application code or assets.

## Cause and correction

`PublicInterfaces/SWIs` supplies complete chunk numbers and `_Base` allocations.
The older-style formulas in `hdr/Messages` added `Module_SWISystemBase` again:
`&40000 + (&1003 * &40)` became &800C0. The same mismatch affected the Wimp
message range, NetFS Notify, and PDriver's message base.

[The separate patch](../../patches/public-messages/series) uses `WimpSWI_Base`,
`NetFSSWI_Base` and `PrintSWI_Base`, retaining their actual public allocations.
The [manifest](../../manifests/public-message-inputs.json) preserves the pinned
upstream hash and records the maintained hash. The complete patch series must
reverse and reapply without fuzz. Every affected desktop consumer is rebuilt;
this is not an Impression-specific workaround.
A [fresh baseline and desktop-kernel rebuild](reports/kernel-rebuild.json)
confirms that both kernel variants remain byte-identical to their previous
verified versions, and the historical baseline ROM still matches its manifest.

The static Wimp gate now checks Notify=&40040, all 17 Wimp allocations from
MenuWarning=&400C0 through IconizeAt=&400D0, and PrintFile=&80140 against explicit
numeric expectations independent of the header formulas. This does not claim
runtime NetFS or printer support.

## Verification

The public `!MenuTest` is an independently defined Wimp 2.00 client. It uses
literal documented message numbers, the classic &8000 lazy-submenu placeholder,
Wimp_CreateSubMenu, ordinary direct submenus and real menu selection paths.
The host moves the actual pointer and clicks both submenu entries, checking
that the task exits and the desktop survives. Three cold machines must agree,
and sampled client/ROM instructions and all software-FPA traps are audited.

The negative control changes only the MenuWarning literal back to &800C0 in a
copy of the built ROM. The independent client must reject it. It does not inject
success handlers or alter the emulator. Run:

```sh
python3 tests/run_menus.py
```

On the corrected image, manual MCP replay opens all six Impression branches:
Document, Edit, Effect, Style, Frame and Misc
([private replay metadata](reports/impression-replay.json)). This is bounded menu compatibility,
not certification of Impression's editing, printing or every nested dialogue.
The [three-cold acceptance](reports/acceptance.json) and
[negative control](reports/negative-control.json) pass on ROM
`bb9d384592b076b630c95ac174ca1985a97fe18dc70025985bae80f34a3063cf`.
That image includes the sound-period correction and is installed in the local
MacArch ROM folder. Close and reopen the machine to reload it. Wider retained
regressions are recorded separately in the release integration report.
