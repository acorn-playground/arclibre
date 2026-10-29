# ArcLibre !Configure

RISC OS 3.11's `!Configure` was never published. The cleaned 3.60 Configure is
a different, much larger C program: about 105 KB with its 3.5-era windows. So
`src/ArcConfigure` is new Apache-2.0 ArcLibre code that reproduces the 3.1
application. Its windows follow the RISC OS 3 User Guide (3.10, Applications
Guide ch.5, "Setting the configuration") and measured 3.11 screenshots of the
Configuration, Mouse, Keyboard, Screen and Window manager windows. It uses no
Acorn code or templates.

## Artwork

- **Section icons:** nine of the 3.60 Configure's own Apache-2.0 sprites
  (`Resources/Sprites,ff9`, pinned at `2fb77e8dc4c0` in
  `manifests/configure-inputs.json`). They are renamed `cfg_*` so that
  `*IconSprites` cannot replace sprites already in the Wimp pool.
- **Other icons:** Net, Printer, Applications, the drive sprites, the
  `!configure` and `file_ff2` icons and all option, radio and arrow sprites
  come from the pinned Wimp set.

## The application

- **Start-up:** double-clicking installs the icon on the right of the icon bar
  and opens no window.
- **Icon-bar menu:** "Configure" with Info, Save and Quit.
  - Save is the standard "Save as:" box (default name `Configure`). It saves by
    dragging or by a full pathname.
  - The file is type &FF2 Config. It holds address/value pairs for the 32 CMOS
    RAM bytes (masked to the bits) that Configure edits.
  - A file dropped on the icon or window, or double-clicked (`Message_DataOpen`,
    or `Alias$@RunType_FF2` when Configure is not running), is written back
    under the same masks.
- **Main window:** "Configuration", 624 × 424 OS units. It has twelve sections
  in the 3.11 order.
  - Net is shaded when NetFS is not running, as on 3.11: NetFS is in the ROM
    but starts only on an Econet station. The Net window is described in
    `docs/network/RESULTS.md`.

### Sections

Each control reads the kernel's or module's own CMOS field. It writes through
the module's `*Configure` keyword where one exists, and otherwise writes the
field directly with the encoding of the 3.60 Configure source for this
kernel. Most sections also apply the change to the running machine.

| Section | Controls | Written as | Applied live |
|---|---|---|---|
| Hard disc drives | ST506 and IDE counts (applied by OK). Spindown and SCSI are shaded, as on a desktop machine without SCSIFS. | `HardDiscs`, `IDEDiscs` | — |
| Floppy disc drives | Drive count (applied by OK) | `Floppies` | — |
| Printer | Port: None, Parallel, Serial, Net; Ignore character | `Print`, `Ignore`, `NoIgnore` | — |
| Mouse | Five speeds | MouseStep | OS_Word 21 |
| Mouse | Drag and double-click delays and distances | Wimp keywords | Wimp |
| Keyboard | Auto-repeat on/off, delay, repeat | `Delay`, `Repeat` | OS_Byte 11/12 |
| Keyboard | Caps lock On, Off, Shift | Caps field | OS_Byte 202 |
| Memory allocation | Seven sizes in K; typed values apply on Return | `ScreenSize` … `RamFsSize` | Effective after reset |
| Sound | Volume bar, voice name (menu of installed voices), voice number, loudspeaker | Sound byte | Sound_Volume, Sound_AttachVoice, Sound_Speaker |
| Sound | Quiet or loud beep | Beep bit | OS_Byte 212 |
| Screen | Monitor type (Auto shades the radios) | `MonitorType` | — |
| Screen | Automatic mode | `WimpMode Auto` | — |
| Screen | Interlace | TV bits | — |
| Screen | Blank delay, Off to 30 Min. | Blank-time bits | `*BlankTime` |
| Screen | Default mode | `WimpMode` | — |
| Screen | Vertical adjust | TV bits | OS_Byte 144 and `Wimp_SetMode` |
| Fonts | FontMax2–5 (applied by OK) | `FontMax2`–`FontMax5` | FontManager applies it at once |
| Window manager | Interactive file copying | FilerAction bit | — |
| Window manager | WimpFlags bits 0–7 (Beep is bit 4 inverted); All/None for the instant-drag options | WimpFlags | — |
| Application auto-start | The Desktop module's ROM-application boot bits (`DeskbootCMOS`) for !Alarm … !Paint; All/None. !Alarm is shaded when it is not in `Resources:` (ArcLibre ships it on disc), and All leaves its bit clear. | Boot bits | — |
| Net | File and printer server (number or name); Use Arthurlib; Broadcast Loader Enable and Colour hourglass | NetFS and NetPrint CMOS; &11 bit 1; &C3 bits 6 and 7 | `FS`, `PS` |

## Build

`bas/Configure` is BBC BASIC text. It is built like `!Calc` by
`tools/build_calc.py configure`:

- tokenised twice with the ROM's own BASIC 1.14, identically;
- the licence lines are numbered 0;
- squished from 18.8K to 15.8K;
- packaged with `!Run`, `!Help` and the 9-sprite file by the new `!Configure`
  wrapper module, `s/ArcConfigure`, about 20.5K in all.

It is registered as `Resources:$.Apps.!Configure`, which is where the Desktop
module's `Config` auto-start entry runs it.

## Gate

The gate is `tests/run_basic_utilities.py`, in DesktopLaunchProbe. It
launches Configure from the Filer and checks:

- the icon-bar icon, the window furniture, the twelve section icons and the
  shaded Net icon;
- the icon-bar menu, and Save to `ADFS::0.$.Cfg` through the real Save box;
- one or more real clicks in every section, each checking the CMOS bytes:
  drag delay, mouse speed (applied live, then restored), Shift caps, delay,
  Module area by arrow and by typing `96` + Return, blank delay "30 Sec.",
  volume, the WaveSynth-Beep voice name, Serial printer, the submenus flag,
  None, auto-start All (every bit but the shaded !Alarm's)/None/!Calc and a
  click on the shaded !Alarm that changes nothing, Floppies 2 and HardDiscs 1 after OK (with
  nothing written before OK), and FontMax2 after OK;
- that double-clicking `Cfg` in the Filer makes the running Configure restore
  every recorded byte;
- Quit.

The saved file is checked as type &FF2, 64 bytes. The Net window is checked in
a separate ConfigureNet trial on an Econet station (`docs/network/RESULTS.md`).
Network settings are not recorded in saved files.

## Not modelled

- Broadcast loading itself: its two CMOS bits are stored, but there is no
  BroadcastLoader module (3.11 had none in ROM either).
- Server menus with real servers: no file or printer server is emulated.
- IDE spindown: no portable hardware.
- SCSI: there is no SCSIFS.
- The original's interactive help and Info wording, which are undocumented.
- The 3.11 drawing of option and radio boxes comes from the ROM's Wimp
  sprites, so it matches the other ArcLibre dialogues rather than 3.11's
  star and green-dot sprites.
