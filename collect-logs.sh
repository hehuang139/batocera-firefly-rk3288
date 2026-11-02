#!/bin/sh
# SPDX-License-Identifier: MIT
# Run on the board: sh /boot/collect-logs.sh
set -u
stamp=$(date +%Y%m%d-%H%M%S)
logdir="/userdata/system/firefly-diagnostics-$stamp"
mkdir -p "$logdir" || exit 1
{
  uname -a
  printf '\nBoard: '
  tr '\000' '\n' < /proc/device-tree/model
  printf '\nCommand line:\n'
  cat /proc/cmdline
  printf '\nBatocera:\n'
  cat /usr/share/batocera/batocera.version 2>/dev/null
  printf '\nStorage:\n'
  lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT
  mount
  printf '\nMemory:\n'
  free -m
  printf '\nDisplay connectors:\n'
  for node in /sys/class/drm/card*-*/status; do
    [ -f "$node" ] || continue
    printf '%s: ' "$node"
    cat "$node"
  done
  printf '\nAudio:\n'
  aplay -l
  printf '\nNetwork:\n'
  ip -brief address
} > "$logdir/system.txt" 2>&1
 dmesg > "$logdir/dmesg.txt" 2>&1
for name in es_log.txt es_launch_stdout.log es_launch_stderr.log; do
  [ ! -f "/userdata/system/configs/emulationstation/$name" ] || cp "/userdata/system/configs/emulationstation/$name" "$logdir/"
done
printf 'Logs saved to %s\n' "$logdir"
