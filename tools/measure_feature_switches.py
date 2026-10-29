#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure what post-3.11 feature switches cost in the delivered ROM's modules.

For each candidate, a temporary copy of the module's existing build work tree
is assembled twice with the same assembler, headers and environment as its
builder: once as delivered, once with only that switch changed. The report
gives the size change and whether the variant still assembles. Nothing in the
build tree or the ROM changes; this only informs which switches are worth a
reviewed, guarded patch. Run after the ROM build (make arclibre-rom).
"""
import json,os,pathlib,re,shutil,subprocess,tempfile
from paths import REPO,HOST
from module_image import load_aof
B=REPO/'build'
MODULES={
 'Wimp':dict(work=B/'desktop-components/work/Wimp',hdr=B/'desktop-components/Hdr',entry='s/Wimp',options='s/Options'),
 'FontManager':dict(work=B/'desktop-components/work/FontManager',hdr=B/'desktop-components/Hdr',entry='s/Fonts',options='s/Fonts01'),
 'Sound0':dict(work=B/'sound/work/Sound0',hdr=B/'sound/Hdr',entry='s/Sound0',options='s/Sound0'),
 'FileCore':dict(work=B/'desktop-defaults/work/FileCore',hdr=B/'desktop-defaults/build/Hdr',entry='s/FileCore',options='s/DebugOpts',predefine=['ArcLibreDelivered SETL {TRUE}']),
}
# (module, switch, value to try, what 3.11 lacked)
CANDIDATES=[
 ('Wimp','outlinefont','false','outline-font desktop (RISC OS 3.5)'),
 ('Wimp','windowsprite','false','textured window backgrounds (3.5)'),
 ('Wimp','NewErrorSystem','false','watchdog and new error system (3.5)'),
 ('Wimp','ErrorServiceCall','false','Wimp_ReportError service call (3.5)'),
 ('Wimp','Stork','false','portable power saving (A4)'),
 ('Wimp','hvblip','false','scroll-bar blips (3.5)'),
 ('Wimp','togglebits','false','Shift-toggle-size behaviour (3.5)'),
 ('Wimp','UseDynamicArea','false','dynamic-area sprite pool (Medusa)'),
 ('Wimp','Medusa','false','Medusa memory management'),
 ('FontManager','build_for_green','true','Medusa-specific font cache handling'),
 ('FontManager','bigbuffers','false','8K path-conversion buffers'),
 ('Sound0','StorkPower','False','portable sound power control (A4)'),
 ('Sound0','EnableIRQsIn16bit','False','16-bit sound hardware (Risc PC)'),
 ('FileCore','BigDisc','F','discs over 512 MB (3.6)'),
 ('FileCore','BigShare','F','large-disc sharing (3.6)'),
 ('FileCore','TwoGigFix','F','2 GB file fixes (3.6)'),
 ('FileCore','DriveStatus','F','drive status reporting (3.6)'),
 ('FileCore','FullAtts','F','extended directory attributes (3.6)'),
]
def assemble(m,root):
 env=dict(os.environ,HDR_PATH=str(m['hdr']),MACHINE='A440',IMAGESIZE='2048K',LOCALE='UK')
 obj=root/'out.aof'
 cmd=[str(HOST/'bin/asasm')]+[f'-PreDefine={p}' for p in m.get('predefine',[])]+['-Uppercase','-cpu=ARM2','-apcs','3/26bit','-aof',m['entry'],str(obj)]
 r=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True)
 if r.returncode:return None,(r.stdout+r.stderr).strip().splitlines()[-3:]
 try:return load_aof(obj)['size'],None
 except AssertionError:return None,['assembles, but needs relocation (not position-independent)']
def variant(name,switch,value):
 m=MODULES[name]
 with tempfile.TemporaryDirectory(prefix='arclibre-switch-') as tmp:
  root=pathlib.Path(tmp)/name;shutil.copytree(m['work'],root)
  if switch:
   p=root/m['options'];t=p.read_text(encoding='latin-1')
   pattern=re.compile(r'^('+re.escape(switch)+r'\s+SETL\s+)(\S+)',re.M)
   found=pattern.findall(t)
   if not found:return None,['switch not found'],None
   t=pattern.sub(lambda x:x.group(1)+value,t);p.write_text(t,encoding='latin-1')
   original=found[0][1]
  else:original=None
  size,err=assemble(m,root)
  return size,err,original
report=[];baseline={}
for name in MODULES:
 size,err,_=variant(name,None,None);assert size,(name,err);baseline[name]=size
for name,switch,value,what in CANDIDATES:
 size,err,original=variant(name,switch,value)
 row=dict(module=name,switch=switch,delivered=original,tried=value,removes=what,assembles=err is None)
 if err is None:row['saved_bytes']=baseline[name]-size
 else:row['error']=err
 report.append(row);print(f"{name:12}{switch:18}{str(original):8}->{value:6} "+(f"{row['saved_bytes']:7} bytes" if err is None else 'not usable: '+' | '.join(err)[:150]),flush=True)
out=B/'feature-switches.json';out.write_text(json.dumps(dict(baseline=baseline,candidates=report),indent=2)+'\n');print(out)
