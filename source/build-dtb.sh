#!/bin/sh
# SPDX-License-Identifier: MIT
# Run in this directory with cpp + dtc installed (or inside the supplied Docker image).
set -eu
cd "$(dirname "$0")"
case "${1:-sd}" in
  sd) input=rk3288-firefly-batocera.dts; output=rk3288-firefly ;;
  emmc) input=rk3288-firefly-batocera-emmc.dts; output=rk3288-firefly-emmc ;;
  *) printf 'Usage: %s [sd|emmc]\n' "$0" >&2; exit 2 ;;
esac
cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I linux-dts-batocera39/include \
  -I linux-dts-batocera39/arch/arm/boot/dts \
  "$input" > "$output.preprocessed.dts"
dtc -I dts -O dtb -o "$output.dtb" "$output.preprocessed.dts"
