#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BUILD_IMAGE=${FIREFLY_BUILD_IMAGE:-firefly-batocera-build:20261102}
VARIANT=${1:-sd}
case "$VARIANT" in
  sd) UBOOT_DIR=build; DTB=rk3288-firefly.dtb; ASSETS=boot-assets ;;
  emmc) UBOOT_DIR=build-emmc; DTB=rk3288-firefly-emmc.dtb; ASSETS=boot-assets/emmc ;;
  *) printf 'Usage: %s [sd|emmc]\n' "$0" >&2; exit 2 ;;
esac
cd "$TASK_DIR"
docker build -t "$BUILD_IMAGE" source
FIREFLY_BUILD_IMAGE="$BUILD_IMAGE" bash source/rebuild-u-boot.sh "$VARIANT"
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$TASK_DIR/source:/src" -w /src "$BUILD_IMAGE" sh build-dtb.sh "$VARIANT"
mkdir -p "$ASSETS"
install -m 0644 "source/$UBOOT_DIR/idbloader.img" "$ASSETS/idbloader.img"
install -m 0644 "source/$UBOOT_DIR/u-boot-dtb.img" "$ASSETS/u-boot-dtb.img"
install -m 0644 "source/$DTB" "$ASSETS/rk3288-firefly.dtb"
if [[ "$VARIANT" == emmc ]]; then
  install -m 0644 boot-assets/batocera.board "$ASSETS/batocera.board"
fi
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$TASK_DIR:/package" -w /package "$BUILD_IMAGE" \
  python3 source/write-boot-manifest.py "$VARIANT"
sha256sum "$ASSETS/idbloader.img" "$ASSETS/u-boot-dtb.img" "$ASSETS/rk3288-firefly.dtb"
