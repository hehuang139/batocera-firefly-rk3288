# 使用 RKDevTool 2.96 烧录 eMMC

适用原版 **Firefly-RK3288**（`firefly,firefly-rk3288`），不适用于 Reload。2026-11-04，用户已按分段写入流程确认 eMMC 镜像启动成功；现场设备为 Samsung eMMC，工具显示 14910 MB、FlashID `454D4D4320`、Loader `2.3a`。完整测试范围见 [测试记录](TESTING.md)。

写入目标是 eMMC **user area**，会覆盖原 Linux 系统、分区表及用户分区。先备份需要保留的数据。目标可用容量至少 **4,848,615,424 字节**，通常需要 8 GB 或更大的 eMMC；容量和介质必须从实际设备读取确认。

## 准备镜像、配置与工具

按 [构建说明](BUILD.md) 下载并校验官方基础镜像，构建 eMMC 版本：

```sh
./build-boot-assets.sh emmc
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py --variant emmc \
  batocera-rk3288-miqi-39-20240301.img.gz emmc.img
```

需要进入 MaskROM 的 RAM 下载阶段时，按构建说明生成固定 Rockchip rkbin 来源的 `rk3288_loader_v1.12.263.bin`。然后生成分段文件与 RKDevTool 配置：

```sh
python3 package-rkdevtool.py emmc.img rkdevtool-emmc \
  --usb-loader path/to/rk3288_loader_v1.12.263.bin
```

打包脚本只操作普通文件，不会写入设备。输出包含 `Image/` 下的六段镜像、临时 USB Loader、`01-usb-loader-ram.cfg`、`02-emmc-write.cfg` 及校验清单。按生成清单校验文件，并保留 `Image/` 与 CFG 的相对位置。

Windows 工具需另外下载，仓库和脚本输出不包含 EXE：

