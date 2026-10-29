#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory actual ROM module headers/command tables against published 3.11 metadata.

This checks presence, not behavioural compatibility. It does not inspect a reference ROM.
Run after tools/build_arclibre_rom.py; output defaults to build/system-audit/inventory.json.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ROM_BASE = 0x03800000


def inventory():
    layout = json.loads((ROOT / 'build/arclibre/rom-layout.json').read_text())
    rom = (ROOT / 'build/arclibre/arclibre.rom').read_bytes()
    digest = hashlib.sha256(rom).hexdigest()
    if digest != layout['rom_sha256']:
        raise ValueError('ROM does not match build layout')
    symbols = json.loads((ROOT / 'build/desktop-defaults/artifacts/symbols.json').read_text())
    rows = [{'title': 'UtilityModule', 'base': symbols['UtilityMod'],
             'length': symbols['EndOfKernel'] - symbols['UtilityMod']}]
    rows += layout['modules']
    rows += [{'title': 'Kernel system command table', 'base': symbols['SysCommsModule'],
              'length': symbols['EndOfKernel'] - symbols['SysCommsModule'],
              'system_table': True}]
    modules = []
    for row in rows:
        base = row['base'] - ROM_BASE
        end = base + row['length']
        if not 0 <= base < end <= len(rom):
            raise ValueError(f'Invalid bounds for {row["title"]}')

        def word(at):
            if not base <= at <= end - 4:
                raise ValueError(f'Word outside {row["title"]}: {at:#x}')
            return struct.unpack_from('<I', rom, at)[0]

        def string(at):
            if not base <= at < end:
                raise ValueError('String outside module')
            stop = rom.index(0, at, end)
            return rom[at:stop].decode('ascii'), stop + 1

        title = row['title'] if row.get('system_table') else string(base + word(base + 16))[0]
        if title != row['title']:
            raise ValueError(f'Header title mismatch: {title}')
        help_text, _ = string(base + word(base + 20))
        commands = []
        offset = word(base + 24)
        at = base + offset
        while offset:
            if not base <= at < end:
                raise ValueError('Unterminated command table')
            if rom[at] == 0:
                break
            name, after = string(at)
            if not name or any(ord(c) < 33 or ord(c) > 126 for c in name):
                raise ValueError('Invalid command name')
            fields = (after + 3) & ~3
            code, flags, syntax, help_entry = [word(fields + i * 4) for i in range(4)]
            # Some help callbacks implement *Commands/*Syntax with a zero
            # normal handler. Preserve that distinction, never call it absent.
            if flags & 0x40000000:
                kind = 'configuration'
            elif code:
                kind = 'filing-command' if flags & 0x80000000 else 'command'
            elif flags & symbols['Help_Is_Code_Flag']:
                kind = 'help-code-entry'
            else:
                kind = 'help-only'
            commands.append({'name': name, 'kind': kind, 'flags': flags,
                             'code_offset': code, 'syntax_offset': syntax,
                             'help_offset': help_entry})
            at = fields + 16
        modules.append({'title': title, 'help': help_text, 'base': row['base'],
                        'length': row['length'], 'entries': commands})
    system_commands = modules.pop()
    titles = {m['title'] for m in modules}
    baseline = json.loads((ROOT / 'manifests/riscos311-module-baseline.json').read_text())
    comparison = [dict(m, status='present' if m['title'] in titles else
                       'partial replacement: ArcPalette' if m['title'] == 'PaletteUtil'
                       else 'absent') for m in baseline['modules']]
    return {'rom_sha256': digest, 'used_bytes': layout['used_bytes'],
            'free_bytes': len(rom) - layout['used_bytes'], 'baseline_source': baseline['source'],
            'scope': 'Module identity/registered table inventory only; not SWI or command semantics certification. Aliases, UKCommand service handlers and external programs are not enumerated.',
            'comparison': comparison, 'modules': modules, 'kernel_system_commands': system_commands}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/system-audit/inventory.json')
    args = parser.parse_args()
    result = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    for status in ('present', 'absent', 'partial replacement: ArcPalette'):
        print(f'{status}: {sum(m["status"] == status for m in result["comparison"])}')
    print(f'{len(result["modules"])} ArcLibre modules; {result["free_bytes"]} ROM bytes free')
    print(args.output)


if __name__ == '__main__':
    main()
