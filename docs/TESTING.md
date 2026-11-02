# 验证与首启记录

## 已执行的构建与文件检查

2026-11-02，使用 Ubuntu 22.04 x86_64 主机和隔离的 Ubuntu 22.04 ARM 交叉编译环境完成：

| 检查 | 结果 |
| --- | --- |
| U-Boot v2024.01 Firefly ARM 构建 | 成功 |
| 公开仓库 `build-boot-assets.sh` 完整执行 | 成功；三项生成文件与首次构建的 SHA-256 一致 |
| Firefly DTB 编译与关键节点检查 | 成功；SD、HDMI、I2S、GPU 启用，eMMC 禁用 |
| 实际官方内核版本和配置提取 | Linux 6.1.55，相关电源、存储、显示和音频驱动启用 |
| U-Boot uImage 头及数据 CRC | 通过 |
| loader 偏移及二进制比较 | idbloader 32 KiB，U-Boot 8 MiB，与构建产物一致 |
| MBR、FAT 和 SHARE 边界 | 通过；完整镜像 4,848,615,424 字节 |
| extlinux / DTB / 板型文件 | 与预期输入逐字节一致 |
| 最终内核、initrd、SquashFS 校验 | 与官方输入一致 |
| gzip 压缩完整性 | 通过 |

关键文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| 官方基础镜像 gzip | `4280732daf9fb32ee59f56f727134c5a5e5c8a2b64add593a5e8e50c78654a01` |
| Firefly idbloader | `52cc45914527403534bd8b6f044acb29b9568c85ef22103c0bbf9afc89825335` |
| Firefly U-Boot | `4f7d7171563590d7098a7c229157fadf840019003f45f29d10e41b1123ee97c4` |
| 官方内核 | `aa709f8af032841c0a4035548362ba8c9b72ad64fba9ff163e1e1e78060f8a61` |
| 官方 initrd | `0d22b407a3a8db0c2600c2e33a56692823d2e21bbfc6543740fa3c442250f542` |
| 官方 SquashFS | `6feb162b5cda73f7332789f1dec491b4b8562c2ccfe3c554f7f1b3703895eb2c` |

U-Boot 的 TPL 设备树生成步骤输出 alias/uclass、gpio_leds 和 syscon 后缀警告；dtc 输出继承节点的 interrupt-provider 与显示 graph 警告，两个构建均返回 0。

## 下一轮硬件验收

验收入口：原版 Firefly-RK3288，TF 卡，HDMI 显示器，USB 键盘或手柄，网线。

| 项目 | 当前进度 |
| --- | --- |
| 芯片/原有引导选择 TF 卡 | 等待首启结果 |
| 进入 Batocera 主界面 | 等待首启结果 |
| HDMI 显示 | 等待首启结果 |
| USB 输入 | 等待首启结果 |
| TF 卡数据分区扩容 | 等待首启结果 |
| 有线网络 | 等待首启结果 |
| HDMI 音频 | 等待首启结果 |
| Panfrost / 游戏运行 | 等待首启结果 |

## 收集日志

进入系统后，通过 Batocera 网络设置取得 IP，再用 SSH 登录。执行：

```sh
sh /boot/collect-logs.sh
```

日志写入 `/userdata/system/firefly-diagnostics-日期时间/`。它包含内核日志、显示接口、声卡、网络和存储信息；分享前可先阅读内容。

若仍启动原来的 Android/Linux，记录原系统版本及启动画面。新 U-Boot 的 `mmc1` 是其自身设备树中的 SD 别名，不能套用到未知旧 U-Boot。需要读串口时，先核实板卡调试口：UART 排针使用 3.3 V 电平，共地、TX/RX 交叉、不接适配器 VCC，参数 115200 8N1、无流控。

## Issue 反馈模板

```text
板卡丝印/修订版：
内存与 eMMC 容量（如已知）：
使用的提交或版本：
TF 卡型号与容量：
写卡工具及校验结果：
电源、散热、HDMI 显示器：
通电后结果和出现时间：
显示/USB/网络/音频结果：
最后一屏文字或日志：
```
