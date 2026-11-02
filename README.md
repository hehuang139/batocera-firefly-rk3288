# Batocera for Firefly-RK3288

原版 **Firefly-RK3288** 的 Batocera 39 社区适配工程，面向 **microSD/TF 卡启动、HDMI 显示和 USB 手柄**。

本项目复用官方 Batocera 39 MiQi 镜像的 RK3288 内核和系统文件，提供 Firefly 专用 U-Boot 配置、设备树、补丁及镜像组装脚本。适用板卡为上游设备树中的 `firefly,firefly-rk3288`；Firefly-RK3288 Reload 使用不同设备树。

## 当前状态

已完成 U-Boot 和设备树编译、镜像组装，以及分区、引导偏移、CRC、启动文件和系统文件校验。下一项验收是原版 Firefly-RK3288 的 **TF 卡 + HDMI 冷启动**；后续在 [测试记录](docs/TESTING.md) 更新实际显示、输入、网络、声音和游戏运行结果。

本仓库发布适配源码、构建配方和启动配置，loader 与 DTB 由构建脚本生成。完整 Batocera 发行版由构建者从官方来源下载，再通过本项目脚本组装。仓库内容覆盖本项目的板级适配部分；系统根文件中的各软件组件由其各自上游维护。

## 版本与改动

| 部分 | 来源 / 配置 |
| --- | --- |
| 基础系统 | Batocera 39，MiQi，2024-03-01 |
| Linux | 官方镜像内的 6.1.55，Panfrost GPU 驱动 |
| U-Boot | v2024.01，`firefly-rk3288_defconfig` |
| 设备树 | Linux v6.1.55 Firefly DTS，加 Batocera RK3288 相关 DTS 补丁 |
| 显示与音频 | HDMI、I2S、HDMI simple-audio-card |
| 存储 | TF 卡；Linux 设备树禁用 eMMC |
| CPU | 保留上游最高 1.608 GHz 配置 |

新 U-Boot 使用内存环境，启动命令只扫描其 SD 控制器 `mmc1`。芯片和板载旧引导是否执行 TF 卡中的 loader，需要首启确认。启动分区板型标识设置为 `firefly-rk3288`，避免自动匹配 MiQi 的系统更新。

## 构建

需要 Linux、Docker 和约 12 GB 可用空间。完整命令、基础镜像的固定校验值和分区布局见 [构建说明](docs/BUILD.md)。

```sh
./build-boot-assets.sh
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py batocera-rk3288-miqi-39-20240301.img.gz rebuilt.img
```

先按构建说明下载指定官方基础镜像。`build-boot-assets.sh` 编译 loader 和 DTB，并复制到 `boot-assets/`；`make-image.py` 校验底包并生成普通 `.img` 文件，写卡由镜像工具完成。

## 首次启动

1. 用 balenaEtcher 把生成的 `.img` 或 `.img.gz` 写入可靠 TF 卡；至少 8 GB，建议 16 GB 或更大。写入会清空目标卡。
2. 板子断电插卡，接 HDMI、USB 键盘或手柄，建议接网线，并使用适合该板的电源与散热。
3. 显示器先开机，板子再通电。首次扩容预留 3–5 分钟。
4. 记录是否进入 Batocera，以及画面、USB 输入、网络和 HDMI 声音的结果。

若仍进入原有 Android/Linux，先保存旧系统信息和启动日志；若黑屏，记录显示器状态、板上指示灯和网口状态。不要凭其他 RK3288 板卡的图示短接引脚。诊断信息及反馈模板见 [测试记录](docs/TESTING.md)。

## 仓库内容

- `make-image.py`：校验官方底包并组装整盘镜像。
- `collect-logs.sh`：在 Batocera 中收集启动和硬件状态。
- `source/`：U-Boot 配方、完整配置、Firefly DTS 及其依赖和选定补丁。
- `boot-assets/`：extlinux 和板型标识；构建后还包含生成的 loader 与 DTB。
- `docs/`：构建说明、验证结果及首启反馈方法。

## 许可与来源

本项目新增的独立脚本按仓库 `LICENSE` 中声明的 MIT 许可发布。上游源码、设备树、补丁和二进制产物保留各自许可证，详情见 [第三方说明](THIRD_PARTY_NOTICES.md)。

- [Batocera](https://github.com/batocera-linux/batocera.linux)
- [U-Boot](https://github.com/u-boot/u-boot)
- [Linux](https://github.com/gregkh/linux)
