#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Repeat complete original C/application assemblies and final candidate links."""
import argparse,hashlib,json,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument("--graphics",action="store_true");args=p.parse_args()
REPO=pathlib.Path(__file__).resolve().parents[1];out=REPO/('build/graphics-apps' if args.graphics else 'build/desktop-apps');observations=[]
for n in [1,2]:
 with (out/f'reproducibility-{n}.log').open('w') as f:
  for name,options in [('build_c_desktop.py',[]),('build_desktop_apps.py',[])]+([('build_graphics_apps.py',[]),('build_task_services.py',[]),('build_streams.py',[]),('build_ram_filing.py',[]),('build_standard_utilities.py',[]),('build_squash.py',[]),('build_basic_utilities.py',[])] if args.graphics else [])+[('build_arclibre_rom.py',['--with-graphics' if args.graphics else '--with-apps'])]:
   subprocess.run([sys.executable,REPO/'tools'/name,*options],stdout=f,stderr=subprocess.STDOUT,check=True)
 paths=set()
 for base,name in [('desktop-c-runtime','link-inputs.json'),('desktop-c-runtime','filer-inputs.json'),('desktop-apps','edit-inputs.json')]+([(f'graphics-apps/{c}','inputs.json') for c in ['Draw','Paint']] if args.graphics else []):
  paths.update(json.loads((REPO/'build'/base/name).read_text())['objects'].values())
 paths.update('build/desktop-apps/artifacts/modules/'+c+'/module.bin' for c in ['ResFiler','BASIC','BASICTrans'])
 paths.update(['build/desktop-apps/Edit.bin','build/desktop-apps/resources.bin',('build/arclibre-graphics/arclibre.rom' if args.graphics else 'build/arclibre-apps/arclibre.rom')])
 if args.graphics:
  paths.update('build/graphics-apps/'+n for n in ['Draw.bin','Paint.bin','resources.bin'])
  paths.update('build/task-services/modules/'+c+'/module.bin' for c in ['Filter','TaskWindow'])
  paths.add('build/task-services/resources.bin')
  paths.update(json.loads((REPO/'build/squash-runtime/inputs.json').read_text())['objects'])
  paths.add('build/squash-runtime/Squash.bin')
  paths.add('build/squash-runtime/resources.bin')
  for group in ['streams','ram-filing','standard-utilities','basic-utilities']:
   paths.update(str(p.relative_to(REPO)) for p in (REPO/'build'/group/'modules').glob('*/module.bin'))
   paths.add(f'build/{group}/resources.bin')
 observations.append({p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)})
assert observations[0]==observations[1]
if args.graphics:assert observations[0]['build/arclibre-graphics/arclibre.rom']==hashlib.sha256((REPO/'build/arclibre/arclibre.rom').read_bytes()).hexdigest()
subprocess.run([sys.executable,REPO/'tests/check_library_identity.py'],check=True)
(out/'reproducibility.json').write_text(json.dumps(dict(status='PASS',complete_builds=2,hashes=observations[0]),indent=2)+'\n')
print('Original application build reproducibility PASS')
