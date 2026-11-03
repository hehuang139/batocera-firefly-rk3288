# 构建与来源

## 系统来源

基础文件：`batocera-rk3288-miqi-39-20240301.img.gz`，1,626,041,381 字节。

下载地址：
https://mirrors.o2switch.fr/batocera/miqi/stable/last/batocera-rk3288-miqi-39-20240301.img.gz

固定 SHA-256：
`4280732daf9fb32ee59f56f727134c5a5e5c8a2b64add593a5e8e50c78654a01`

基础系统源码：[Batocera 提交 9cbda965212c51ecebb4b79c2b77c91f55715bb7](https://github.com/batocera-linux/batocera.linux/tree/9cbda965212c51ecebb4b79c2b77c91f55715bb7)。

## 编译引导和设备树

需要 Linux、Docker；完整构建和分段打包建议预留约 20 GB。仓库包含 U-Boot 配方、完整配置、DTS 依赖、Batocera DTS 补丁和哈希。脚本下载固定的 U-Boot v2024.01 源码并校验 SHA-256；上游 U-Boot 源码未修改。

在仓库根目录执行：

```sh
./build-boot-assets.sh emmc
```

顶层脚本创建 Docker 工具环境，运行 `source/rebuild-u-boot.sh emmc` 和 `source/build-dtb.sh emmc`，将引导文件及 `manifest.json` 写入 `boot-assets/emmc/`。`source/build-emmc/` 保留 U-Boot 编译产物。`source/uboot-emmc.config` 与 `source/uboot-emmc-manifest.json` 是历史成功启动版本的 U-Boot 配置和产物记录，不包含当前 Linux Wi-Fi DTB；本次生成文件以 `boot-assets/emmc/manifest.json` 中的实际哈希为准。

SD 实验版本使用 `./build-boot-assets.sh sd`，产物位于 `source/build/`、`boot-assets/`。不传参数时保持 SD 默认行为。两个版本的构建目录和清单独立；组装脚本核对版本、U-Boot 目标、DTB 和各产物哈希，拒绝混用。

DTS 使用 Linux v6.1.55 依赖树，按顺序应用 Batocera 的七个相关补丁。省略 CPU 1.8 GHz/boost 补丁，保留上游 1.608 GHz 上限。`source/dts-patch-audit/` 保存补丁和来源；`linux-event-codes.h` 保存符号链接所指向的实际头文件内容，便于源码归档和跨平台处理。

Dockerfile 使用 Ubuntu 22.04 和 apt 软件包。工具链版本可能随更新变化，历史清单的二进制哈希对应当次环境，不要求未来工具链生成的文件逐字节相同。

## 组装整盘镜像

把官方压缩镜像放到仓库根目录，执行：

```sh
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py --variant emmc \
  batocera-rk3288-miqi-39-20240301.img.gz emmc.img
```

脚本核对引导清单、DTB 的 eMMC 状态和基础 SHA-256，输出新的普通 `.img` 及 `.img.manifest.json`，拒绝覆盖已有路径，不接受块设备。保留官方内核、initrd、SquashFS 和 SHARE 分区，替换引导区、DTB、extlinux、板型标识，加入日志脚本。

组装时默认在临时目录下载固定来源的 AP6335 NVRAM 和许可证，校验哈希后将 `boot-custom.sh` 与 `firefly-wifi/` 加入 FAT 启动分区。早期脚本在 udev 之前安装板级 NVRAM，来源及实际哈希另记入镜像旁清单的 `wifi_firmware` 字段。启动机制、MAC 处理和实际验证范围见 [Wi-Fi 修复与验证](WIFI.md)。

如需复用已下载文件或离线组装，先在联网环境准备新目录，再把它传给组装脚本；脚本仍会核验文件包与当前准备器是否匹配：

```sh
python3 tools/prepare_wifi_firmware.py out/wifi-firmware
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py --variant emmc --wifi-firmware out/wifi-firmware \
  batocera-rk3288-miqi-39-20240301.img.gz emmc.img
```

上述准备命令只生成普通文件包，不会写入开发板。现有系统如已有自定义 `boot-custom.sh`，更新时应先合并原有逻辑，不要直接覆盖。

SD 镜像将参数改为 `--variant sd`，并使用不同输出文件名。可用 `gzip -1 -n sd.img` 压缩后交给写卡工具；RKDevTool 打包需要未压缩的 eMMC `.img`。

Wi-Fi 的现场验证仅针对 eMMC 安装。SD 版本禁用 eMMC，在 CPU / 设备树序列号缺失或全零时，没有可用的 eMMC CID 回退，开机脚本会拒绝生成备用 MAC；不能把两种 DTS 均编译通过等同于 SD Wi-Fi 已验证。

布局（每扇区 512 字节）：

| 内容 | 偏移 / 起始扇区 | 大小 |
| --- | --- | --- |
| MBR | 0 | 512 字节 |
| Firefly idbloader | 32 KiB / 64 | 63,488 字节 |
| Firefly u-boot-dtb.img | 8 MiB / 16,384 | 历史测试 eMMC 554,696 字节；SD 554,688 字节，以当前清单为准 |
| BATOCERA FAT32 | 16 MiB / 32,768 | 4 GiB 分区 |
| SHARE ext4 | 4,311,744,512 / 8,421,376 | 初始 512 MiB，首启扩容 |

完整 `.img` 为 4,848,615,424 字节。原 MiQi loader 和持久环境区域在写入 Firefly loader 前清零。新 U-Boot 使用内存环境；自己的设备树中 eMMC 为 `mmc0`、SD 为 `mmc1`，不可套用于未知旧 U-Boot。

不同 mtools 写入时间会改变整盘镜像哈希。`source/uboot*-manifest.json` 和 [测试记录](TESTING.md) 中的值用于识别相应历史产物；当前引导与 Linux DTB 使用新生成的 `boot-assets[/emmc]/manifest.json`，整盘镜像使用旁边的 `.img.manifest.json`。Wi-Fi 修复后的 DTB 有意改变，不应要求它与修复前文件逐字节相同。

## 生成 RKDevTool 分段包

以下步骤需要 Linux x86_64、Python 3，以及前述 Docker 工具环境。

```sh
mkdir -p out
python3 tools/build-usb-loader.py out/usb-loader

docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 package-rkdevtool.py emmc.img out/rkdevtool \
  --usb-loader out/usb-loader/rk3288_loader_v1.12.263.bin
```

USB Loader 来自 Rockchip `rkbin` 固定提交 `3e288fe814e059dd06833495f845cab04ac20a5c`，由 DDR、usbplug、miniloader 和 `boot_merger` 合成。脚本核验全部输入哈希，保存来源和原许可。它用于 MaskROM 阶段的 `LoaderToDDR`，不同于写入 eMMC 的主线 `idbloader.img`。输出目录必须是新目录。

分段脚本核验完整镜像的 MBR、引导偏移、设备树及启动文件，生成四段 1 GiB、SHARE 512 MiB、头部 16 MiB。按物理偏移重组后的 SHA-256 必须与输入一致。同时生成两份 CFG、`parts-manifest.json` 和 `SHA256SUMS`。配置保持存储字段为空，头部最后写入。脚本只读写普通文件，不访问设备。

从 [Radxa 工具目录](https://dl.radxa.com/tools/windows/) 获取 RKDevTool 2.96 和 Driver Assistant 5.14，将 `out/rkdevtool/` 内的 `Image/` 和 CFG 放到 RKDevTool.exe 所在目录，按 [eMMC 烧录说明](FLASHING-EMMC.md) 操作。输出不是 RKFW `update.img`，不用于“升级固件”。Windows 工具不随仓库分发。

2026-11-04，两种引导和 Wi-Fi 修正版 DTS 均编译通过；含早期 NVRAM 安装及 MMC CID 回退的 eMMC 整盘镜像已完成组装、FAT 回读和 RKDevTool 六段重组校验，完整镜像与重组 SHA-256 一致。现场在历史 `emmc-test1` 安装上部署相同 DTB 和早期文件，已通过一次软件重启后的 NVRAM 自动安装、无线枚举、扫描和系统网络列表验证。新整盘镜像尚未另行完整烧录上板。历史构建、哈希与实测范围见 [测试记录](TESTING.md)。
