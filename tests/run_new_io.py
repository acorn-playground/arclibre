#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The A5000 family's I/O: IOEB, and the 82C711's floppy, IDE, serial and parallel.

As RISC OS 3.11's one ROM did, the delivered kernel probes at reset for an
IOEB and an 82C710/711 (Hdr:Machine.A440's HasIOEB), and reports them through
OS_ReadSysInfo 2 and 3. ADFS, Serial and Parallel choose their hardware from
those, so the ROM's original drivers for the new I/O run unchanged. NewIOProbe
boots the delivered ROM to the desktop, three cold boots each, on an emulated
A5000 (ARM3, IDE), A3010 (ARM250, no IDE) and A3020 (ARM250, IDE), and types
at the real F12 command line:

- OS_ReadSysInfo 2 gives IOEB and an 82C710-class chip (1, 1, 0: as RISC OS
  3.11 on the same emulated A5000) and 3 its sub-units;
- the 765 floppy controller catalogues an ADFS D floppy and writes to it;
- on IDE, ADFS catalogues a hard disc built on the host and copies a file
  each way, checked on the host from both discs;
- OS_SerialOp 9600 baud programs the UART's divisor latch with 12
  (1.8432 MHz / 16 / 9600), from MacArch's trace of 82C711 writes;
- a byte for the printer reaches the 82C711's printer data port, strobed
  through its control port (MacArch models no printer acknowledge, so only
  the first byte goes);
- on an A5000 with a multisync or VGA monitor, the kernel reads the monitor
  ID lines as monitor types 1 and 3, and on VGA selects the 25.175 MHz
  pixel clock.

The negative control is the frozen baseline ROM, which does not probe
(HasIOEB false): on the same A5000 its ADFS drives the 1772 that isn't there,
never touches the 82C711, and catalogues nothing.
"""
import concurrent.futures,hashlib,json,os,pathlib,re,shutil,subprocess,sys
from gate_mode import COLD,start,same,finish,probe_exit
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tests'))
from verify_filer_disc import read_directory
args=[x for x in sys.argv[1:] if not x.startswith('--')]
root=R/(args[0] if args else 'build/arclibre');baseline=R/'build/desktop-baseline/artifacts'
out=R/'build/new-io-tests';start(out)
env=dict(os.environ,MACARCH_CORE=str(R/'build/macarch/ArchimedesCore'),CLANG_MODULE_CACHE_PATH=str(R/'build/clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(R/'build/swift-module-cache'),MACARCH_SIO_TRACE='1')
def run(cmd,name):
 print(name,flush=True)
 with (out/(name+'.log')).open('w') as f:subprocess.run([str(x) for x in cmd],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
def sha(b):return hashlib.sha256(b).hexdigest()
run(['swift','build','--package-path',R/'tests/harness','--scratch-path',R/'build/harness-newio','--cache-path',R/'build/swift-cache','--disable-sandbox','--build-system','native','-c','release','--product','NewIOProbe'],'harness')
exe=R/'build/harness-newio/release/NewIOProbe'
floppy=(R/'build/dosfs/arclibre-dosfs.adf').read_bytes();README=(R/'src/ArcLibre/dosfs/ReadMe').read_bytes()
IDE_README=b'ArcLibre IDE hard disc, built on the host.\n'
SYS='SYS "OS_ReadSysInfo",2 TO a%,b%,c%:SYS "OS_ReadSysInfo",3 TO d%,e%:PRINT "SYS ";~a%;" ";~b%;" ";~c%;" ";~d%;" ";~e%'
MONITOR='SYS "OS_ReadSysInfo",1 TO a%,b%,c%:PRINT "MONITOR ";b%'
BAUD='SYS "OS_SerialOp",5,7:SYS "OS_SerialOp",5,-1 TO ,r%:PRINT "BAUD ";r%'
PRINTER='VDU 2,1,65,3:PRINT "PRINTED"'
FLOPPY=['*Cat :0','*Copy ADFS::0.$.ReadMe ADFS::0.$.Copy ~C~V']
IDE=['*Cat :4','*Copy ADFS::0.$.ReadMe ADFS::4.$.FromFloppy ~C~V','*Copy ADFS::4.$.ReadMe ADFS::0.$.FromIDE ~C~V']
def commands(ide):return FLOPPY+(IDE if ide else [])+['*FX 5,1','BASIC',SYS,BAUD,PRINTER,'WAIT:3','QUIT']
def trial(rom_root,model,monitor,cmds,name,rom='arclibre.rom'):
 p=out/name;shutil.rmtree(p,ignore_errors=True);p.mkdir();(p/'disc0.in.adf').write_bytes(floppy)
 run([exe,rom_root/rom,rom_root,model,monitor,p/'disc0.in.adf',p/'run',*cmds],name)
 r=json.loads((p/'run/result.json').read_text());assert r['status']=='PASS' and r['rom_sha256']==sha((rom_root/rom).read_bytes()),r
 # 82C711 accesses, by command: (port, value) for writes.
 io={};c=None
 for l in (out/(name+'.log')).read_text().splitlines():
  if l.startswith('COMMAND '):c=int(l.split()[1])
  m=re.match(r'SIO write \w+ port (\w+) = \w{2}(\w{2})',l)
  if m and c is not None:io.setdefault(c,[]).append((m.group(1),int(m.group(2),16)))
 return p,r,io
def after(r,i):
 """The lines printed after command i's echo, which wraps at 80 columns after its prompt."""
 s=r['screens'][i];cmd=r['commands'][i]
 j=max(k for k,l in enumerate(s) if cmd[:70] in l)+(len(cmd)+1+79)//80
 return '\n'.join(l.rstrip() for l in s[j:] if l.strip() and not l.startswith('?') and l.strip() not in ['*','>','*_','>_'])
def file(p,name):
 b=(p/'run/disc0.adf').read_bytes();e=read_directory(b,4)[name];return b[e['address']*256:e['address']*256+e['length']]
def positive(job):
 model,ide,n=job;cmds=commands(ide);p,r,io=trial(root,model,'standard',cmds,f'{model.lower()}-{n}');at=cmds.index
 assert not r['errors'],r['errors']
 assert r['cpu']==('ARM3' if model=='A5000' else 'ARM250'),r['cpu']
 cat=after(r,at('*Cat :0'));assert 'Dir. ADFS::DOSFS.$' in cat and re.search(r'DOSFS\s+R/R\s+ReadMe\s+R/R',cat),cat
 assert file(p,'Copy')==README
 got=dict(model=model,cpu=r['cpu'],floppy_write=len(README))
 if ide:
  cat=after(r,at('*Cat :4'));assert 'Dir. ADFS::IDEDisc.$' in cat and 'ReadMe' in cat,cat
  hard={x['path']:x for x in r['hard_disc']}
  assert hard['FromFloppy']['length']==len(README) and hard['FromFloppy']['sha256']==sha(README),hard
  assert file(p,'FromIDE')==IDE_README
  got.update(ide=sorted(hard),ide_to_floppy=len(IDE_README))
 sysinfo=after(r,at(SYS));assert sysinfo=='SYS 1 1 0 101111 0',sysinfo
 assert after(r,at(BAUD))=='BAUD 7'
 # 9600 baud: the line control register's DLAB (bit 7) set, divisor 12 in the low latch.
 serial=io[at(BAUD)];lcr=[v for port,v in serial if port=='3FB']
 assert ('3F8',12) in serial and ('3F9',0) in serial and any(v&0x80 for v in lcr) and not lcr[-1]&0x80,serial
 printer=io[at(PRINTER)];assert ('278',0x41) in printer and any(port=='27A' for port,_ in printer),printer
 assert after(r,at(PRINTER))=='PRINTED'
 got.update(sysinfo=sysinfo,uart_divisor=12,printer_data=0x41)
 return got
def monitor(job):
 mon,n=job;p,r,io=trial(root,'A5000',mon,['BASIC',MONITOR,'QUIT'],f'a5000-{mon}-{n}')
 assert not r['errors'],r['errors']
 return dict(monitor=mon,monitor_type=after(r,1),pixel_clock_select=r['vidc_clock_select'])
MODELS=[('A5000',True),('A3010',False),('A3020',True)]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 results=list(pool.map(positive,[(m,ide,n) for m,ide in MODELS for n in COLD]))
 monitors=list(pool.map(monitor,[(mon,n) for mon in ['standard','multisync','vga'] for n in COLD]))
by_model={m:[x for x in results if x['model']==m] for m,_ in MODELS}
by_monitor={mon:[x for x in monitors if x['monitor']==mon] for mon in ['standard','multisync','vga']}
same(*by_model.values(),*by_monitor.values())
assert [by_monitor[m][0]['monitor_type'] for m in ['standard','multisync','vga']]==['MONITOR 0','MONITOR 1','MONITOR 3'],by_monitor
assert [by_monitor[m][0]['pixel_clock_select'] for m in ['standard','multisync','vga']]==[0,0,1],by_monitor
obs=dict(models={m:v[0] for m,v in by_model.items()},monitors={m:v[0] for m,v in by_monitor.items()})
(out/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
probe_exit(out,root/'arclibre.rom',obs,'New I/O')
# Negative control: the frozen baseline kernel does not probe.
# (It has no BASIC, so only the floppy is tried.)
p,r,io=trial(baseline,'A5000','standard',['*Cat :0','WAIT:10'],'negative-baseline',rom='floppy.rom')
fails='\n'.join(l.rstrip() for l in r['screens'][-1] if l.strip());assert '*Cat :0' in fails and 'Dir. ADFS::DOSFS.$' not in fails,fails
assert not any(port.startswith('3F') for port,_ in io.get(0,[])),io.get(0)
finish(out,dict(status='PASS',rom_sha256=sha((root/'arclibre.rom').read_bytes()),emulator_unchanged=True,guest_code_injection=False,observations=obs,
 negative_control=dict(rom='build/desktop-baseline (frozen baseline, HasIOEB false)',rom_sha256=sha((baseline/'floppy.rom').read_bytes()),floppy=fails.splitlines()[-1]),
 limits=['MacArch models no 82C711 serial line or printer: the UART and printer port are checked by the values written to them, and only the first printer byte goes (no acknowledge).',
  'The A4000 (as the A3020, without an Econet header option) and the A5000 with an ARM250 are not separately run.',
  'No physical A5000, A3010, A3020 or A4000 has been tested.']))
print('New I/O PASS',flush=True)
