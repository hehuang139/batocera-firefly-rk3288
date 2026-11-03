#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Download pinned Rockchip inputs and merge an RK3288 USB LoaderToDDR file.

Requires Linux x86_64 to run Rockchip's prebuilt boot_merger. Output is a new
ordinary directory containing the loader, provenance, upstream license and
downloaded inputs. It does not access a board or install a bootloader. Generated
Rockchip binaries retain the upstream license; they are not covered by MIT.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import stat
import subprocess
import urllib.request


COMMIT = "3e288fe814e059dd06833495f845cab04ac20a5c"
URL = f"https://raw.githubusercontent.com/rockchip-linux/rkbin/{COMMIT}/"
INPUTS = {
    "RKBOOT/RK3288MINIALL.ini": "182d4c869c4af0aef6972278bd2fd2e807ed89c08587bf349f677781eb1ed673",
    "bin/rk32/rk3288_ddr_400MHz_v1.12.bin": "6e9241e09aa6a12be37df5088e0efa1554f8ae6827939925b1aeba5b2e433d55",
    "bin/rk32/rk3288_usbplug_v2.63.bin": "5e36a42499c4f9568234f076214d70c5e9cd047171a2262ad85c746cd76da743",
    "bin/rk32/rk3288_miniloader_v2.63.bin": "af23cd7259d4fb06965b3d661525ce0aff8c29c0fef0d3c8af227f50e228f92b",
    "tools/boot_merger": "f8e1a2d01bc475e9571ab0aec00e4cca3d85bbd4587f3873970560443a237d0c",
}
LICENSE_SHA256 = "1b3cfbd212ef0e645b34aa6beee07343ce954a4f512338f12317ab297a9c9829"
LOADER = "rk3288_loader_v1.12.263.bin"


def download(path, relative, wanted):
    request = urllib.request.Request(URL + relative, headers={"User-Agent": "firefly-rk3288-builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != wanted:
        raise ValueError(f"Download SHA-256 mismatch: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)


def build(output):
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("Rockchip boot_merger requires a Linux x86_64 host")
    output.mkdir(parents=False, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    for relative, wanted in INPUTS.items():
        print(f"Downloading {relative}", flush=True)
        download(inputs / relative, relative, wanted)
    download(output / "RKBIN-LICENSE.txt", "LICENSE", LICENSE_SHA256)
    merger = inputs / "tools/boot_merger"
    merger.chmod(0o755)
    subprocess.run([str(merger.resolve()), "RKBOOT/RK3288MINIALL.ini"], cwd=inputs, check=True)
    generated = inputs / LOADER
    if generated.is_symlink() or not stat.S_ISREG(generated.stat().st_mode):
        raise ValueError("boot_merger did not create an ordinary loader file")
    data = generated.read_bytes()
    if len(data) != 209230:
        raise ValueError("Unexpected RK3288 loader length")
    with (output / LOADER).open("xb") as destination:
        destination.write(data)
    provenance = {
        "rkbin_commit": COMMIT,
        "inputs": [{"path": path, "url": URL + path, "sha256": sha}
                   for path, sha in INPUTS.items()],
        "license": {"path": "RKBIN-LICENSE.txt", "url": URL + "LICENSE",
                    "sha256": LICENSE_SHA256},
        "output": {"name": LOADER, "size_bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest(),
                   "use": "USB LoaderToDDR to RAM only; not a raw eMMC image"},
    }
    (output / "usb-loader-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                                       encoding="utf-8")
    print(json.dumps(provenance["output"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path, help="new directory; its parent must exist")
    args = parser.parse_args()
    try:
        build(args.output_directory)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
