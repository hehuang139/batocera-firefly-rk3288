# Wi-Fi：修复与验证

2026-11-04，在原版 Firefly-RK3288 的 eMMC 安装上，修正设备树、补充 AP6335 板级 NVRAM 并加入有线身份更新后，**已验证一次软件重启后的 Wi-Fi 自动关联、DHCP IPv4 和无线 SSH**。启动 ID 确认改变，板级 NVRAM 自动安装，SDIO、`wlan0` 与 BCM4339/2 固件 `6.37.39.113` 正常初始化。驱动修复后的扫描也已通过：`connmanctl scan wifi` 完成，发现 17 个无线服务。

Batocera 的 `wifi.enabled = 1`，`batocera-wifi list` 已能输出非空无线网络列表。用户配置网络后，ConnMan 显示 `Connected = true`、`Tethering = false`，`wlan0` 为 UP 并取得 DHCP IPv4；通过该无线地址完成 SSH 登录，主机密钥与同一块板匹配，当时有线接口没有 IPv4。

重启后，有线和无线 MAC 均与部署前备份完全一致，本次无线 IP 也相同。当时网线未连接，`carrier = 0`，因此没有验证更新后的有线 DHCP 地址。2.4 / 5 GHz 各频段、吞吐量、游戏文件传输、长期稳定性及多次冷启动仍未验收；一次 DHCP 地址复用也不能证明地址永久固定。传输步骤见 [传输游戏](TRANSFER-GAMES.md)。

## 第一处阻断：SDIO 供电描述与电源时序

修复前系统没有无线接口，`/sys/bus/sdio/devices/` 为空。运行内核为 6.1.55，`ff0d0000.mmc` 在探测时反复输出：

```text
Failed getting OCR mask: 0
could not set regulator OCR (-22)
failed to enable vmmc regulator
```

实际运行设备树将 SDIO0 的 `vmmc-supply` 指向固定 5 V 的 `vcc_sys`，系统 regulator 接口也报告 5,000,000 微伏。这无法形成正常的 MMC 电压掩码，日志同时确认 DW-MMC 供电设置失败。SDIO0 本身已启用，内核也已启用 brcmfmac SDIO 支持，不能只根据未出现无线接口认定缺驱动。

