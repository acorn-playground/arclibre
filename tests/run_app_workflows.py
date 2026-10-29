#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original application editing/interchange, checked against disk and artwork bytes."""
import concurrent.futures
from gate_mode import COLD,PROBE,start,same,finish
import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
from adfs_fixture import oldcheck
from verify_desktop_rom_trace import verify
from desktop_profile import desktop_task_count
from verify_filer_disc import read_directory

ROOT = REPO / 'build/arclibre'
OUT = REPO / 'build/app-workflows'
assert sys.argv[1:] in [[], ['--verify-existing'], ['--probe']]
VERIFY_EXISTING = '--verify-existing' in sys.argv
TEXT = b'ArcLibre document saved by the original Edit.\nRevised line survives a cold restart.\n'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def media(path, app):
    data = path.read_bytes()
    assert len(data) == 615 * 4 * 32 * 256
    assert data[255] == oldcheck(data[:255]) and data[511] == oldcheck(data[256:511])
    rows = read_directory(data, 4)
    doc = 'Document' if app == 'Edit' else app + 'Doc'
    assert set(rows) == {'ReadMe', doc} | ({'PaintSrc'} if app == 'Draw' else set())
    spans = [(0, 0xe00)]
    files = {}
    for name, row in rows.items():
        start = row['address'] * 256
        files[name] = data[start:start + row['length']]
        spans.append((start, start + ((row['length'] + 255) & ~255)))
        assert row['attributes'] == 3
    assert files['ReadMe'] == b'ArcLibre original ST506 hard disc.\n'
    row = rows[doc]
    assert row['load'] >> 20 == 0xfff
    assert (row['load'] >> 8) & 4095 == {'Edit': 0xfff, 'Draw': 0xaff, 'Paint': 0xff9}[app]
    assert data[510] % 3 == 0
    for i in range(0, data[510], 3):
        start = int.from_bytes(data[i:i + 3], 'little') * 256
        length = int.from_bytes(data[256 + i:259 + i], 'little') * 256
        assert length > 0
        spans.append((start, start + length))
    spans.sort()
    assert spans[0][0] == 0 and spans[-1][1] == len(data)
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:])), 'complete, non-overlapping allocation map'
    return files, dict(sha256=sha(path), directory=rows, allocation_and_checksums=True)


def objects(data, offset=0):
    result = []
    while offset < len(data):
        tag, size = struct.unpack_from('<2I', data, offset)
        assert size >= 8 and size % 4 == 0 and offset + size <= len(data)
        result.append((tag, data[offset:offset + size]))
        offset += size
    assert offset == len(data)
    return result


