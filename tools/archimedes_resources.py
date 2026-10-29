# SPDX-License-Identifier: Apache-2.0
"""Select flat original-VIDC desktop assets without altering pinned originals."""
import hashlib,json,re,struct
from paths import REPO

def sha(b):return hashlib.sha256(b).hexdigest()

def sprites(data):
    count,first,free=struct.unpack_from('<3I',data)
    assert first==16 and free==len(data)+4
    p=first-4;rows=[]
    for _ in range(count):
        size=struct.unpack_from('<I',data,p)[0]
        assert size>=44 and size%4==0 and p+size<=len(data)
        b=data[p:p+size];name=b[4:16].split(b'\0')[0].decode('latin1')
        mode=struct.unpack_from('<I',b,40)[0]
        rows.append((name,mode,b));p+=size
    assert p==len(data)
    return rows

def filter_resources(blob):
    p=0;out=bytearray();report=[];seen=set();sprite_audit=[];furniture=None;comments=[];comment_saving=0
    # This concatenation has no terminator: Messages supplies the final zero.
    while p<len(blob):
        length,load,exec_,size,attrs=struct.unpack_from('<5I',blob,p)
        assert length>=28 and length%4==0 and p+length<=len(blob)
        record=blob[p:p+length];end=record.index(0,20);name=record[20:end].decode()
        assert name not in seen,name
        seen.add(name);dataoff=((end+4)&~3)+4;data=record[dataoff:dataoff+size]
        assert len(data)==size and struct.unpack_from('<I',record,dataoff-4)[0]==size+4
        if name in ['Resources.Wimp.Sprites','Resources.Wimp.Sprites22']:
            rows=sprites(data);kept=[];removed=[]
            for n,mode,b in rows:
                if n in ['tile_1','tile_1-8','tile_1-16']:
                    removed.append(dict(name=n,mode=mode,bytes=len(b),sha256=sha(b),reason='16bpp unsupported by VIDC1' if mode>>27==5 else 'unused global decoration in flat desktop profile'))
                else:
                    assert mode<256 or mode>>27 in [1,2,3,4],(n,hex(mode),'unsupported sprite depth')
                    kept.append((n,mode,b))
            body=b''.join(b for _,_,b in kept);new=struct.pack('<3I',len(kept),16,len(body)+16)+body
            assert sprites(new)==kept
            prefix=record[20:dataoff-4];record=struct.pack('<5I',24+len(prefix)+len(new),load,exec_,len(new),attrs)+prefix+struct.pack('<I',len(new)+4)+new
            report.append(dict(resource=name,source_sha256=sha(data),selected_sha256=sha(new),original_bytes=len(data),selected_bytes=len(new),removed=removed,retained=[dict(name=n,mode=m,sha256=sha(b),bytes=len(b)) for n,m,b in kept]))
        if name=='Resources.Wimp.Tools':
            asset=json.loads((REPO/'manifests/archimedes-furniture.json').read_text())
            new=(REPO/asset['path']).read_bytes()
            assert len(new)==asset['bytes'] and sha(new)==asset['sha256']
            prefix=record[20:dataoff-4]
            record=struct.pack('<5I',24+len(prefix)+len(new),load,exec_,len(new),attrs)+prefix+struct.pack('<I',len(new)+4)+new
            furniture=dict(asset,previous_sha256=sha(data),previous_bytes=len(data),selected_bytes=len(new))
        if name.endswith('.Messages'):
            # MessageTrans ignores lines beginning '#'. None of these comments
            # carries a notice; every message line is kept byte for byte.
            lines=data.split(b'\n');kept=[l for l in lines if not l.startswith(b'#')]
            if len(kept)!=len(lines):
                assert not any(re.search(rb'(?i)copyright|licen|apache|\(c\)',l) for l in lines if l.startswith(b'#')),name
                new=b'\n'.join(kept);prefix=record[20:dataoff-4]
                before=len(record);record=struct.pack('<5I',24+len(prefix)+((len(new)+3)&~3),load,exec_,len(new),attrs)+prefix+struct.pack('<I',len(new)+4)+new+bytes(-len(new)%4)
                comment_saving+=before-len(record)
                comments.append(dict(resource=name,source_sha256=sha(data),selected_sha256=sha(new),comment_lines=len(lines)-len(kept),original_bytes=len(data),selected_bytes=len(new)))
        if load>>8&4095==0xff9:
            start=((record.index(0,20)+4)&~3)+4
            length_now=struct.unpack_from('<I',record,12)[0]
            final_rows=sprites(record[start:start+length_now])
            # Depths from the original VIDC VWSTAB entries in Kernel/s/vdu/vdumodes.
            mode_bits={0:1,4:1,8:2,9:4,12:4,18:1,19:2,20:4,23:1,25:1,27:4,31:4}
            for n,m,b in final_rows:assert m in mode_bits,(name,n,m,'unreviewed sprite screen mode')
            sprite_audit.append(dict(resource=name,sprites=len(final_rows),modes={str(m):mode_bits[m] for m in sorted({m for _,m,_ in final_rows})},sha256=sha(record[start:start+length_now])))
        out+=record;p+=length
    assert len(report)==2 and sum(len(r['removed']) for r in report)==4
    assert furniture is not None and len(blob)-len(out)-comment_saving==155712
    return bytes(out),dict(profile='original VIDC, bitmap font, flat background',saved_bytes=len(blob)-len(out),message_comment_bytes_saved=comment_saving,message_comments=comments,records_not_listed_byte_identical=True,resources=report,bundled_sprite_files=sprite_audit,furniture=furniture)
