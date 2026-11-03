#!/bin/bash
# SPDX-License-Identifier: MIT
# firefly-rk3288-ap6335-boot-hook-v1
# S00bootcustom calls this before S05udev can load brcmfmac.
set -euo pipefail

[[ ${1:-} == start ]] || exit 0

fail() { echo "Firefly AP6335: $*" >&2; exit 1; }
boot_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
network_helper="$boot_dir/firefly-network-identity.sh"
if [[ -f $network_helper && ! -L $network_helper ]]; then
    if ! bash "$network_helper" start; then
        echo 'Firefly: Ethernet identity setup failed; continuing Wi-Fi setup' >&2
    fi
else
    echo 'Firefly: missing regular Ethernet identity helper; continuing Wi-Fi setup' >&2
fi
nvram="$boot_dir/firefly-wifi/nvram_AP6335.txt"
expected=9f6dbebb3f0b078831de6d0998e8bdbae421015beeabb22d3774f5c66b99a326
[[ -f $nvram && ! -L $nvram ]] || fail "missing regular NVRAM file: $nvram"
actual=$(sha256sum "$nvram")
[[ ${actual%% *} == "$expected" ]] || fail 'NVRAM checksum mismatch'

# The overrides support offline testing; normal boot uses the system paths.
firmware_dir=${FIREFLY_WIFI_FIRMWARE_DIR:-/lib/firmware/brcm}
target="$firmware_dir/brcmfmac4339-sdio.firefly,firefly-rk3288.txt"
[[ ! -L $target ]] || fail "refusing firmware symlink: $target"
mac=''
valid_mac() {
    local candidate=${1,,}
    [[ $candidate =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]] || return 1
    [[ $candidate != 00:00:00:00:00:00 && $candidate != ff:ff:ff:ff:ff:ff &&
       $candidate != 00:90:4c:c5:12:38 ]] || return 1
    (( (16#${candidate:0:2} & 1) == 0 ))
}
if [[ -e $target ]]; then
    [[ -f $target ]] || fail "not a regular firmware file: $target"
    # Keep custom calibration intact. Only our pinned NVRAM with a different
    # MAC is eligible for an idempotent update.
    cmp -s <(sed '/^macaddr=/d' "$nvram") <(sed '/^macaddr=/d' "$target") ||
        fail "existing board NVRAM differs; review it before replacing: $target"
    candidate=$(sed -n 's/^macaddr=//p' "$target")
    if valid_mac "$candidate"; then mac=${candidate,,}; fi
fi
if [[ -z $mac ]]; then
    serial_file=${FIREFLY_WIFI_SERIAL_FILE:-/proc/device-tree/serial-number}
    cpuinfo=${FIREFLY_WIFI_CPUINFO:-/proc/cpuinfo}
    serial=''
    if [[ -r $serial_file ]]; then serial=$(tr -d '\000\r\n' < "$serial_file"); fi
    if [[ ! $serial =~ ^[[:xdigit:]]{8,64}$ || $serial =~ ^0+$ ]]; then
        if [[ -r $cpuinfo ]]; then
            serial=$(awk 'tolower($1) == "serial" { print $3; exit }' "$cpuinfo")
        fi
    fi
    if [[ $serial =~ ^[[:xdigit:]]{8,64}$ && ! $serial =~ ^0+$ ]]; then
        identity="cpu-serial:${serial,,}"
    else
        # Some RK3288 kernels expose an all-zero CPU Serial. The original
        # board's internal eMMC offers a stable identifier even when that
        # happens. Do not take an SD/TF card's CID: it follows the card.
        mmc_sysfs=${FIREFLY_WIFI_MMC_SYSFS:-/sys/class/mmc_host}
        count=0
        cid=''
        for device in "$mmc_sysfs"/mmc*/mmc*:*; do
            [[ -r $device/type ]] || continue
            [[ $(< "$device/type") == MMC ]] || continue
            count=$((count + 1))
            [[ -r $device/cid ]] || fail "missing eMMC CID: $device"
            candidate=$(tr -d '[:space:]' < "$device/cid")
            [[ $candidate =~ ^[[:xdigit:]]{32}$ && ! $candidate =~ ^0+$ ]] ||
                fail "invalid eMMC CID: $device"
            cid=${candidate,,}
        done
        [[ $count == 1 ]] ||
            fail 'no unique CPU serial or unambiguous eMMC CID; refusing the vendor sample MAC'
        identity="emmc-cid:$cid"
    fi
    digest=$(printf 'firefly-rk3288-ap6335:%s' "$identity" | sha256sum)
    mac="02:${digest:0:2}:${digest:2:2}:${digest:4:2}:${digest:6:2}:${digest:8:2}"
fi
mkdir -p -- "$firmware_dir"
temporary=$(mktemp "$target.firefly.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
sed "s/^macaddr=.*/macaddr=$mac/" "$nvram" > "$temporary"
chmod 0644 "$temporary"
if [[ -f $target ]] && cmp -s "$temporary" "$target"; then
    rm -f -- "$temporary"
else
    mv -f -- "$temporary" "$target"
fi
trap - EXIT
echo "Firefly AP6335: installed board NVRAM with MAC $mac"
