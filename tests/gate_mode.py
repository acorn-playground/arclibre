# SPDX-License-Identifier: Apache-2.0
"""Shared --probe handling for runtime gates.

A full gate runs three cold boots, requires identical observations and runs its
negative control; only it writes acceptance.json, which release recording
requires. With --probe a gate runs one cold boot, skips the negative control
and writes probe.json instead, leaving any acceptance record untouched.
"""
import json,sys
PROBE='--probe' in sys.argv
COLD=[1] if PROBE else [1,2,3]

def start(out):
 """Prepare the gate's output directory and clear the stale record it will replace."""
 out.mkdir(parents=True,exist_ok=True)
 (out/('probe.json' if PROBE else 'acceptance.json')).unlink(missing_ok=True)

def same(*series):
 """Every cold boot must observe the same thing (trivially true for one)."""
 for values in series:
  values=list(values.values()) if isinstance(values,dict) else list(values)
  assert all(v==values[0] for v in values),'cold observations differ'

def finish(out,report):
 report=dict(report,cold_boots=len(COLD))
 if PROBE:report.update(status='PROBE_PASS',negative_control_skipped=True)
 (out/('probe.json' if PROBE else 'acceptance.json')).write_text(json.dumps(report,indent=2)+'\n')

def probe_exit(out,rom,observations,name):
 """In probe mode, record the single cold boot and stop before negative controls."""
 if not PROBE:return
 import hashlib
 finish(out,dict(status='PASS',rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),observations=observations))
 print(name+' probe PASS',flush=True);sys.exit(0)
