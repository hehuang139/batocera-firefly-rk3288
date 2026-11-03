# 验证与启动记录

## 2026-11-04：eMMC 启动、手柄、有线网络与扩容

用户在原版 Firefly-RK3288 上使用 RKDevTool 2.96 分段写入 eMMC 后，确认 Batocera 启动成功，并报告手柄可用。手柄型号、接口及游戏内测试细节未提供；这次结果不代表所有手柄或全部游戏已验证。

随后通过有线 SSH 检查，确认有线网络可用，`/userdata` 位于 `mmcblk1p2`，SHARE 分区已扩容至约 10.5 GiB。Wi-Fi 最初因 SDIO 初始化及板级 NVRAM 问题不可用；修正后已通过一次软件重启验证，启动 ID 改变，NVRAM 自动安装，SDIO、`wlan0`、BCM4339/2 固件 `6.37.39.113` 恢复。扫描重启前发现 20 个服务、重启后发现 17 个服务；路由器关联、各频段、速度和长期稳定性尚未验证。证据和机制见 [Wi-Fi 修复与验证](WIFI.md)。

| 项目 | 现场记录 |
| --- | --- |
| 板卡 | 原版 Firefly-RK3288，非 Reload |
| 原有系统 | Linux |
| 先前 TF 卡尝试 | 仍进入原 Linux；尚未通过启动日志确定原因 |
| 写入工具 | Windows RKDevTool 2.96，“下载镜像”，强制按地址写 |
| 写入介质 | 板载 eMMC user area，从 LBA 0 开始的整盘内容 |
| Flash 信息 | Samsung，14910 MB（工具显示值） |
| FlashID | `454D4D4320`，前四字节 `45 4D 4D 43` 为 ASCII `EMMC` |
| 当前 Loader | `2.3a` |
| Loader 兼容性处理 | 手动选 EMMC 报“Loader不支持切换”；读取 FlashID / Flash 信息确认默认介质后，存储列留空写入成功 |
| 启动结果 | 2026-11-04，用户确认 eMMC 镜像启动成功 |
| 手柄 | 用户报告可用；未提供型号、接口及游戏内测试细节 |
| 有线网络 | 已通过现场 SSH 登录验证 |
| SHARE 扩容 | 已确认约 10.5 GiB，挂载于 `/userdata` |
| Wi-Fi | BCM4339 枚举与一次软件重启后的自动恢复、扫描通过；重启后 17 个服务，见 [分析](WIFI.md) |

该镜像使用主线 TPL/SPL：`idbloader` 位于 32 KiB，U-Boot 位于 8 MiB；U-Boot 扫描 `mmc0`，Linux 的 eMMC 与 SD 控制器均启用，U-Boot 使用内存环境。烧录六段连续覆盖 4,848,615,424 字节，头部最后写入。配置与复现步骤见 [eMMC 烧录说明](FLASHING-EMMC.md)。

本次最初启动的 `emmc-test1` 镜像 SHA-256（后续现场 Wi-Fi 更新了 DTB / NVRAM，不再是该整盘文件的原样运行状态）：

```text
bc38fe7350c18f157a6d835cc88ce5b1e725ee05a2d1d4587a95815f413bfaca
```

该历史镜像的 U-Boot 引导产物 SHA-256（不包含后续 Linux Wi-Fi DTB）：

| 文件 | SHA-256 |
| --- | --- |
| eMMC idbloader | `bf82871726471c2f8e229423597d8b68641dc63d842bb67eda4c2ab5611d0ea0` |
| eMMC u-boot-dtb.img | `f5b5ee8e934355908e8f8c43615b717de64143fa3ed0029c5396d2c53e847588` |

这些值标识此次测试文件。重新构建时工具链版本、构建时间或 FAT 写入时间可能改变最终文件哈希；不能把新生成文件与历史测试文件的逐字节差异直接等同于启动故障。

## 功能验收进度

| 项目 | 当前进度 |
| --- | --- |
| eMMC 写入并启动 Batocera | 用户已确认成功 |
| 手柄输入 | 用户报告可用；型号、接口及游戏内细节未提供 |
| TF 卡启动 | 未确认；本板先前仍进入原 Linux |
| HDMI 分辨率、模式与稳定性 | 尚未单独验证 |
| 其他 USB 外设 | 尚未单独验证 |
| SHARE 数据分区自动扩容 | 已验证；约 10.5 GiB |
| 有线网络与 SSH | 已通过现场 SSH 登录验证 |
| Wi-Fi SDIO / 驱动初始化与扫描 | BCM4339 已枚举，重启后扫描完成、17 个无线服务，`batocera-wifi list` 返回非空列表；见 [分析](WIFI.md) |
| Wi-Fi 开机自动恢复 | 已通过一次软件重启验证；NVRAM 自动安装、`wlan0` 恢复 |
| Wi-Fi 关联路由器、频段与传输性能 | 尚未验证 |
| SD 版本 Wi-Fi | 尚未验证；eMMC 被禁用，无有效 CPU / 设备树序列号时不能使用 CID 回退 |
| 蓝牙 | 尚未单独验证 |
| 游戏文件网络传输 | 尚未单独验证 |
| HDMI / 模拟音频 | 尚未单独验证 |
| Panfrost GPU 加速 / 游戏运行 | 尚未单独验证 |
| 多次冷启动与长时间运行 | 尚未单独验证 |

