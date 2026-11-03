#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create RKDevTool 2.96 CFG files without accessing a device.

Input JSON: {"items": [{"name": "emmc-01", "path": "Image/emmc-01.img",
"address_sectors": 32768, "selected": true}]}.

The binary layout was checked against RKDevTool 2.96's own exported CFG.
Rows are 610 bytes: name at 2, path at 82, LBA at 602, selected DWORD at 606.
The path buffer also contains optional storage metadata: byte 597 == 'S',
followed by a little-endian storage DWORD at 598. It is deliberately cleared
here, leaving the current default storage selected. No storage switch is sent
for this default in the verified 2.96 download flow. The UI's Write by Address
option is separate and must still be enabled by the operator.
"""

import argparse
import json
from pathlib import Path, PureWindowsPath
import struct


HEADER_SIZE, ITEM_SIZE = 29, 610
# Vendor-format header: CFG, header size, SYSTEMTIME metadata, count, offset, size.
HEADER = bytes.fromhex("434647001d00e6070a0004001400100014002f005b00021d0000006202")
RESERVED = {"loader", "parameter", "uboot", "trust", "loadertoddr"}


def field(value, units, label):
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError(f"{label} must be a nonempty string without NUL")
    data = value.encode("utf-16-le")
    if len(data) >= units * 2:
        raise ValueError(f"{label} exceeds {units - 1} UTF-16 code units")
    return data.ljust(units * 2, b"\0")


def parse_cfg(data):
    if len(data) < HEADER_SIZE or data[:4] != b"CFG\0":
        raise ValueError("Not an RKDevTool CFG")
    count = data[22]
    if struct.unpack_from("<IH", data, 23) != (HEADER_SIZE, ITEM_SIZE):
        raise ValueError("Unsupported CFG header or row size")
    if len(data) != HEADER_SIZE + count * ITEM_SIZE:
        raise ValueError("CFG length does not match its header")
    rows = []
    for index in range(count):
        row = data[HEADER_SIZE + index * ITEM_SIZE:HEADER_SIZE + (index + 1) * ITEM_SIZE]
        if struct.unpack_from("<H", row)[0] != ITEM_SIZE:
            raise ValueError("Invalid CFG row size")
        address, selected = struct.unpack_from("<II", row, 602)
        if selected not in (0, 1):
            raise ValueError("Invalid CFG selected DWORD")
        rows.append({
            "name": row[2:82].decode("utf-16-le").split("\0", 1)[0],
            "path": row[82:602].decode("utf-16-le").split("\0", 1)[0],
            "address_sectors": address,
            "selected": bool(selected),
            "storage": struct.unpack_from("<I", row, 598)[0] if row[597] == 0x53 else 0,
        })
    return rows


def make_cfg(manifest, *, allow_loader_to_ddr=False):
    items = manifest.get("items") if isinstance(manifest, dict) else None
    if not isinstance(items, list) or not 1 <= len(items) <= 255:
        raise ValueError("Expected 1..255 CFG items")
    header = bytearray(HEADER)
    header[22] = len(items)
    output, expected, names = bytearray(header), [], set()
    for index, item in enumerate(items):
        name = item["name"]
        name_data = field(name, 40, "name")
        if name.lower() in RESERVED:
            if not (allow_loader_to_ddr and index == 0 and name == "LoaderToDDR"):
                raise ValueError(f"Reserved RKDevTool row name: {name}")
        if name.lower() in names:
            raise ValueError(f"Duplicate row name: {name}")
        names.add(name.lower())
        field(item["path"], 257, "path")
        path = item["path"].replace("/", "\\")
        if not PureWindowsPath(path).is_absolute() and not path.startswith(".\\"):
            path = ".\\" + path
        # At most 256 UTF-16 units plus NUL: never overlap storage at row 597.
        path_data = field(path, 257, "path").ljust(520, b"\0")
        address = item["address_sectors"]
        if isinstance(address, str):
            address = int(address, 0)
        if isinstance(address, bool) or not isinstance(address, int) or not 0 <= address <= 0xFFFFFFFF:
            raise ValueError("address_sectors must be a uint32 sector number")
        selected = item.get("selected", True)
        if not isinstance(selected, bool):
            raise ValueError("selected must be a JSON boolean")
        if item.get("storage", 0) != 0:
            raise ValueError("Only default storage=0 is supported; do not request a storage switch")
        row = struct.pack("<H", ITEM_SIZE) + name_data + path_data + struct.pack("<II", address, selected)
        if row[597:602] != bytes(5):
            raise ValueError("Path overlaps hidden storage metadata")
        output.extend(row)
        expected.append({"name": name, "path": path, "address_sectors": address,
                         "selected": selected, "storage": 0})
    if parse_cfg(output) != expected:
        raise ValueError("CFG round-trip verification failed")
    return bytes(output), expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-loader-to-ddr", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        data, expected = make_cfg(manifest, allow_loader_to_ddr=args.allow_loader_to_ddr)
        with args.output.open("xb") as stream:
            stream.write(data)
        if parse_cfg(args.output.read_bytes()) != expected:
            raise ValueError("Saved CFG verification failed")
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "items": expected}, indent=2))


if __name__ == "__main__":
    main()