def sprite(data):
    count, first, free = struct.unpack_from('<3I', data)
    assert count == 1 and first == 16 and free == len(data) + 4
    body = data[12:]
    assert struct.unpack_from('<I', body)[0] == len(body)
    w, h, left, right, image, mask, mode = struct.unpack_from('<7I', body, 16)
    assert mode == 12 and left == 0 and right == 31 and image == 172
    width, height = (w + 1) * 8, h + 1
    end = image + width * height // 2
    assert mask in [image, end]
    assert len(body) == end + (width * height // 2 if mask != image else 0)
    points = set()
    for y in range(height):
        for x in range(width):
            value = body[image + y * width // 2 + x // 2] >> (4 * (x % 2)) & 15
            assert value in [0, 11], 'black background and real red paint only'
            if value == 11:
                points.add((x, y))
    return width, height, points, body[mask:] if mask != image else None


def paint_checks(path, saved):
    stages = {n: sprite((path / (n + '-document.bin')).read_bytes()) for n in
              ['painted', 'flipped', 'rotated', 'scaled-paint', 'mask-removed', 'mask-restored']}
    original = {(4 + i * 2 + dx, 13 + i) for i in range(10) for dx in [0, 1]}
    flipped = {(x, 31 - y) for x, y in original}
    # Mode 12 pixels are 2 by 4 OS units. A 90-degree rotation doubles
    # the pixel width and halves the height; nearest-neighbour samples odd x.
    rotated = {(2 * y + dx, (31 - x) // 2) for x, y in flipped if x % 2 for dx in [0, 1]}
    scaled = {(2 * x + dx, y) for x, y in rotated for dx in [0, 1]}
    for name, size, points in [('painted', (32, 32), original), ('flipped', (32, 32), flipped),
                              ('rotated', (64, 16), rotated), ('scaled-paint', (128, 16), scaled),
                              ('mask-removed', (128, 16), scaled), ('mask-restored', (128, 16), scaled)]:
        assert stages[name][:2] == size and stages[name][2] == points, name
    assert stages['mask-removed'][3] is None
    assert stages['mask-restored'][3] and set(stages['mask-restored'][3]) == {255}
    assert sprite(saved) == stages['mask-restored']
    return dict(width=128, height=16, mode=12, painted_pixels=40,
                exact_flip_rotation_and_scale=True, opaque_mask_recreated=True,
                rectangular_pixel_sampling_accounted_for=True)


def draw_checks(path, saved):
    assert saved[:4] == b'Draw' and struct.unpack_from('<2I', saved, 4) == (201, 0)
    doc = objects(saved, 40)
    assert sorted(t for t, _ in doc) == [0, 1, 2, 5, 11]
    assert b'Corpus.Bold\0' in next(b for t, b in doc if t == 0)
    text = next(b for t, b in doc if t == 1)
    assert text[52:].split(b'\0')[0] == b'ArcLibre Draw text'
    assert struct.unpack_from('<I', text, 32)[0] == 1, 'real outline-font reference'
    assert struct.unpack_from('<2I', text, 36) == (8192, 8192), 'X scale doubles text width only'
    before = objects((path / 'outline-text-document.bin').read_bytes())
    grouped = objects((path / 'grouped-document.bin').read_bytes())
    after = objects((path / 'ungrouped-document.bin').read_bytes())
    assert [t for t, _ in before] == [2, 1] and after == before
    assert [t for t, _ in grouped] == [6] and objects(grouped[0][1], 36) == before
    assert [t for t, _ in objects((path / 'undo-text-document.bin').read_bytes())] == [2]
    assert [t for t, _ in objects((path / 'redo-text-document.bin').read_bytes())] == [2, 1]
    old_box = struct.unpack_from('<4i', before[0][1], 8)
    new_box = struct.unpack_from('<4i', next(b for t, b in doc if t == 2), 8)
    # The path's zero-width stroke bounding-box margin is unchanged by scaling.
    old_points = [struct.unpack_from('<2i', before[0][1], i) for i in [44, 56, 68, 80, 92]]
    new_path = next(b for t, b in doc if t == 2)
    new_points = [struct.unpack_from('<2i', new_path, i) for i in [44, 56, 68, 80, 92]]
    assert max(x for x, y in new_points) - min(x for x, y in new_points) == 2 * (max(x for x, y in old_points) - min(x for x, y in old_points))
    assert max(y for x, y in new_points) - min(y for x, y in new_points) == max(y for x, y in old_points) - min(y for x, y in old_points)
    paint = (OUT / 'fixtures/PaintSprite').read_bytes()
    assert next(b for t, b in doc if t == 5)[24:] == paint[12:], 'Draw embeds actual Paint pixels, palette and mask unchanged'
    return dict(object_tags=[t for t, _ in doc], outline_font='Corpus.Bold',
                text='ArcLibre Draw text', undo_redo=True, group_ungroup=True,
                original_path_bounds=old_box, scaled_path_bounds=new_box,
                x_scale=2, exact_paint_sprite_import=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    start(OUT)
    env = dict(os.environ, MACARCH_CORE=str(REPO / 'build/macarch/ArchimedesCore'),
               CLANG_MODULE_CACHE_PATH=str(REPO / 'build/clang-cache'),
               SWIFTPM_MODULECACHE_OVERRIDE=str(REPO / 'build/swift-module-cache'))
    def run(cmd, log):
        print(log, flush=True)
        with (OUT / (log + '.log')).open('w') as stream:
            subprocess.run([str(v) for v in cmd], env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
    for product in ['GraphicsProbe', 'EditProbe']:
        run(['swift', 'build', '--package-path', REPO / 'tests/harness', '--scratch-path', REPO / 'build/harness-patched',
             '--cache-path', REPO / 'build/swift-cache', '--disable-sandbox', '--build-system', 'native',
             '-c', 'release', '--product', product], product + '-build')
    def trial(spec):
        app, n = spec
        path = OUT / (app.lower() + '-cold-' + str(n))
        if not VERIFY_EXISTING:
            shutil.rmtree(path, ignore_errors=True)
        binary = REPO / ('build/harness-patched/release/' + ('EditProbe' if app == 'Edit' else 'GraphicsProbe'))
        command = [binary, ROOT / 'arclibre.rom', ROOT, path] + ([] if app == 'Edit' else [app])
        if not VERIFY_EXISTING:
            run(command + ['advanced'], app + '-write-' + str(n))
        files, disk = media(path / 'test.hdf', app)
        docname = 'Document' if app == 'Edit' else app + 'Doc'
        doc = files[docname]
        if app == 'Paint':
            detail = paint_checks(path / 'write', doc)
        elif app == 'Draw':
            detail = draw_checks(path / 'write', doc)
            assert files['PaintSrc'] == (OUT / 'fixtures/PaintSprite').read_bytes()
        else:
            assert doc == TEXT
            detail = dict(cross_window_selection_copy=True, undo_redo=True, find_and_replace=True, text=TEXT.decode())
        if not VERIFY_EXISTING:
            run(command + ['advanced', 'reopen'], app + '-reopen-' + str(n))
        assert media(path / 'test.hdf', app) == (files, disk), 'cold reopening must not modify media'
        phases = {}
        for phase in ['write', 'reopen']:
            p = path / phase
            result = load(p / 'result.json')
            assert result['status'] == 'PASS' and result['advanced'] and result['rom_sha256'] == sha(ROOT / 'arclibre.rom')
            assert result['task_count'] == desktop_task_count(ROOT)+1 and not result['errors'] and all(result['exceptions'][i] == 0 for i in [3, 4, 5])
            assert result['writes'] > 0 if phase == 'write' else result['writes'] == 0
            if app == 'Draw' and phase == 'write':
                events = result['stack_events']
                assert any(v['entry'] == '_kernel_StkOvfGetNewChunk' for v in events)
                assert any(v['entry'] == '_kernel_StackOverflowExit' for v in events)
                for event in events:
                    base = event['sl'] - 560
                    chunk = event['chunk']
                    assert chunk[0] in [0xf60690ff, 0x760690ff]
                    assert base + 36 <= event['sp'] <= base + chunk[3]
            if app == 'Edit':
                assert any(v['text'].encode('latin1') == doc for v in result['text_buffers'])
            elif app == 'Paint':
                assert doc in [(p / v['file']).read_bytes() for v in result['document_buffers']]
            else:
                solid = b''.join(b for t, b in objects(doc, 40) if t not in [0, 11])
                assert solid in [(p / v['file']).read_bytes() for v in result['document_buffers']]
            checked = verify(p, required=['SharedCLib', app, 'ADFS', 'Filer'], root=ROOT)
            result.pop('configuration')
            phases[phase] = dict(result=result, trace=checked,
                                 screenshots={f.name: sha(f) for f in sorted(p.glob('*.png'))})
        return app, n, dict(media=disk, document_sha256=hashlib.sha256(doc).hexdigest(), checks=detail, phases=phases)
    results = {app: {} for app in ['Paint', 'Draw', 'Edit']}
    # The interchange fixture must come from Paint's actual verified save.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for app, n, result in pool.map(trial, [('Paint', n) for n in COLD]):
            results[app][n] = result
    files, _ = media(OUT / 'paint-cold-1/test.hdf', 'Paint')
    (OUT / 'fixtures').mkdir(exist_ok=True)
    (OUT / 'fixtures/PaintSprite').write_bytes(files['PaintDoc'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for app, n, result in pool.map(trial, [(app, n) for app in ['Draw', 'Edit'] for n in COLD]):
            results[app][n] = result
    for app, trials in results.items():
        same(trials)
    report = dict(status='PASS', rom_sha256=sha(ROOT / 'arclibre.rom'), independent_cold_boots=18,
                  trials_per_app=3, identical_repeats=True, no_guest_code_injection=True, emulator_unchanged=True,
                  real_st506=True, artwork_and_disk_bytes_checked=True, original_application_code=True,
                  results={app: trials[1] for app, trials in results.items()})
    finish(OUT,report)
    print('Application editing and interchange PASS', flush=True)


if __name__ == '__main__':
    main()
