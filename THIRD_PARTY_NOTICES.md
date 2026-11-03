# Third-party sources and licenses

本项目是原版 Firefly-RK3288 的 Batocera 板级适配工程。仓库根目录的 MIT 许可证只覆盖明确标记为本项目新增的独立脚本和项目文档，不替换下述上游文件的许可证。各文件内的 SPDX 标识、版权声明和上游许可证继续适用。

## 本项目新增内容

MIT 适用于 `make-image.py`、`package-rkdevtool.py`、`collect-logs.sh`、`build-boot-assets.sh`、`tools/*.py`、`source/write-boot-manifest.py`、`source/rebuild-u-boot.sh`、`source/build-dtb.sh`、`source/Dockerfile`、各版本 `extlinux.conf` 以及项目说明文档。Firefly wrapper DTS 继续使用文件头的双重许可；U-Boot 派生配置继续使用上游许可。

许可全文位于 `LICENSE` 和 `LICENSES/`。

## Batocera / Buildroot

- 基础二进制：`batocera-rk3288-miqi-39-20240301.img.gz`。
- 下载：[官方镜像镜像站目录](https://mirrors.o2switch.fr/batocera/miqi/stable/39/)。
- 固定源码参考：[9cbda965212c51ecebb4b79c2b77c91f55715bb7](https://github.com/batocera-linux/batocera.linux/tree/9cbda965212c51ecebb4b79c2b77c91f55715bb7)。
- 上游说明：[Batocera licenses](https://wiki.batocera.org/license)。
- [该版本 COPYING](https://github.com/batocera-linux/batocera.linux/blob/9cbda965212c51ecebb4b79c2b77c91f55715bb7/COPYING) 说明 Buildroot 的 GPL-2.0-or-later 许可及补丁例外。

Batocera 集成的内核、模拟器、系统库、固件、主题和媒体资源具有各自许可证，包括 GPL、LGPL、BSD、MIT 和带有非商业条件的许可。上游声明：Batocera 团队独立编写的代码通常使用 LGPLv3，继承自其他项目的代码继续受对应上游许可约束。

本仓库中的 Batocera DTS 补丁保持上游来源和被修改组件的许可。官方底包中的内核、initrd 和 SquashFS 系统由构建脚本保留，用户从指定官方来源获取该底包。

若另行发布完整系统二进制镜像，应同时提供所包含 GPL/LGPL 等组件要求的对应源码、修改、配置、构建资料和许可文本。本适配仓库及其源码包覆盖板级适配，不能替代整套发行版所有组件的对应源码。

## U-Boot v2024.01

- 源码：[U-Boot v2024.01](https://github.com/u-boot/u-boot/tree/v2024.01)。
- 构建配方：`source/rebuild-u-boot.sh`。
- 固定配置：`source/uboot.config`（SD）、`source/uboot-emmc.config`（eMMC）。
- 来源和产物校验值：`source/uboot-manifest.json`、`source/uboot-emmc-manifest.json`。
- [许可说明](https://github.com/u-boot/u-boot/blob/v2024.01/Licenses/README)。

U-Boot 主体为 GPLv2，许多文件允许使用后续版本；以各源文件声明为准。源码内的 `Licenses/` 包含许可全文与例外。Firefly loader 由未修改的 v2024.01 源码和本仓库公开配置构建。

## Linux v6.1.55 设备树及绑定头文件

- 来源：[Linux v6.1.55](https://github.com/gregkh/linux/tree/v6.1.55)。
- 原版板型：[rk3288-firefly.dts](https://github.com/gregkh/linux/blob/v6.1.55/arch/arm/boot/dts/rk3288-firefly.dts)。
- 板级公共描述：[rk3288-firefly.dtsi](https://github.com/gregkh/linux/blob/v6.1.55/arch/arm/boot/dts/rk3288-firefly.dtsi)。

`rk3288-firefly.dts`、`rk3288-firefly.dtsi` 及本项目 wrapper `source/rk3288-firefly-batocera.dts` 使用其文件头声明的 `GPL-2.0-or-later OR MIT` 双重许可。其余 SoC 描述和绑定头文件保留各自文件头许可，包括带 Linux syscall note 的 UAPI 头文件。

Firefly 原始 DTS 作者版权声明保留在源文件中。Batocera 补丁后的公共 DTS 及补丁记录位于 `source/linux-dts-batocera39/`、`source/dts-patch-audit/`。

## Rockchip USB 下载 Loader 与 Windows 工具

`tools/build-usb-loader.py` 从 [Rockchip 官方 rkbin 固定提交](https://github.com/rockchip-linux/rkbin/tree/3e288fe814e059dd06833495f845cab04ac20a5c) 下载 `RK3288MINIALL.ini`、DDR、usbplug、miniloader 和 `boot_merger`，核对 SHA-256，并保存该提交的 [LICENSE](https://github.com/rockchip-linux/rkbin/blob/3e288fe814e059dd06833495f845cab04ac20a5c/LICENSE)。生成包保留 `RKBIN-LICENSE.txt` 和来源清单；上游二进制不改用本项目 MIT 许可，也不提交到仓库。

RKDevTool 2.96 和 Rockchip Driver Assistant 由用户从厂商工具下载站另行取得，按各自许可使用，不包含在仓库中。CFG 格式依据 RKDevTool 2.96 实际配置文件、附带手册和格式检查实现。

## 项目名称和素材

Batocera、Firefly 及其他项目名称用于说明兼容目标和来源。各项目标识及素材的权利归其相应权利人所有。此适配工程未额外打包商业游戏或 BIOS。
