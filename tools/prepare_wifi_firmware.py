#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Download and verify the pinned AP6335 NVRAM into a new boot-file bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

PACKAGE = Path(__file__).resolve().parents[1]
COMMIT = 'b61a1e8499a4f1956ef417cbcfaa6c2cf805ce08'
UPSTREAM = 'https://github.com/radxa/rkwifibt'
BASE_URL = f'https://raw.githubusercontent.com/radxa/rkwifibt/{COMMIT}'
FILES = {
    'nvram_AP6335.txt': {
        'url': f'{BASE_URL}/firmware/broadcom/AP6335/wifi/nvram_AP6335.txt',
        'sha256': '9f6dbebb3f0b078831de6d0998e8bdbae421015beeabb22d3774f5c66b99a326',
    },
    'LICENSE.rkwifibt': {
        'url': f'{BASE_URL}/LICENSE',
        'sha256': 'ec1dabfa95bf2e8f0de4311a9ceacfd841c45a772bf7eab3aa4c121284616df2',
    },
}
HOOK = PACKAGE / 'tools' / 'firefly-boot-custom.sh'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected a regular file: {path}')
    return path.read_bytes()


def prepare_bundle(destination):
    """Never overwrite a caller's files, including an existing custom hook."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    firmware = destination / 'firefly-wifi'
    firmware.mkdir()
    records = {}
    for name, record in FILES.items():
        with urllib.request.urlopen(record['url'], timeout=60) as response:
            data = response.read(1024 * 1024 + 1)
        if digest(data) != record['sha256']:
            raise ValueError(f'Pinned firmware checksum mismatch: {name}')
        (firmware / name).write_bytes(data)
        records[name] = dict(record, size_bytes=len(data))
    hook = read_regular(HOOK)
    (destination / 'boot-custom.sh').write_bytes(hook)
    manifest = {
        'board': 'firefly,firefly-rk3288', 'module': 'AP6335 / BCM4339',
        'upstream': UPSTREAM, 'commit': COMMIT,
        'upstream_import_commit': 'fe32b4846ce7fc14a73a9922e397b906fadd7868',
        'license': 'Upstream root LICENSE (Rockchip BSD-3-Clause); see THIRD_PARTY_NOTICES.md',
        'files': records, 'boot_hook_sha256': digest(hook),
        'target': '/lib/firmware/brcm/brcmfmac4339-sdio.firefly,firefly-rk3288.txt',
    }
    (firmware / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return validate_bundle(destination)


def validate_bundle(destination):
    destination = Path(destination)
    firmware = destination / 'firefly-wifi'
    manifest = json.loads(read_regular(firmware / 'manifest.json'))
    if (manifest.get('commit') != COMMIT or manifest.get('upstream') != UPSTREAM or
            manifest.get('board') != 'firefly,firefly-rk3288'):
        raise ValueError('Wi-Fi bundle is not for the pinned Firefly AP6335 source')
    for name, record in FILES.items():
        data = read_regular(firmware / name)
        entry = manifest['files'][name]
        if (digest(data) != record['sha256'] or entry.get('sha256') != record['sha256']
                or entry.get('url') != record['url'] or entry.get('size_bytes') != len(data)):
            raise ValueError(f'Wi-Fi bundle checksum/provenance mismatch: {name}')
    hook = read_regular(destination / 'boot-custom.sh')
    if hook != read_regular(HOOK) or manifest.get('boot_hook_sha256') != digest(hook):
        raise ValueError('Wi-Fi bundle boot hook differs from this recipe; prepare a fresh bundle')
    return manifest


def install_into_image(image, boot_offset, destination):
    """Install verified boot files, rejecting any unrelated existing hook/data."""
    destination = Path(destination)
    validate_bundle(destination)
    drive = f'{image}@@{boot_offset}'

    def entries(directory):
        listing = subprocess.check_output(['mdir', '-a', '-b', '-i', drive, directory], text=True)
        return {line.strip().rstrip('/').rsplit('/', 1)[-1].lower()
                for line in listing.splitlines() if line.strip()} - {'.', '..'}

    def read(target):
        return subprocess.check_output(['mtype', '-i', drive, target])

    root = entries('::/')
    hook_target = '::/boot-custom.sh'
    hook = destination / 'boot-custom.sh'
    if 'boot-custom.sh' in root and read(hook_target) != read_regular(hook):
        raise ValueError('Existing /boot/boot-custom.sh conflicts with the Firefly Wi-Fi hook')
    firmware_names = ('nvram_AP6335.txt', 'LICENSE.rkwifibt', 'manifest.json')
    if 'firefly-wifi' in root:
        existing = entries('::/firefly-wifi/')
        if existing - {name.lower() for name in firmware_names}:
            raise ValueError('Existing /boot/firefly-wifi has unrecognized files')
        for name in firmware_names:
            if (name.lower() in existing and
                    read(f'::/firefly-wifi/{name}') != read_regular(destination / 'firefly-wifi' / name)):
                raise ValueError(f'Existing /boot/firefly-wifi/{name} conflicts with the pinned bundle')
    else:
        subprocess.run(['mmd', '-i', drive, '::/firefly-wifi'], check=True)
    files = [(hook, hook_target)] + [
        (destination / 'firefly-wifi' / name, f'::/firefly-wifi/{name}') for name in firmware_names
    ]
    for source, target in files:
        subprocess.run(['mcopy', '-o', '-i', drive, str(source), target], check=True)
        if read(target) != read_regular(source):
            raise ValueError(f'Wi-Fi boot file verification failed: {target}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_directory', type=Path, help='New directory; existing paths are rejected')
    args = parser.parse_args()
    try:
        manifest = prepare_bundle(args.output_directory)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f'Prepared {args.output_directory.resolve()}')
    print(f'NVRAM SHA256: {manifest["files"]["nvram_AP6335.txt"]["sha256"]}')


if __name__ == '__main__':
    main()
