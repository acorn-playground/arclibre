PYTHON ?= python3

# ---------------------------------------------------------------------------
# Release (see BUILD.md). Every release ships the 2 MB ROM with its extras
# disc and the 4 MB ROM, named with manifests/release.json's version.
#
#   make release-test   build both ROMs and the disc and run every gate on them
#   (record the release with tools/record_desktop_release.py and commit)
#   make release        package dist/arclibre-VERSION/
# ---------------------------------------------------------------------------
.PHONY: all release-test release arclibre-test-parallel arclibre-test arclibre-package
all: arclibre-rom

# release-test runs the release suite on the 2 MB ROM and the extras disc, then
# builds and gates the 4 MB ROM. The 4 MB build relinks the shared C modules,
# so it comes after every 2 MB gate, and it is run here without its make
# prerequisites, which would rebuild the 2 MB ROM and discard the suite's records.
release-test: arclibre-test-parallel
	$(PYTHON) tools/build_basic_utilities.py with-alarm
	$(PYTHON) tools/build_arclibre_rom.py --four-meg
	$(PYTHON) tests/run_rom_4m.py

release:
	$(PYTHON) tools/package_release.py

# The 2 MB release suite in three balanced lanes (tests/run_release.py).
arclibre-test-parallel: arclibre-rom extras-disc
	$(PYTHON) tests/run_release.py

# The same steps, one after another.
arclibre-test: arclibre-rom extras-disc
	OPEN_ARCHIMEDES_OUTPUT="$(CURDIR)/build/desktop-baseline" $(MAKE) desktop-test multitask-test
	OPEN_ARCHIMEDES_OUTPUT="$(CURDIR)/build/desktop-baseline" $(PYTHON) tests/run.py
	$(PYTHON) tests/check_apps_build.py --graphics
	$(PYTHON) tests/run_squash.py build/arclibre
	$(PYTHON) tests/run_basic_utilities.py build/arclibre
	$(PYTHON) tests/run_standard_utilities.py
	$(PYTHON) tests/run_clock.py
	$(PYTHON) tests/run_debugger.py
	$(PYTHON) tests/run_dosfs.py
	$(PYTHON) tests/run_format.py
	$(PYTHON) tests/run_dosfs_formats.py
	$(PYTHON) tests/run_new_io.py
	$(PYTHON) tests/run_netfs.py
	$(PYTHON) tests/run_arm3.py
	$(PYTHON) tests/run_hardware.py
	$(PYTHON) tests/run_printing.py
	$(PYTHON) tests/run_extras.py
	$(PYTHON) tests/run_ram_filing.py
	$(PYTHON) tests/run_streams.py
	$(PYTHON) tests/check_stream_sleep_negative.py
	$(PYTHON) tests/run_task_services.py
	$(PYTHON) tests/run_menus.py
	$(PYTHON) tests/run_desktop_rom.py
	$(PYTHON) tests/run_sprite_commands.py
	$(PYTHON) tests/run_palette.py
	$(PYTHON) tests/run_sound.py
	$(PYTHON) tests/run_desktop_actions.py
	$(PYTHON) tests/run_filer_actions.py
	$(PYTHON) tests/run_desktop_apps.py
	$(PYTHON) tests/run_graphics_apps.py
	$(PYTHON) tests/run_app_workflows.py

# The 2 MB release's checks and source rebuild (tools/package_release.py runs it).
arclibre-package:
	$(PYTHON) tools/package_arclibre.py

# ---------------------------------------------------------------------------
# Development tiers; neither produces release evidence (see tests/run_checks.py).
# ---------------------------------------------------------------------------
.PHONY: check check-full
check:
	$(PYTHON) tests/run_checks.py check

check-full:
	$(PYTHON) tests/run_checks.py check-full

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
.PHONY: arclibre-rom arclibre-rom-4m arclibre-test-4m extras-disc extras-test dosfs-disc dosfs-test alarm-disc printing-disc
# The 2 MB ROM: build/arclibre/arclibre.rom (installed in MacArch unless
# ARCLIBRE_INSTALL_ROM=0; see BUILD.md).
arclibre-rom: arclibre-baseline startup-stack sound-components graphics-app-components task-service-components stream-components ram-filing-components standard-utility-components clock-components debugger-components desktop-utility-components network-components hardware-components printing-components
	$(PYTHON) tools/verify_candidate_patches.py
	$(PYTHON) tools/build_arclibre_rom.py

# The 4 MB ROM with everything in it: the 2 MB ROM plus DOSFS, !Alarm and
# printing, which the 2 MB ROM ships on a disc (see docs/rom-4m). Built after
# the 2 MB ROM, whose BASIC builds the printing disc's programs; never installed
# in MacArch. DOSFS's ROM objects come from the DOSFS disc build.
arclibre-rom-4m: arclibre-rom dosfs-disc
	$(PYTHON) tools/build_printing_disc.py
	$(PYTHON) tools/build_basic_utilities.py with-alarm
	$(PYTHON) tools/build_arclibre_rom.py --four-meg

arclibre-test-4m: arclibre-rom-4m
	$(PYTHON) tests/run_rom_4m.py
	$(PYTHON) tools/package_rom_4m.py

# The 2 MB ROM's one shipped floppy: DOSFS, !Alarm and printing, joined from
# their own discs (build/extras-disc/arclibre-extras.adf).
extras-disc: dosfs-disc alarm-disc printing-disc
	$(PYTHON) tools/build_extras_disc.py

extras-test: extras-disc
	$(PYTHON) tests/run_extras.py

