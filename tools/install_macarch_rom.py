#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Refresh the explicitly configured local MacArch ROM after a normal build."""
import hashlib,json,os,pathlib,tempfile
from paths import REPO

def install():
    settings=REPO/'arclibre.local.json'
    if os.environ.get('ARCLIBRE_INSTALL_ROM')=='0' or not settings.exists():
        return
    config=json.loads(settings.read_text())
    destination=pathlib.Path(config['macarch_rom']).expanduser()
    data=(REPO/'build/arclibre/arclibre.rom').read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if destination.exists():
        previous=hashlib.sha256(destination.read_bytes()).hexdigest()
        if previous not in [config.get('installed_sha256'),digest]:
            raise RuntimeError(f'{destination} changed independently; check the local install configuration')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.arclibre-',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp,0o644)
        os.replace(tmp,destination)
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)
    config['installed_sha256']=digest
    settings.write_text(json.dumps(config,indent=2)+'\n')
    print(f'Installed {destination}\nSHA-256 {digest}\nReopen the MacArch machine to reload ROM bytes (Power Cycle retains its loaded ROM).')

if __name__=='__main__':
    install()
