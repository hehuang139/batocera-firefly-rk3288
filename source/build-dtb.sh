#!/bin/sh
# SPDX-License-Identifier: MIT
# Run in this directory with cpp + dtc installed (or inside the supplied Docker image).
set -eu
cd "$(dirname "$0")"
cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I linux-dts-batocera39/include \
  -I linux-dts-batocera39/arch/arm/boot/dts \
  rk3288-firefly-batocera.dts > rk3288-firefly.preprocessed.dts
dtc -I dts -O dtb -o rk3288-firefly.dtb rk3288-firefly.preprocessed.dts
