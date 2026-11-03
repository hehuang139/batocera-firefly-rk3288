#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Split a verified eMMC image into an RKDevTool raw-download file package.

Requires mtools (mtype) and device-tree-compiler (fdtget), available in the
project's Docker image. Only ordinary files are accepted. A new output directory
is required; no USB device, block device, or Windows executable is accessed.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import struct
import subprocess

from tools.make_rkdev_cfg import make_cfg, parse_cfg


PACKAGE = Path(__file__).resolve().parent
IMAGE_SIZE = 4848615424
BOOT_OFFSET = 16 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024 * 1024
BUFFER_SIZE = 8 * 1024 * 1024
ASSET_NAMES = ("idbloader.img", "u-boot-dtb.img", "rk3288-firefly.dtb",
               "extlinux.conf", "batocera.board")


def regular(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Only an ordinary file is accepted: {path}")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(BUFFER_SIZE), b""):
            h.update(data)
    return h.hexdigest()


def validate_image(image, assets):
    regular(image)
    if image.suffix != ".img" or image.stat().st_size != IMAGE_SIZE:
        raise ValueError(f"Expected an uncompressed {IMAGE_SIZE}-byte .img file")
    manifest_path = assets / "manifest.json"
    regular(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("variant"), manifest.get("boot_targets"), manifest.get("image_size_bytes")) != (
            "emmc", "mmc0", IMAGE_SIZE):
        raise ValueError("Boot assets must describe the eMMC/mmc0 variant")
    contents = {}
    for name in ASSET_NAMES:
        path = assets / name
        regular(path)
        data = path.read_bytes()
        record = manifest["artifacts"][name]
        if len(data) != record["size_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Boot asset manifest mismatch: {name}")
        contents[name] = data
    with image.open("rb") as stream:
        mbr = stream.read(512)
        if mbr[510:512] != b"\x55\xaa":
            raise ValueError("Invalid MBR signature")
        for index, wanted in enumerate(((12, 32768, 8388608), (131, 8421376, 1048576))):
            record = struct.unpack_from("<B3sB3sII", mbr, 446 + index * 16)
            if (record[2], record[4], record[5]) != wanted:
                raise ValueError("Unexpected MBR partition layout")
        if mbr[478:510] != bytes(32) or (8421376 + 1048576) * 512 != IMAGE_SIZE:
            raise ValueError("Unexpected additional partition or image bounds")
        for name, offset, limit in (("idbloader.img", 32768, 8388608),
                                    ("u-boot-dtb.img", 8388608, BOOT_OFFSET)):
            expected = contents[name]
            if not expected or offset + len(expected) > limit:
                raise ValueError(f"Boot asset exceeds its reserved region: {name}")
            stream.seek(offset)
            if stream.read(len(expected)) != expected:
                raise ValueError(f"Image does not contain the expected eMMC {name}")
    if b"setenv boot_targets mmc0; bootflow scan -lb" not in contents["u-boot-dtb.img"]:
        raise ValueError("U-Boot does not contain the expected mmc0 boot command")
    drive = f"{image.resolve()}@@{BOOT_OFFSET}"
    for name, target in (("rk3288-firefly.dtb", "::/boot/rk3288-firefly.dtb"),
                         ("extlinux.conf", "::/extlinux/extlinux.conf"),
                         ("batocera.board", "::/boot/batocera.board")):
        data = subprocess.check_output(["mtype", "-i", drive, target])
        if data != contents[name]:
            raise ValueError(f"Image FAT file differs from the eMMC boot asset: {name}")
    dtb = str((assets / "rk3288-firefly.dtb").resolve())
    compatible = subprocess.check_output(["fdtget", "-t", "s", dtb, "/", "compatible"],
                                         text=True).split()
    status = subprocess.check_output(["fdtget", "-t", "s", dtb, "/mmc@ff0f0000", "status"],
                                     text=True).strip()
    if "firefly,firefly-rk3288" not in compatible or status != "okay":
        raise ValueError("Device tree must target original Firefly-RK3288 with eMMC enabled")
    if b"label=BATOCERA" not in contents["extlinux.conf"]:
        raise ValueError("Unexpected extlinux root filesystem configuration")
    return manifest


def usb_contract():
    spec = importlib.util.spec_from_file_location("usb_loader_contract", PACKAGE / "tools/build-usb-loader.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_usb_loader(loader):
    contract = usb_contract()
    regular(loader)
    provenance_path = loader.parent / "usb-loader-provenance.json"
    license_path = loader.parent / "RKBIN-LICENSE.txt"
    regular(provenance_path)
    regular(license_path)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    inputs = {record["path"]: record["sha256"] for record in provenance["inputs"]}
    if provenance.get("rkbin_commit") != contract.COMMIT or inputs != contract.INPUTS:
        raise ValueError("USB loader provenance does not match the pinned Rockchip inputs")
    record = provenance["output"]
    if (loader.name != contract.LOADER or record["name"] != contract.LOADER
            or loader.stat().st_size != 209230 or record["size_bytes"] != 209230
            or digest(loader) != record["sha256"]):
        raise ValueError("USB loader does not match its recorded output SHA-256/size")
    if digest(license_path) != contract.LICENSE_SHA256:
        raise ValueError("Missing or modified upstream Rockchip license")
    return provenance


def part_ranges():
    """Execution order: four FAT slices, SHARE, then the first 16 MiB."""
    ranges = [(f"emmc-{index + 1:02d}", BOOT_OFFSET + index * CHUNK_SIZE, CHUNK_SIZE)
              for index in range(4)]
    return ranges + [("emmc-05", BOOT_OFFSET + 4 * CHUNK_SIZE, 512 * 1024 * 1024),
                     ("emmc-header-last", 0, BOOT_OFFSET)]


def copy_extent(source, destination, offset, length):
    source.seek(offset)
    h = hashlib.sha256()
    with destination.open("xb") as output:
        while length:
            data = source.read(min(length, BUFFER_SIZE))
            if not data:
                raise ValueError("Unexpected EOF while splitting image")
            output.write(data)
            h.update(data)
            length -= len(data)
    return h.hexdigest()


def verify_parts(directory, parts, image_sha256):
    h, position = hashlib.sha256(), 0
    for part in sorted(parts, key=lambda item: item["offset_bytes"]):
        if part["offset_bytes"] != position or part["address_sectors"] * 512 != position:
            raise ValueError("Split image has a hole, overlap, or wrong LBA")
        path = directory / part["path"]
        regular(path)
        if path.stat().st_size != part["size_bytes"] or digest(path) != part["sha256"]:
            raise ValueError("Split image file size/SHA-256 mismatch")
        with path.open("rb") as stream:
            for data in iter(lambda: stream.read(BUFFER_SIZE), b""):
                h.update(data)
        position += part["size_bytes"]
    if position != IMAGE_SIZE or h.hexdigest() != image_sha256:
        raise ValueError("Reassembled SHA-256 differs from the complete image")
    return h.hexdigest()


def package_image(image, output, loader, assets):
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a new directory; refusing to overwrite")
    assets_manifest = validate_image(image, assets)
    provenance = validate_usb_loader(loader)
    source_sha256 = digest(image)
    output.mkdir(parents=False, exist_ok=False)
    images = output / "Image"
    images.mkdir()
    shutil.copyfile(loader, images / loader.name)
    for name in ("usb-loader-provenance.json", "RKBIN-LICENSE.txt"):
        shutil.copyfile(loader.parent / name, output / name)
    parts = []
    with image.open("rb") as source:
        for name, offset, length in part_ranges():
            path = images / f"{name}.img"
            part_hash = copy_extent(source, path, offset, length)
            parts.append({"name": name, "path": f"Image/{path.name}",
                          "address_sectors": offset // 512, "address_hex": f"0x{offset // 512:08X}",
                          "offset_bytes": offset, "size_bytes": length, "sha256": part_hash,
                          "selected": True, "storage": 0})
            print(f"Created {path.name}: LBA {offset // 512:#x}, {length} bytes", flush=True)
    reassembled = verify_parts(output, parts, source_sha256)
    loader_item = {"name": "LoaderToDDR", "path": f"Image/{loader.name}",
                   "address_sectors": 0, "selected": True, "storage": 0}
    for name, items in (("01-usb-loader-ram.cfg", [loader_item]),
                        ("02-emmc-write.cfg", [dict(loader_item, selected=False)] + parts)):
        data, expected = make_cfg({"items": items}, allow_loader_to_ddr=True)
        target = output / name
        with target.open("xb") as stream:
            stream.write(data)
        if parse_cfg(target.read_bytes()) != expected:
            raise ValueError("Saved download CFG verification failed")
    records = {"variant": "emmc", "raw_image": image.name, "size_bytes": IMAGE_SIZE,
               "sha256": source_sha256, "reassembled_sha256": reassembled,
               "target_minimum_capacity_bytes": IMAGE_SIZE, "boot_assets": assets_manifest,
               "usb_loader": provenance["output"], "items": parts,
               "device_write_performed": False}
    (output / "parts-manifest.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    (output / "README.txt").write_text(
        "Original Firefly-RK3288 eMMC raw-download package; not an RKFW update.img.\n"
        "Obtain RKDevTool 2.96 separately; copy this package's CFG and Image directory into its program directory.\n"
        "Follow docs/FLASHING-EMMC.md. In MaskROM, stage 01 uses LoaderToDDR to RAM only.\n"
        "Before stage 02, remove TF, read FlashID/FlashInfo and confirm default EMMC and sufficient capacity.\n"
        "Keep Storage blank, enable Write by Address, keep LoaderToDDR unchecked, write all six raw rows once.\n"
        "The 16 MiB header is last. Do not select persistent Loader, parameter, uboot or trust rows.\n"
        "Disable RESET_AFTER_DOWNLOAD while staging. Save logs; file hashes do not prove device readback.\n"
        "Windows tools and drivers are not included. Generated Rockchip USB binaries retain RKBIN-LICENSE.txt.\n",
        encoding="utf-8")
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text("".join(
        f"{digest(path)}  {path.relative_to(output).as_posix()}\n" for path in files), encoding="utf-8")
    print(f"Verified package: {output}\nReassembled SHA-256: {reassembled}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output_directory", type=Path, help="new directory; its parent must exist")
    parser.add_argument("--usb-loader", type=Path, required=True,
                        help="loader with sibling provenance/license from tools/build-usb-loader.py")
    parser.add_argument("--boot-assets", type=Path, default=PACKAGE / "boot-assets/emmc")
    args = parser.parse_args()
    try:
        package_image(args.image, args.output_directory, args.usb_loader, args.boot_assets)
    except (KeyError, OSError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
