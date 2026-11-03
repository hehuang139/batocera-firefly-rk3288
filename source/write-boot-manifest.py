#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record the selected build and its actual artifacts after compilation."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=['sd', 'emmc'])
    variant = parser.parse_args().variant
    assets = ROOT / 'boot-assets'
    build = ROOT / 'source/build'
    target, emmc_status = 'mmc1', 'disabled'
    if variant == 'emmc':
        assets = assets / 'emmc'
        build = ROOT / 'source/build-emmc'
        target, emmc_status = 'mmc0', 'okay'
    config = (build / '.config').read_text()
    if (f'CONFIG_BOOTCOMMAND="setenv boot_targets {target}; bootflow scan -lb"' not in config
            or 'CONFIG_ENV_IS_NOWHERE=y' not in config):
        raise ValueError('The actual U-Boot configuration does not match the requested variant')
    dtb_status = subprocess.check_output([
        'fdtget', '-t', 's', str(assets / 'rk3288-firefly.dtb'), '/mmc@ff0f0000', 'status'
    ], text=True).strip()
    if dtb_status != emmc_status:
        raise ValueError('The actual Linux DTB does not match the requested storage variant')
    artifacts = {}
    for name in ['idbloader.img', 'u-boot-dtb.img', 'rk3288-firefly.dtb', 'extlinux.conf', 'batocera.board']:
        path = assets / name
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError(f'Not an ordinary artifact file: {path}')
        artifacts[name] = {'size_bytes': path.stat().st_size,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {'schema_version': 1, 'variant': variant, 'image_size_bytes': 4848615424,
                'boot_targets': target, 'emmc_linux_status': emmc_status,
                'uboot_version': 'v2024.01', 'uboot_config_sha256': hashlib.sha256((build / '.config').read_bytes()).hexdigest(),
                'artifacts': artifacts}
    output = assets / 'manifest.json'
    output.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Wrote {output.relative_to(ROOT)} ({variant}, {target})')


if __name__ == '__main__':
    main()
