#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble a regular image FILE; never accepts block devices or writes a card."""
import argparse
import gzip
import hashlib
from pathlib import Path
import shutil
import stat
import struct
import subprocess

BASE_SHA256 = '4280732daf9fb32ee59f56f727134c5a5e5c8a2b64add593a5e8e50c78654a01'
PACKAGE = Path(__file__).resolve().parent
ASSETS = PACKAGE / 'boot-assets'
BOOT_OFFSET = 16 * 1024 * 1024
IMAGE_SIZE = 4848615424

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def regular(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Only ordinary files are accepted: {path}')

def patch_image(image):
    image = Path(image)
    regular(image)
    if image.stat().st_size != IMAGE_SIZE:
        raise ValueError('Unexpected base image length')
    with image.open('r+b') as f:
        mbr = f.read(512)
        if mbr[510:512] != b'\x55\xaa': raise ValueError('Invalid MBR')
        p1 = struct.unpack('<B3sB3sII', mbr[446:462])
        p2 = struct.unpack('<B3sB3sII', mbr[462:478])
        if (p1[2], p1[4], p1[5]) != (12, 32768, 8388608):
            raise ValueError('Unexpected boot partition')
        if (p2[2], p2[4], p2[5]) != (131, 8421376, 1048576):
            raise ValueError('Unexpected SHARE partition')
        # Remove the donor board's loader and persistent environment area.
        f.seek(32768)
        f.write(bytes(BOOT_OFFSET - 32768))
        for filename, offset, limit in [
            ('idbloader.img', 32768, 8 * 1024 * 1024),
            ('u-boot-dtb.img', 8 * 1024 * 1024, BOOT_OFFSET),
        ]:
            data = (ASSETS / filename).read_bytes()
            if offset + len(data) > limit: raise ValueError('Loader overlaps next region')
            f.seek(offset)
            f.write(data)
    drive = f'{image}@@{BOOT_OFFSET}'
    for source, target in [
        (ASSETS / 'rk3288-firefly.dtb', '::/boot/rk3288-firefly.dtb'),
        (ASSETS / 'extlinux.conf', '::/extlinux/extlinux.conf'),
        (ASSETS / 'batocera.board', '::/boot/batocera.board'),
        (PACKAGE / 'collect-logs.sh', '::/collect-logs.sh'),
    ]:
        subprocess.run(['mcopy', '-o', '-i', drive, str(source), target], check=True)
    subprocess.run(['mdel', '-i', drive, '::/boot/rk3288-miqi.dtb'], check=True)
    # Verify both low-level loader copies and MBR after the filesystem edits.
    with image.open('rb') as f:
        if f.read(512) != mbr: raise ValueError('MBR changed')
        for filename, offset in [('idbloader.img', 32768), ('u-boot-dtb.img', 8388608)]:
            expected = (ASSETS / filename).read_bytes()
            f.seek(offset)
            if f.read(len(expected)) != expected: raise ValueError('Loader mismatch')
    print(f'Created {image} ({image.stat().st_size} bytes)', flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('official_base_gz', type=Path)
    p.add_argument('output_img', type=Path)
    a = p.parse_args()
    regular(a.official_base_gz)
    if a.output_img.exists() or a.output_img.is_symlink():
        p.error('Output must be a new file; refusing to overwrite')
    if not str(a.output_img).endswith('.img'): p.error('Output must end in .img')
    if sha256(a.official_base_gz) != BASE_SHA256: p.error('Base SHA-256 does not match')
    with gzip.open(a.official_base_gz, 'rb') as src, a.output_img.open('xb') as dst:
        shutil.copyfileobj(src, dst, 4 * 1024 * 1024)
    patch_image(a.output_img)
    print(sha256(a.output_img), a.output_img)

if __name__ == '__main__': main()