- [RKDevTool 2.96 中文版](https://dl.radxa.com/tools/windows/RKDevTool_Release_v2.96_zh.zip)
- [Rockchip DriverAssitant 5.14](https://dl.radxa.com/tools/windows/DriverAssitant_v5.14.zip)

安装驱动，将 RKDevTool 解压到简短英文目录，再将分段输出目录内的文件复制到 `RKDevTool.exe` 所在目录，使 `Image/` 与两份 CFG 位于该目录。不要把整盘镜像重命名为 `update.img`：它不是 Rockchip RKFW 固件包，应使用“下载镜像”，而非“升级固件”。

如工具 `config.ini` 中有 `RESET_AFTER_DOWNLOAD`，关闭工具后将其设为 `FALSE`，再启动工具，避免写完自动重启。使用自己的配置时也需核对这一项。

## 连接与确认下载模式

1. 保持开发板正常外接供电，通过板卡 OTG 连接电脑。
2. 使用此前刷写这块板 Linux 的已知方法，或已核实的原版板卡说明，进入下载模式。本文不指定未经核实的按键组合或短接位置。
3. 打开 RKDevTool 2.96，确认显示找到一个 **LOADER** 或 **MASKROM** 设备，再继续。

### 仅 MASKROM：下载临时 USB Loader 到 RAM

当前已显示 LOADER 时跳过本节。

1. 打开“下载镜像”，在表格空白处右键“导入配置”，选择 `01-usb-loader-ram.cfg`。
2. 检查唯一勾选的行名必须是 **`LoaderToDDR`**，路径指向 `Image\rk3288_loader_v1.12.263.bin`。
3. 点“执行”，等待工具识别为 LOADER。

`LoaderToDDR` 将 USB Loader 下载到 RAM，不写设备存储。特殊行名 `Loader` 会执行持久 IDBlock 写入，含义不同，不能互换。主线 `idbloader.img` 是镜像内的存储引导文件，也不能当作此处的 USB 下载 Loader。此次已启动设备使用原来的 Loader `2.3a`，不代表 MaskROM RAM 阶段已在该板单独验证。

## 先读取默认介质，再写入

1. 在“高级功能”依次点击“读取FlashID”和“读取Flash信息”，保存结果。
2. 确认当前默认介质是 **eMMC**，容量不少于 **4,848,615,424 字节**。FlashID 显示 `EMMC`，或开头四字节为 `45 4D 4D 43`，可用于确认介质；同时核对 Flash 信息中的厂商、容量。容量或介质无法确认时先停止，保留读取结果。
3. 回到“下载镜像”，重新导入 `02-emmc-write.cfg`。
4. **各镜像行的“存储”列保持空白，使用刚确认的默认存储；不要手动改成 EMMC。** 勾选“强制按地址写”。
5. 首行 `LoaderToDDR` 必须不勾选；其后六段镜像全部勾选，名称、地址、路径与下表和生成清单一致。

本次现场 Loader `2.3a` 不支持显式存储查询/切换。在“存储”列手动选择 EMMC 会在写入前报 **“Loader不支持切换”**。重新导入 CFG 恢复空白存储列，确认默认存储为 eMMC 后，保持空白即可按当前介质写入。这个处理以已读取的默认介质为依据，不能把“留空”当作所有设备都默认写 eMMC 的保证。

配置文件不代替“强制按地址写”的界面检查。若相对路径找不到文件，逐行浏览选择 `Image/` 下同名文件，保留行名和地址。不要额外添加或勾选 `parameter`、`trust`、`uboot` 或持久 `Loader` 行。

## 六段地址与执行顺序

地址单位为 **512 字节扇区**，不是字节。

| 顺序 | 文件 | 写入地址 | 文件字节数 |
| --- | --- | --- | --- |
| 1 | `Image/emmc-01.img` | `0x00008000` | 1,073,741,824 |
| 2 | `Image/emmc-02.img` | `0x00208000` | 1,073,741,824 |
| 3 | `Image/emmc-03.img` | `0x00408000` | 1,073,741,824 |
| 4 | `Image/emmc-04.img` | `0x00608000` | 1,073,741,824 |
| 5 | `Image/emmc-05.img` | `0x00808000` | 536,870,912 |
| 6 | `Image/emmc-header-last.img` | `0x00000000` | 16,777,216 |

六段按物理偏移排序后连续覆盖整个 4,848,615,424 字节镜像，没有间隙或重叠。最后一段包含 MBR、32 KiB 处的 idbloader 与 8 MiB 处的 U-Boot，因此必须保留在最后一行。分段文件是完整 raw 镜像的切片，不是 Android 分区镜像。

1. 完成介质、容量、路径、勾选和地址检查后，点一次“执行”，按上述顺序完成全部六段。
2. 等待所有下载成功，期间不要断电、拔线或逐段重启。若工具提供下载校验功能，请启用，并保存完整日志。
3. 文件哈希或打包重组校验只确认输入文件；下载成功也不等同于独立的全盘回读校验。
4. 完全断电，**取下 TF 卡**，断开 OTG，连接 HDMI、输入设备等后正常上电，首次等待 3–5 分钟。TF 卡可能包含相同的 `BATOCERA` / `SHARE` 标签，应避免首启挂载错盘。

此流程不修改 eMMC boot0 / boot1、OTP 或硬件 boot partition 配置。若写入报错、仍进入旧 Linux 或黑屏，先保存 RKDevTool 全部日志和 Flash 读取结果，再按 [测试记录](TESTING.md) 收集信息。

## 来源与复现范围

- RKDevTool 随附《开发工具用户手册》说明 `LoaderToDDR` / `Loader` 的区别及按地址烧写。
- 临时 USB Loader 来源为 [Rockchip rkbin 固定提交 `3e288fe814e059dd06833495f845cab04ac20a5c`](https://github.com/rockchip-linux/rkbin/tree/3e288fe814e059dd06833495f845cab04ac20a5c)，输入与输出哈希由生成步骤记录。
- eMMC 与 SD 选择来自本项目主线 U-Boot 的 `mmc0` / `mmc1` 别名；不能据此推断板上旧 Loader 的启动优先级。
- 本次验证为一块原版板卡的 eMMC 启动成功，更多外设与功能结果持续记入 [测试记录](TESTING.md)。
