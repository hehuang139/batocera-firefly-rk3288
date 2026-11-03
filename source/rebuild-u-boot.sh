#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
# Run from any directory. No /dev device is read or written.
TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
IMAGE=${FIREFLY_BUILD_IMAGE:-firefly-batocera-build:20261102}
VARIANT=${1:-sd}
case "$VARIANT" in
  sd) BUILD_DIR=build; BOOT_TARGET=mmc1; LOCAL_VERSION=-firefly-sd1 ;;
  emmc) BUILD_DIR=build-emmc; BOOT_TARGET=mmc0; LOCAL_VERSION=-firefly-emmc1 ;;
  *) printf 'Usage: %s [sd|emmc]\n' "$0" >&2; exit 2 ;;
esac
ARCHIVE="$TASK_DIR/u-boot-v2024.01.tar.gz"
if [[ ! -f "$ARCHIVE" ]]; then
  curl -fL --retry 3 'https://codeload.github.com/u-boot/u-boot/tar.gz/refs/tags/v2024.01' -o "$ARCHIVE"
fi
(cd "$TASK_DIR" && printf '%s  %s\n' 'a03c3c2ba9d2bea5176c6406f1f3429a79e1147be242f5a07dbd9e89b3cc83c4' 'u-boot-v2024.01.tar.gz' | sha256sum -c -)
if [[ ! -d "$TASK_DIR/u-boot-2024.01" ]]; then
  tar -xzf "$ARCHIVE" -C "$TASK_DIR"
fi
docker run --rm --user "$(id -u):$(id -g)" \
  -e SOURCE_DATE_EPOCH=1704672000 \
  -e "FIREFLY_UBOOT_DIR=$BUILD_DIR" -e "FIREFLY_BOOT_TARGET=$BOOT_TARGET" \
  -e "FIREFLY_LOCAL_VERSION=$LOCAL_VERSION" \
  -v "$TASK_DIR:/build" -w /build/u-boot-2024.01 "$IMAGE" \
  bash -c '
    set -euo pipefail
    output="../$FIREFLY_UBOOT_DIR"
    make CROSS_COMPILE=arm-linux-gnueabihf- O="$output" firefly-rk3288_defconfig
    scripts/config --file "$output/.config" \
      --disable ENV_IS_IN_MMC --enable ENV_IS_NOWHERE \
      --disable SILENT_CONSOLE --enable BOOTSTD_FULL \
      --set-val BOOTDELAY 5 \
      --set-str BOOTCOMMAND "setenv boot_targets $FIREFLY_BOOT_TARGET; bootflow scan -lb" \
      --set-str LOCALVERSION "$FIREFLY_LOCAL_VERSION"
    make CROSS_COMPILE=arm-linux-gnueabihf- O="$output" olddefconfig
    make -j8 CROSS_COMPILE=arm-linux-gnueabihf- O="$output"
  '
sha256sum "$TASK_DIR/$BUILD_DIR/idbloader.img" "$TASK_DIR/$BUILD_DIR/u-boot-dtb.img" "$TASK_DIR/$BUILD_DIR/u-boot-rockchip.bin"
