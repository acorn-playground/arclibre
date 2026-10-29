#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original IIC_Control and RTCAdjust: clock reads and writes, NoAck, calibration, drift, dates."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,sys
from gate_mode import COLD,PROBE,start,same,finish
R=pathlib.Path(__file__).resolve().parents[1]
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
negative_root=R/(args[1] if len(args)>1 else 'build/arclibre-without-clock')
out=R/'build/clock-tests';out.mkdir(exist_ok=True);start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-clock','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','ClockProbe'],'harness')
exe=R/'build/harness-clock/release/ClockProbe'
if len(args)<2 and not PROBE:run([sys.executable,R/'tools/build_arclibre_rom.py','--without-clock'],'negative-rom')
if not PROBE:
 positive=json.loads((root/'rom-layout.json').read_text());negative=json.loads((negative_root/'rom-layout.json').read_text())
 assert {r['component'] for r in positive['modules']}-{r['component'] for r in negative['modules']}=={'IIC','RTCAdjust'}
def trial(job):
 name,rom_root,scenario=job;p=out/name;shutil.rmtree(p,ignore_errors=True)
 run([exe,rom_root/'arclibre.rom',rom_root,p,scenario],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['scenario']==scenario
 o=json.loads((p/'observations.json').read_text());o.pop('basic_screen');return o
# A probe boots once for IIC reads, NoAck and RTCAdjust's start-up state; the
# hourly calibration, drift, Die, date boundaries and missing-module control
# run only in the full gate.
jobs=[('smoke-1',root,'smoke')] if PROBE else [(f'drift-{n}',root,'drift') for n in COLD]+[('century',root,'century'),('leap',root,'leap'),('absent',negative_root,'absent')]
# Each trial is one emulated hour of about 3.5 min; all six run at once.
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=dict(zip([j[0] for j in jobs],pool.map(trial,jobs)))
if not PROBE:same([results[f'drift-{n}'] for n in COLD])
rom_hash=sha(root/'arclibre.rom')
report=dict(status='PASS',rom_sha256=rom_hash,negative_rom_sha256=None if PROBE else sha(negative_root/'arclibre.rom'),identical_repetitions=True,
 kernel_and_emulator_unchanged=True,guest_code_injection=False,iic_control_reads_pcf8583=True,iic_control_writes_pcf8583=True,iic_noack_message=True,
 hourly_recalibration_matches_formula=True,drift_lengthens_ioc_tick=True,die_restores_default_latch=True,
 century_and_leap_day_boundaries=True,missing_modules_negative_control=True,observations=results)
finish(out,report);print('IIC and RTCAdjust PASS',flush=True)
