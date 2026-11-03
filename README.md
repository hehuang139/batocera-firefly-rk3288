# Batocera for Firefly-RK3288

原版 **Firefly-RK3288** 的 Batocera 39 社区适配工程。**2026-11-04，用户已确认板载 eMMC 镜像启动成功、手柄可用**；当前以 eMMC 为主要验证入口，保留 microSD/TF 卡实验流程。

本项目复用官方 Batocera 39 MiQi 镜像的 RK3288 内核和系统文件，提供 Firefly 专用 U-Boot 配置、设备树、补丁及镜像组装脚本。适用板卡为上游设备树中的 `firefly,firefly-rk3288`；Firefly-RK3288 Reload 使用不同设备树。

## 当前状态

已完成 U-Boot 和设备树编译、镜像组装及文件检查，并在一块原版 Firefly-RK3288 上完成 eMMC 启动验证。该板原系统为 Linux；先前 TF 卡尝试仍进入原 Linux，尚未确认原因，不能据此认定原版 Firefly 不支持 TF 启动。

用户报告手柄可用，尚未提供型号、接口和游戏内测试细节。现场已通过有线 SSH 验证网络可用，并确认 SHARE 分区已扩容至约 10.5 GiB。修正 SDIO 设备树、补充 AP6335 板级 NVRAM 并加入有线身份更新后，已验证**一次软件重启后的 Wi-Fi 自动关联、DHCP IPv4 和无线 SSH**。频段覆盖、传输速度及长期稳定性尚未验证，详见 [Wi-Fi 修复与验证](docs/WIFI.md)。其他外设、游戏、音频和游戏文件网络传输尚未单独验证，详见 [测试记录](docs/TESTING.md)。添加游戏的方法见 [传输游戏与 BIOS](docs/TRANSFER-GAMES.md)，退出游戏等操作见 [手柄操作](docs/CONTROLS.md)。

本仓库提供适配源码、构建配方、启动配置和分段烧录包生成脚本；完整镜像需要从官方基础镜像自行组装。目前没有发布可下载的整盘镜像，也不随仓库分发 Windows 烧录工具 EXE。系统根文件中的各软件组件由其各自上游维护。

开机流程已加入稳定有线 MAC 的辅助脚本，并在一次软件重启后确认有线和无线 MAC 与部署前一致。当时网线未连接，尚未验证更新后的有线 DHCP。固定 MAC 与固定 IP 是两项配置：两种接口需分别设置 DHCP 地址保留，目前尚未完成，见 [网络地址说明](docs/WIFI.md#有线与无线-ip)。

## 版本与改动

| 部分 | 来源 / 配置 |
| --- | --- |
| 基础系统 | Batocera 39，MiQi，2024-03-01 |
| Linux | 官方镜像内的 6.1.55，Panfrost GPU 驱动 |
| U-Boot | v2024.01，`firefly-rk3288_defconfig`，内存环境 |
| 设备树 | Linux v6.1.55 Firefly DTS，加 Batocera RK3288 相关 DTS 补丁 |
| 显示与音频配置 | HDMI、I2S、HDMI simple-audio-card；完整功能仍待测试 |
| eMMC 版本 | U-Boot 扫描 `mmc0`；Linux 启用 eMMC 与 SD；已确认启动 |
| SD 实验版本 | U-Boot 扫描 `mmc1`；Linux 禁用 eMMC；启动及 Wi-Fi 均未验证 |
| CPU | 保留上游最高 1.608 GHz 配置 |

上述 `mmc0` / `mmc1` 是本项目主线 U-Boot 的设备树别名，不能套用到板上未知的旧 U-Boot。启动分区板型标识为 `firefly-rk3288`，避免自动匹配 MiQi 的系统更新。

## 构建 eMMC 镜像

需要 Linux、Docker 和足够的构建、镜像及分段文件空间。先按 [构建说明](docs/BUILD.md) 下载并校验指定官方基础镜像，再在仓库根目录执行：

```sh
./build-boot-assets.sh emmc
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py --variant emmc \
  batocera-rk3288-miqi-39-20240301.img.gz emmc.img
```

生成的是普通整盘 `.img`，不是 Rockchip RKFW `update.img`。eMMC 写入使用 RKDevTool 2.96 的“下载镜像”和分段地址配置，详见 [eMMC 烧录步骤](docs/FLASHING-EMMC.md)。写入会覆盖板载原系统与用户分区，请先备份需要保留的数据。

组装脚本默认下载并校验固定来源的 AP6335 NVRAM，加入开机早期安装流程；离线构建可先准备文件包，再通过 `--wifi-firmware` 指定，见 [Wi-Fi 说明](docs/WIFI.md)。

本次验证的旧 Loader 版本为 `2.3a`。手动选择 EMMC 会报“Loader不支持切换”；成功流程先读取 FlashID 和 Flash 信息确认默认介质，再将各行“存储”列留空写入。不要跳过介质和容量检查。

## SD 实验流程

SD 版本构建方法见 [构建说明](docs/BUILD.md)，通过 `./build-boot-assets.sh sd` 和 `make-image.py --variant sd ...` 选择。不要将两个版本的引导产物混用。

本次 Wi-Fi 修复验证仅覆盖 eMMC 安装。SD 版本禁用了 eMMC；若该板也没有有效 CPU / 设备树序列号，开机脚本无法取得备用 MAC 标识，会拒绝安装 NVRAM，详见 [Wi-Fi 验证范围](docs/WIFI.md)。

1. 用 balenaEtcher 把 SD 版本 `.img` 或 `.img.gz` 写入可靠 TF 卡；至少 8 GB，建议 16 GB 或更大。写入会清空目标卡。
2. 板子断电插卡，接 HDMI、USB 键盘或手柄，建议接网线，并使用适合该板的电源与散热。
3. 显示器先开机，板子再通电，首次等待 3–5 分钟。
4. 记录是否进入 Batocera，以及画面、USB 输入、网络和 HDMI 声音的结果。

本板的 TF 尝试仍进入原 Linux。若出现同样现象，先保存原系统信息及启动日志；若黑屏，记录显示器状态、板上指示灯和网口状态。不要凭其他 RK3288 板卡的图示短接引脚。诊断方法见 [测试记录](docs/TESTING.md)。

## 仓库内容

- `build-boot-assets.sh`：构建指定存储版本的 loader 和 DTB。
- `make-image.py`：校验官方底包并组装指定版本的整盘镜像。
- `package-rkdevtool.py`：生成普通分段镜像、地址配置和校验清单，不访问设备。
- `collect-logs.sh`：在 Batocera 中收集启动和硬件状态。
- `tools/firefly-network-identity.sh`：在 ConnMan 前设置板卡专属的稳定有线 MAC。
- `source/`：U-Boot 配方、完整配置、Firefly DTS 及其依赖和选定补丁。
- `boot-assets/`：extlinux 和板型标识；构建后还包含生成的 loader 与 DTB。
- `docs/`：构建、eMMC 烧录、游戏传输和实际验证记录。

## 许可与来源

本项目新增的独立脚本按仓库 `LICENSE` 中声明的 MIT 许可发布。上游源码、设备树、补丁和二进制产物保留各自许可证，详情见 [第三方说明](THIRD_PARTY_NOTICES.md)。

- [Batocera](https://github.com/batocera-linux/batocera.linux)
- [U-Boot](https://github.com/u-boot/u-boot)
- [Linux](https://github.com/gregkh/linux)
