#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BUILD_IMAGE=${FIREFLY_BUILD_IMAGE:-firefly-batocera-build:20261102}
cd "$TASK_DIR"
docker build -t "$BUILD_IMAGE" source
FIREFLY_BUILD_IMAGE="$BUILD_IMAGE" bash source/rebuild-u-boot.sh
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$TASK_DIR/source:/src" -w /src "$BUILD_IMAGE" sh build-dtb.sh
install -m 0644 source/build/idbloader.img boot-assets/idbloader.img
install -m 0644 source/build/u-boot-dtb.img boot-assets/u-boot-dtb.img
install -m 0644 source/rk3288-firefly.dtb boot-assets/rk3288-firefly.dtb
sha256sum boot-assets/idbloader.img boot-assets/u-boot-dtb.img boot-assets/rk3288-firefly.dtb
