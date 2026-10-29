#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Podule manager and serial and parallel device drivers on IOC machines.

HardwareProbe boots the delivered ROM on an emulated A440/1 and A3000 (ARM2,
IOC, 6551, IOC printer port) and types commands at the real F12 command line:
*Podules scans the four IOC slots and reports RISC OS 3.11's wording; the
Podule SWIs return the real &502 error for an empty slot; devices:$ holds the
Parallel and Serial devices; OS_SerialOp sets and reads back split baud rates
and data format, programming the 6551's control register; serial: opens and
closes; a byte written to parallel: stays queued while the printer reports
BUSY (no printer is attached), with the acknowledge interrupt enabled and no
write to the printer data latch. The negative control is the ROM without the
four modules.
"""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre')
out=R/'build/hardware-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'))
def run(cmd,name,check=True):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:return subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=check)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-hardware','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','HardwareProbe'],'harness')
exe=R/'build/harness-hardware/release/HardwareProbe'
# An error block's text, printed after a tag: X<n> (V clear) or E<n> <number> <text>.
def err(tag,call):return f'SYS "{call} TO e%;f%:IF f% AND 1 THEN PRINT "{tag}E ";~!e%;" ";:i%=4:REPEAT:VDU e%?i%:i%+=1:UNTIL e%?i%=0:PRINT ELSE PRINT "{tag}OK"'
PODULE0=err('P0',"XPodule_ReadID\",0")
PODULE3=err('P3',"XPodule_ReadHeader\",3,&8000")
BAUD='SYS "OS_SerialOp",5,7:SYS "OS_SerialOp",6,8:SYS "OS_SerialOp",5,-1 TO ,r%:SYS "OS_SerialOp",6,-1 TO ,t%:PRINT "BAUD ";r%;" ";t%'
FORMAT='SYS "OS_SerialOp",1,&15 TO ,o%:SYS "OS_SerialOp",1,-1 TO ,n%:PRINT "FORMAT ";~o%;" ";~n%'
SERIAL='f%=OPENIN"serial:":CLOSE#f%:PRINT "SERIAL OK"'
PARALLEL='f%=OPENOUT"parallel:":BPUT#f%,"ABC";:PRINT "PARALLEL QUEUED"'
COMMANDS=['*Podules','*Help Podules','*Cat devices:$','BASIC',PODULE0,PODULE3,BAUD,FORMAT,SERIAL,PARALLEL,'WAIT:3']
def trial(rom_root,model,cmds,name):
 p=out/name;shutil.rmtree(p,ignore_errors=True)
 run([exe,rom_root/'arclibre.rom',rom_root,model,p,*cmds],name)
 r=json.loads((p/'result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((rom_root/'arclibre.rom').read_bytes()),r
 return r
def after(r,i):
 """The lines printed after command i's echo, which wraps at 80 columns after its prompt."""
 s=r['screens'][i];cmd=r['commands'][i]
 j=max(k for k,l in enumerate(s) if cmd[:70] in l)+(len(cmd)+1+79)//80
 return '\n'.join(l.rstrip() for l in s[j:] if l.strip() and not l.startswith('?') and l.strip() not in ['*','>','*_','>_'])
