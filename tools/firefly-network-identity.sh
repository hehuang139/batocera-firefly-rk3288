#!/bin/bash
# SPDX-License-Identifier: MIT
# Set a stable board-specific Ethernet MAC before ConnMan starts.
set -euo pipefail

fail() { echo "Firefly Ethernet identity: $*" >&2; exit 1; }
action=${1:-}
case "$action" in start|print-identity) ;; *) fail 'expected start or print-identity' ;; esac

serial_file=${FIREFLY_NETWORK_SERIAL_FILE:-/proc/device-tree/serial-number}
cpuinfo=${FIREFLY_NETWORK_CPUINFO:-/proc/cpuinfo}
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
    mmc_sysfs=${FIREFLY_NETWORK_MMC_SYSFS:-/sys/class/mmc_host}
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
    [[ $count == 1 ]] || fail 'no unique CPU serial or unambiguous eMMC CID'
    identity="emmc-cid:$cid"
fi
board_id=$(printf 'firefly-rk3288-board:%s' "$identity" | sha256sum)
board_id=${board_id%% *}
if [[ $action == print-identity ]]; then
    printf '%s\n' "$board_id"
    exit 0
fi

digest=$(printf 'firefly-rk3288-ethernet:%s' "$identity" | sha256sum)
mac="02:${digest:0:2}:${digest:2:2}:${digest:4:2}:${digest:6:2}:${digest:8:2}"
boot_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
configuration=${FIREFLY_NETWORK_CONF:-$boot_dir/firefly-network.conf}
[[ ! -L $configuration ]] || fail "refusing configuration symlink: $configuration"
if [[ -e $configuration ]]; then
    [[ -f $configuration ]] || fail "not a regular configuration file: $configuration"
    configured_id=''
    configured_mac=''
    while IFS= read -r line || [[ -n $line ]]; do
        line=${line%$'\r'}
        case "$line" in ''|'#'*) continue ;; esac
        if [[ $line =~ ^board_id=([[:xdigit:]]{64})$ && -z $configured_id ]]; then
            configured_id=${BASH_REMATCH[1],,}
        elif [[ $line =~ ^ethernet_mac=(([[:xdigit:]]{2}:){5}[[:xdigit:]]{2})$ && -z $configured_mac ]]; then
            configured_mac=${BASH_REMATCH[1],,}
        else
            fail "invalid or duplicate configuration entry: $configuration"
        fi
    done < "$configuration"
    [[ $configured_id == "$board_id" ]] || fail 'configuration belongs to another board or lacks board_id'
    [[ -n $configured_mac && $configured_mac != 00:00:00:00:00:00 &&
       $configured_mac != ff:ff:ff:ff:ff:ff ]] || fail 'invalid configured Ethernet MAC'
    (( (16#${configured_mac:0:2} & 1) == 0 )) || fail 'multicast Ethernet MAC is not allowed'
    mac=$configured_mac
fi

net_sysfs=${FIREFLY_NETWORK_NET_SYSFS:-/sys/class/net}
interface="$net_sysfs/eth0"
[[ -r $interface/address && -r $interface/flags ]] || fail 'eth0 is not available before ConnMan'
current=$(< "$interface/address")
if [[ ${current,,} == "$mac" ]]; then
    echo "Firefly Ethernet identity: eth0 already uses $mac"
    exit 0
fi
flags=$(< "$interface/flags")
[[ $flags =~ ^0x[[:xdigit:]]+$ ]] || fail 'cannot determine eth0 administrative state'
(( (flags & 1) == 0 )) || fail 'eth0 is already up; refusing to interrupt the link'
proc_root=${FIREFLY_NETWORK_PROC_ROOT:-/proc}
for comm in "$proc_root"/[0-9]*/comm; do
    if [[ -r $comm ]] && IFS= read -r process < "$comm"; then
        [[ $process != connmand ]] || fail 'ConnMan is already running; refusing to change eth0 MAC'
    fi
done
ip link set dev eth0 address "$mac"
current=$(< "$interface/address")
[[ ${current,,} == "$mac" ]] || fail 'Ethernet MAC readback differs after setting it'
echo "Firefly Ethernet identity: eth0 uses $mac"