## 已执行的构建与文件检查

2026-11-02，使用 Ubuntu 22.04 x86_64 主机和隔离的 Ubuntu 22.04 ARM 交叉编译环境完成 SD 实验版本的初始构建。随后 eMMC 测试版本重新编译了引导和设备树，并检查 eMMC / SD 节点均为 `okay`、U-Boot `mmc0` 指向 `/mmc@ff0f0000`。

2026-11-04，新增的公开双版本构建流程已完成 SD / eMMC 重新构建、镜像组装与分段打包验证。实际启动和 SSH 验证以历史 `emmc-test1` 安装为基础，随后现场更新 Wi-Fi DTB 与 NVRAM；新整盘构建产物尚未单独上板验证。

Wi-Fi 修正版的 SD / eMMC DTS 均已编译通过。以下历史哈希不标识当前 Linux DTB；当前构建产物应使用新生成的 `boot-assets[/emmc]/manifest.json` 和镜像旁清单核对。

包含 Wi-Fi DTB、早期安装文件及 MMC CID 备用标识逻辑的整盘镜像已完成构建、FAT 回读和 RKDevTool 分段重组校验；完整文件及六段重组的 SHA-256 均为 `cc30155784d9762044e8bf603f9a47a1aedcdedd377a360861bb1adc3e8b265a`。现场以已有 `emmc-test1` 安装更新相同文件后完成重启验证；该新整盘文件尚未另行完整烧录上板。

| 检查 | 结果 |
| --- | --- |
| U-Boot v2024.01 Firefly ARM 构建 | 成功 |
| 初始公开 `build-boot-assets.sh` 完整执行 | 成功；三项生成文件与当次首次构建的 SHA-256 一致 |
| Firefly DTB 编译与关键节点检查 | 成功；SD 版禁用 eMMC，eMMC 版启用 eMMC 与 SD |
| 实际官方内核版本和配置提取 | Linux 6.1.55，相关电源、存储、显示和音频驱动启用 |
| U-Boot uImage 头及数据 CRC | 通过 |
| loader 偏移及二进制比较 | idbloader 32 KiB，U-Boot 8 MiB，与相应构建产物一致 |
| MBR、FAT 和 SHARE 边界 | 通过；完整镜像 4,848,615,424 字节 |
| extlinux / DTB / 板型文件 | 与预期输入逐字节一致 |
| 最终内核、initrd、SquashFS 校验 | 与官方输入一致 |
| SD gzip 压缩完整性 | 通过 |
| 当前 Wi-Fi 修正版 eMMC 分段配置与重组 | 六段生成成功，无间隙或重叠；重组 SHA-256 与当前完整镜像一致 |

共同输入与初始 SD 产物的 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| 官方基础镜像 gzip | `4280732daf9fb32ee59f56f727134c5a5e5c8a2b64add593a5e8e50c78654a01` |
| 初始 SD idbloader | `52cc45914527403534bd8b6f044acb29b9568c85ef22103c0bbf9afc89825335` |
| 初始 SD U-Boot | `4f7d7171563590d7098a7c229157fadf840019003f45f29d10e41b1123ee97c4` |
| 官方内核 | `aa709f8af032841c0a4035548362ba8c9b72ad64fba9ff163e1e1e78060f8a61` |
| 官方 initrd | `0d22b407a3a8db0c2600c2e33a56692823d2e21bbfc6543740fa3c442250f542` |
| 官方 SquashFS | `6feb162b5cda73f7332789f1dec491b4b8562c2ccfe3c554f7f1b3703895eb2c` |

U-Boot 的 TPL 设备树生成步骤输出 alias/uclass、gpio_leds 和 syscon 后缀警告；dtc 输出继承节点的 interrupt-provider 与显示 graph 警告，两个构建均返回 0。

## 收集日志

进入系统后，通过 Batocera 网络设置取得 IP，再用 SSH 登录。执行：

```sh
sh /boot/collect-logs.sh
```

日志写入 `/userdata/system/firefly-diagnostics-日期时间/`，包含内核日志、显示接口、声卡、网络和存储信息。对外分享前请检查并移除其中的私人信息。

若仍启动原系统，记录原系统版本及启动画面。本项目 U-Boot 的 `mmc0` / `mmc1` 分别是 eMMC / SD 别名，不能套用到未知旧 U-Boot。需要读取串口时，先核实原版板卡的调试口：使用 3.3 V 电平，共地、TX/RX 交叉、不接适配器 VCC，参数 115200 8N1、无流控。

## Issue 反馈模板

```text
板卡丝印/修订版：
内存与 eMMC 容量：
使用的提交或版本，emmc / sd：
镜像 SHA-256：
原有系统与当前 Loader 版本：
FlashID / Flash 信息（eMMC 烧录时）：
烧录工具版本、完整日志与校验结果：
TF 卡型号与容量（SD 实验时）：
电源、散热、HDMI 显示器：
通电后结果和出现时间：
显示/手柄型号与接口/其他 USB/网络/音频/扩容/游戏结果：
最后一屏文字或日志：
```