def acia(r,i):return [x['access'].split('IOC write bank 3 addr ')[1] for x in r['acia'] if x['command']==i]
def positive(job):
 model,n=job;r=trial(root,model,COMMANDS,f'{model.lower()}-{n}');c=r['commands'];at=c.index;st=r['states']
 assert not r['errors'],r['errors']
 assert after(r,at('*Podules'))=='\n'.join(f'Podule {i}: No installed podule' for i in range(4)),after(r,0)
 assert after(r,at('*Help Podules')).startswith('==> Help on keyword Podules\n*Podules gives information about podules installed in the computer')
 cat=after(r,at('*Cat devices:$'));assert re.search(r'^Parallel\s+W/\s+Serial\s+WR/$',cat,re.M),cat
 # Podule 0's ID byte reads as absent; slot 3 is the last IOC slot.
 assert after(r,at(PODULE0))=='P0E 502 No installed podule' and after(r,at(PODULE3))=='P3E 502 No installed podule'
 assert after(r,at(BAUD))=='BAUD 7 8'
 # The 6551 has one baud generator, in control register bits 0-3 (&33B000C):
 # receive 9600 leaves it at the transmit rate, 1200 (8); transmit 19200 sets &F.
 # The upper bits are the unmodelled register's &FF read back.
 baud=acia(r,at(BAUD));assert baud==['33B000C = E8','33B000C = EF'],baud
 # The format is read back from the 6551's own registers, which MacArch does
 # not model (&FF, so &3F), as RISC OS 3.11 reads it; the writes encode &15:
 # word length into control bits 5-7 and parity into command bits 5-7.
 assert after(r,at(FORMAT))=='FORMAT 3F 3F',after(r,at(FORMAT))
 assert acia(r,at(FORMAT))==['33B000C = BF','33B0008 = 5F'],acia(r,at(FORMAT))
 assert after(r,at(SERIAL))=='SERIAL OK'
 # The 6551's reset, command and control registers are written at start-up.
 boot=[x['access'].split('addr ')[1] for x in r['acia'] if x['command']==0];assert boot[0]=='33B0004 = 03',boot
 assert after(r,at(PARALLEL))=='PARALLEL QUEUED'
 # IRQ A bit 0 low is printer BUSY; the driver waits for acknowledge (bit 2).
 for i in [at(PARALLEL),at('WAIT:3')]:
  s=st[i];assert s['irq_a_status']&1==0 and s['irq_a_mask']&4 and s['printer_data_writes']==0,s
 assert st[at('*Podules')]['irq_a_mask']&4==0,'acknowledge interrupt only enabled while output is queued'
 return dict(model=model,podules=after(r,0),devices=cat.splitlines()[-1],podule_errors=[after(r,at(PODULE0)),after(r,at(PODULE3))],
  baud=after(r,at(BAUD)),format=after(r,at(FORMAT)),acia_boot=boot,acia_baud=baud,acia_format=acia(r,at(FORMAT)),
  parallel=dict(queued_bytes=3,irq_a_mask=st[at(PARALLEL)]['irq_a_mask'],printer_data_writes=0))
jobs=[(model,n) for model in ['A440','A3000'] for n in COLD]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=dict(zip(jobs,pool.map(positive,jobs)))
for model in ['A440','A3000']:same([results[(model,n)] for n in COLD])
obs={model:results[(model,COLD[0])] for model in ['A440','A3000']}
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'Hardware')
run([sys.executable,R/'tools/build_arclibre_rom.py','--without-hardware'],'negative-rom')
neg=R/'build/arclibre-without-hardware';titles={m['component'] for m in json.loads((neg/'rom-layout.json').read_text())['modules']}
assert not titles&{'Podule','Serial','SerialSpt','Parallel'},titles
r=trial(neg,'A440',['*Podules','*Cat devices:$','BASIC',PODULE0,BAUD,PARALLEL],'negative-without-hardware');c=r['commands']
assert 'The disc drive is empty' in after(r,0)
assert 'Parallel' not in after(r,1) and 'Serial' not in after(r,1)
assert after(r,c.index(PODULE0))=='SWI name not known','BASIC cannot resolve the name'
assert after(r,c.index(BAUD))=='BAUD -1 -1','OS_SerialOp unclaimed without SerialDeviceSupport'
assert 'Filing system or path parallel: not present' in after(r,c.index(PARALLEL))
assert not r['acia'] and not r['printer_data']
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_control=dict(rom_sha256=sha((neg/'arclibre.rom').read_bytes()),podules='The disc drive is empty (no such command)',podule_swi='SWI name not known',
  serialop='unclaimed (R1 returned unchanged)',parallel='Filing system or path parallel: not present'),
 limits=['MacArch models no 6551 or printer: serial bytes cannot be shown on a line, and the printer port always reads BUSY, so no character is strobed out.',
  'No expansion card is fitted, so only the empty-slot scan and errors are exercised.',
  'The delivered kernel is the A440/A3000 profile (no IOEB probe), so the 82C710 paths of the A5000 and ARM250 machines are built but not reached.',
  'Physical hardware is untested.']))
print('Hardware PASS',flush=True)