修正仅从 SDIO0 删除该 `vmmc-supply` 引用，保留 1.8 V `vqmmc-supply`；没有改变共享 5 V `vcc_sys` 节点或板上实际供电。另按 [原版 Firefly vendor DTS 固定提交](https://github.com/rockchip-linux/kernel/blob/9ead5f3cbd6e0abd0ac70002205993c953c227ea/arch/arm/boot/dts/rk3288-firefly.dtsi#L163) 补充 `mmc-pwrseq-simple`、GPIO4_D4 低有效复位和 HYM8563 32 kHz 外部时钟，并限制 SDIO 总线最高 50 MHz。组合更新后系统能够枚举 BCM4339；本次没有逐项进行 A/B 测试，因此没有单独证明供电描述与复位 / 时钟各自对枚举的影响。

vendor DTS 也把 `vbat_wl` 指向共享 5 V 节点；删除该引用是针对当前主线 MMC 电压模型的处理，不是照搬 vendor 供电配置。上述描述来自设备树及驱动日志，不是板上电压测量；不能因此把共享电源改成 3.3 V。

## 第二处阻断：缺少板级 NVRAM

SDIO 枚举恢复后，BCM4339 固件初始化还需要对应板卡的 NVRAM 文本。基础系统已有 BCM4339 固件二进制，但缺少本板使用的 AP6335 配置。仅存在 `.bin` 并不足以完成初始化。

补充固定来源的 AP6335 NVRAM 后，brcmfmac 完成初始化，ConnMan 扫描成功并列出 20 个无线服务。配置文件包含板级射频和校准参数，应按板型及芯片使用，不能通过重命名其他 BCM4345 / BCM43455 文件替代。

日志可能先尝试带板型后缀的固件名，再退回通用 BCM4339 二进制；前一个可选候选不存在不等于最终加载失败。缺少 CLM 文件的警告也没有阻止本次实际扫描，但这不足以证明全部地区、频段和发射功率条件已验证。应结合后续固件启动、无线接口和扫描结果判断，不能只统计日志中的 `failed` 字样。

## 开机安装与重启验证

准备工具为 [`tools/prepare_wifi_firmware.py`](../tools/prepare_wifi_firmware.py) 与 [`tools/firefly-boot-custom.sh`](../tools/firefly-boot-custom.sh)。在构建主机执行以下命令，输出目录必须尚不存在：

```sh
python3 tools/prepare_wifi_firmware.py wifi-bundle
```

准备器生成 `boot-custom.sh`、`firefly-network-identity.sh` 与 `firefly-wifi/` 目录，后者包含 `nvram_AP6335.txt`、`LICENSE.rkwifibt` 和 `manifest.json`。部署到启动分区后，由 `S00bootcustom` 在 udev 之前调用 `/boot/boot-custom.sh`，先运行有线身份辅助脚本，再把 NVRAM 安装为 `/lib/firmware/brcm/brcmfmac4339-sdio.firefly,firefly-rk3288.txt`，避免内存根文件系统中的手工复制在重启后消失或驱动先于配置加载。有线辅助脚本失败会记录错误并继续 Wi-Fi 安装。已有自定义 `boot-custom.sh` 的系统需要先合并原有逻辑，不能直接覆盖。

`make-image.py` 默认在临时目录自动下载并校验这份文件包，再把开机文件加入镜像；预先下载后可离线组装：

```sh
python3 make-image.py --variant emmc --wifi-firmware wifi-bundle \
  batocera-rk3288-miqi-39-20240301.img.gz emmc.img
```

这些构建命令仍应在 [构建说明](BUILD.md) 的工具环境内执行。镜像旁的 `.img.manifest.json` 中用 `wifi_firmware` 记录来源及哈希。

下载器固定使用 [radxa/rkwifibt 提交 `b61a1e8499a4f1956ef417cbcfaa6c2cf805ce08`](https://github.com/radxa/rkwifibt/tree/b61a1e8499a4f1956ef417cbcfaa6c2cf805ce08)，并校验原始 NVRAM SHA-256 为 `9f6dbebb3f0b078831de6d0998e8bdbae421015beeabb22d3774f5c66b99a326`。供应商文件和许可证由准备器下载生成，不直接提交到仓库。

已有目标 NVRAM 与固定来源的校准内容一致时，优先保留其中合法、非上游样例的 MAC；遇到其他校准内容则拒绝覆盖，要求先检查。需要备用值时，先读取设备树或 CPU 序列号；要求为 8–64 位十六进制且非全零。本板未提供有效 CPU / 设备树序列号，因此使用 eMMC CID 回退：只接受 MMC 总线中唯一的 `type = MMC` 设备，跳过 `type = SD` 的 TF 卡，CID 必须为 32 位十六进制且非全零。没有候选、多个 MMC 设备或无有效标识时拒绝生成备用值，不沿用公共样例地址。

序列号与 CID 使用不同输入前缀哈希，再生成稳定的本地管理单播 MAC。CID 筛选依据为 MMC 设备类型，不依赖开机早期尚可能未出现的块设备节点，也不表示通用支持任意可移动 MMC。

本次现场修复范围是 **eMMC 版本**。SD 版本的 DTS 虽然也编译通过，但其 Linux 配置禁用 eMMC；在同样缺少有效 CPU / 设备树序列号的板上，无法取得 eMMC CID，脚本会拒绝生成备用 MAC。TF 卡 CID 不作为替代来源，不能据此宣称 SD 版本 Wi-Fi 已可用。

包含 Wi-Fi 修复与有线身份辅助脚本的当前整盘镜像已完成组装、FAT 文件回读和 RKDevTool 六段生成 / 重组校验；重组 SHA-256 与完整镜像相同。现场是在历史 `emmc-test1` 安装上部署相同 DTB 和早期文件，通过一次软件重启验证有线与无线 MAC 保持一致、Wi-Fi 自动关联和无线 SSH 正常。新整盘镜像尚未另行完整烧录上板，文件验证与现场更新验证的范围应分别理解。

## 有线与无线 IP

有线 `eth0` 与无线 `wlan0` 是不同网卡，各自通过 DHCP 获取地址。切换到 Wi-Fi 后应查看 `ip -4 address show wlan0`；不能继续假定先前的有线 IP 就是无线 IP。

此前观察到有线 MAC 在不同启动间变化。U-Boot 配置启用 `CONFIG_NET_RANDOM_ETHADDR=y`，同时使用不持久化的 `CONFIG_ENV_IS_NOWHERE=y`；运行设备树中的有线 MAC 也随启动变化，DHCP 服务器因而可能将其视为新设备。

[`tools/firefly-network-identity.sh`](../tools/firefly-network-identity.sh) 在 ConnMan 启动前，为 `eth0` 设置稳定的本地管理单播 MAC，默认以有效 CPU 序列号或唯一 MMC CID 为依据，使用与无线备用地址不同的哈希前缀。它只在地址不同、接口尚未启用且 ConnMan 尚未运行时修改，避免中断在线连接。现场保留原有租约身份的覆盖配置已部署，并通过一次软件重启验证：有线 MAC 与部署前备份完全一致，无线硬件 MAC 也保持一致，Wi-Fi 自动关联且无线 SSH 可用。当时有线 `carrier = 0`，没有验证有线联网或 DHCP 地址。

本修复在 Linux 层设置接口地址，不修改 U-Boot 的随机地址行为。现场重启后，运行设备树中的有线 MAC 与 Linux 当前接口 MAC 不同，`/sys/class/net/eth0/addr_assign_type` 为 `3`（软件设置），后者与部署前地址一致。验收应读取当前 Linux 接口地址，不能只查看运行设备树。

可选的 `/boot/firefly-network.conf` 只接受 `board_id` 与 `ethernet_mac`，按严格字段解析而非作为 shell 执行；`board_id` 必须与本板身份匹配。以下命令只读取并输出板卡身份指纹：

```sh
bash /boot/firefly-network-identity.sh print-identity
```

该私有配置用于单板保留既有有线 MAC，不应提交到仓库或复制到其他板卡；通用镜像安装器会拒绝包含它。通用构建使用每板派生地址，不包含现场 MAC 或网络地址。

**稳定 MAC 不保证 DHCP 永远分配同一 IP。** 要求地址固定时，应在 DHCP 服务器中分别为稳定有线 MAC 和无线 MAC 保留两个不同地址，再逐接口重启验收。当前地址保留尚未完成；未知 DHCP 地址池时不要直接把当前动态地址锁为静态地址。

Batocera 原有的 `SingleConnectedTechnology=true` 和有线优先策略保持不变。插拔网线可能改变活动接口，应分别验证有线和无线的 MAC、租约及连接，不能把其中一个接口的地址变化直接视为另一个接口失败。

## 回退现场更新

现场更新保留了原 DTB，并将原启动配置备份为 `/boot/extlinux/extlinux.conf.pre-wifi`。需要回退时，将 `/boot` 重新挂载为可写，把 extlinux 的 `DEFAULT` 改回引用原 DTB 的保留条目，或恢复该配置备份；确认其 `FDT` 指向仍存在的原 DTB。

若原系统没有自定义开机脚本、当前 `/boot/boot-custom.sh` 完全由本项目提供，可将它改名为 `boot-custom.sh.disabled` 保留备份，使开机不再安装 NVRAM。已有其他自定义逻辑时应仅撤销本项目调用，保留原脚本；不要覆盖已有的同名备份。

完成后执行 `sync`，将 `/boot` 重新挂载为只读，再重启。回退不需要改写整盘镜像，也不修改 eMMC boot0 / boot1。

仅回退有线身份更新时，在 `/boot` 可写期间，从本次部署前的备份同时恢复 `/boot/boot-custom.sh` 和 `/boot/firefly-wifi/manifest.json`，以保留已验证的 Wi-Fi 流程及与之匹配的清单。确认恢复后的启动脚本不再调用有线身份辅助脚本；专用 `firefly-network-identity.sh` 和私有 `firefly-network.conf` 可保留为不再调用的文件，不必删除。随后 `sync`、重新挂载只读并重启。不要在当前连接已启用时强行改回有线 MAC。

## 排查命令与结果判读

```sh
ip -brief link
iw dev
rfkill list
ls -l /sys/bus/sdio/devices
for node in /sys/bus/sdio/devices/*; do
    [ -e "$node" ] || continue
    cat "$node/uevent"
    readlink "$node/driver"
done
dmesg | grep -Ei 'ff0d0000|brcm|firmware|mmc|sdio|wlan|rfkill'
connmanctl scan wifi
connmanctl services
```

先确认 SDIO 和驱动，再看实际请求的固件与 NVRAM；无线接口出现后验证扫描，最后才进行关联、网络连通和性能测试。分享日志前移除私人 IP、MAC、SSID 和凭据。