# DOSFS as a disc-loaded module: build/dosfs/DOSFS,ffa and arclibre-dosfs.adf.
dosfs-disc: c-desktop-components
	$(PYTHON) tools/build_dosfs.py

# Runtime gate on the existing build/arclibre ROM.
dosfs-test: dosfs-disc
	$(PYTHON) tests/run_dosfs.py --no-build

# !Alarm on its own floppy: build/alarm-disc/arclibre-alarm.adf.
alarm-disc: arclibre-rom
	$(PYTHON) tools/build_alarm_disc.py

# !Printers and its modules on their own floppy: build/printing-disc/arclibre-printing.adf.
printing-disc: arclibre-rom
	$(PYTHON) tools/build_printing_disc.py

# ---------------------------------------------------------------------------
# The build graph. Host tools first, then the frozen kernel/filing baseline
# (the first restored ARM2 ROM, rebuilt exactly to check the toolchain and the
# maintained tree), then the isolated component stacks the ROM joins.
# ---------------------------------------------------------------------------
.PHONY: bootstrap c-bootstrap baseline arclibre-baseline desktop-components fpemulator fpe-test renderer-components renderer-test font-stack font-test wimp-stack wimp-test desktop-test multitask-test startup-components startup-stack sound-components action-components task-service-components c-desktop-components desktop-app-components graphics-app-components stream-components ram-filing-components clock-components network-components printing-components hardware-components debugger-components standard-utility-components desktop-utility-components
bootstrap:
	$(PYTHON) tools/bootstrap.py

# GCCSDK 3.4.6 for the C modules (Draw, Paint, Edit, FilerAct, DOSFS...).
c-bootstrap: bootstrap
	$(PYTHON) tools/bootstrap_c.py

# The frozen baseline in build/rom (tests/run.py is its regression suite).
baseline: bootstrap
	$(PYTHON) tools/build.py --baseline

# The same baseline for the desktop ROM's stacks, in build/desktop-baseline.
arclibre-baseline: bootstrap
	OPEN_ARCHIMEDES_OUTPUT="$(CURDIR)/build/desktop-baseline" $(PYTHON) tools/build.py --baseline

desktop-components: bootstrap
	$(PYTHON) tools/build_desktop.py

fpemulator: bootstrap
	$(PYTHON) tools/build_fpe.py

fpe-test: baseline desktop-components fpemulator
	$(PYTHON) tools/verify_candidate_patches.py
	$(PYTHON) tests/run_fpe.py

renderer-components: bootstrap
	$(PYTHON) tools/build_renderers.py

renderer-test: baseline renderer-components
	$(PYTHON) tools/verify_candidate_patches.py
	$(PYTHON) tests/run_renderers.py

font-stack: desktop-components renderer-components
	$(PYTHON) tools/prepare_font_stack.py

font-test: baseline font-stack
	$(PYTHON) tools/verify_candidate_patches.py
	$(PYTHON) tests/run_fonts.py

wimp-stack: font-stack fpemulator
	$(PYTHON) tools/prepare_wimp_stack.py

wimp-test: baseline wimp-stack
	$(PYTHON) tools/verify_candidate_patches.py
	$(PYTHON) tests/run_wimp.py

desktop-test: renderer-test font-test fpe-test wimp-test

# Real file-loaded tasks, separate slots and software-FPA context switching.
multitask-test: baseline wimp-stack
	$(PYTHON) tools/prepare_multitask.py
	$(PYTHON) tests/run_multitask.py

startup-components: desktop-components
	$(PYTHON) tools/build_startup.py

startup-stack: startup-components wimp-stack
	$(PYTHON) tools/prepare_desktop_startup.py

sound-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_sound.py

action-components: startup-components
	$(PYTHON) tools/build_desktop_actions.py

task-service-components: desktop-app-components
	$(PYTHON) tools/build_task_services.py

# The original C runtime (SharedCLibrary) and FilerAct.
c-desktop-components: c-bootstrap action-components
	$(PYTHON) tools/build_c_desktop.py

desktop-app-components: arclibre-baseline c-desktop-components
	$(PYTHON) tools/build_palette.py
	OPEN_ARCHIMEDES_OUTPUT="$(CURDIR)/build/desktop-defaults" $(PYTHON) tools/build.py --desktop-defaults
	$(PYTHON) tools/build_hard_disc.py
	$(PYTHON) tools/build_desktop_apps.py

graphics-app-components: desktop-app-components
	$(PYTHON) tools/build_graphics_apps.py

stream-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_streams.py

ram-filing-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_ram_filing.py

clock-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_system_modules.py clock

# Original Econet, BBCEconet, NetFS, NetFiler, NetPrint and NetStatus (docs/network).
network-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_system_modules.py network

# Original PDriver, PDriverDP, PDriverPS, PDumperSupport, PDumperDM, PDumperLJ
# and !Printers' SetPrint, for the printing disc (docs/printing).
printing-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_system_modules.py printing

# Original Podule manager and serial and parallel device drivers (docs/hardware).
hardware-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_system_modules.py hardware

debugger-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_system_modules.py debugger
	$(PYTHON) tools/build_system_modules.py arm3

standard-utility-components: arclibre-baseline startup-components
	$(PYTHON) tools/build_standard_utilities.py

desktop-utility-components: c-desktop-components startup-components network-components hardware-components
	$(PYTHON) tools/build_squash.py
	$(PYTHON) tools/generate_alarm_code.py
	$(PYTHON) tools/build_basic_utilities.py
	$(PYTHON) tools/build_calc.py
	$(PYTHON) tools/build_system_modules.py calc
	$(PYTHON) tools/build_calc.py configure
	$(PYTHON) tools/build_system_modules.py configure
