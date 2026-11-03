# Wi-Fi：当前已知初始化问题

2026-11-04，在已经从 eMMC 启动的 `emmc-test1` 系统上，用户报告搜索不到无线网络。通过有线 SSH 只读检查，确认系统没有无线接口，`/sys/bus/sdio/devices/` 为空，`iw dev` 没有输出。

## 已确认的失败阶段

运行内核为 6.1.55。无线 SDIO 控制器 `ff0d0000.mmc` 在探测时反复输出：

```text
Failed getting OCR mask: 0
could not set regulator OCR (-22)
failed to enable vmmc regulator
```

实际运行设备树中，`/mmc@ff0d0000/vmmc-supply` 引用了 `/vsys-regulator`，其固定电压为 5,000,000 微伏；系统 regulator 接口也报告 `vcc_sys` 为 5 V。仓库继承的 Firefly DTS 将 `vbat_wl` 和 `vcc_sys` 定义为同一个 5 V 节点，并让 SDIO0 的 `vmmc-supply` 指向它。这一供电描述无法形成正常 MMC 电压掩码，与现场 OCR / regulator 错误一致。

SDIO0 已设置 `status = "okay"`，并配置总线引脚及 `vqmmc-supply`。官方内核启用了 `CONFIG_BRCMFMAC=m`、`CONFIG_BRCMFMAC_SDIO=y`，系统中存在 `brcmfmac.ko` 和 BCM4339 固件二进制。因此当前首先阻塞在 SDIO 设备初始化阶段，尚未进入无线扫描或固件加载阶段；没有证据表明路由器、密码或游戏传输设置是本次原因。

这描述的是设备树及驱动初始化问题，不是对板上实际电压的测量，也不证明硬件损坏。`vcc_sys` 为多个设备共用，不能为了消除报错就把共享 5 V 节点改成 3.3 V。

## 仍需核对的条件

Rockchip 的 [原版 Firefly vendor DTS](https://github.com/rockchip-linux/kernel/blob/develop-4.4/arch/arm/boot/dts/rk3288-firefly.dtsi) 为无线模块配置了电源时序、GPIO4_D4 复位及 HYM8563 外部时钟。当前主线 DTS 缺少对应的无线 `mmc-pwrseq` 关联。修复时需要按原版板卡电路及绑定规则核对供电描述、复位和 32 kHz 时钟，再观察 SDIO 是否枚举。

无线模块的实际 SDIO ID 尚未读取到，不能仅按常见 AP6335 型号就确认芯片。设备出现后，还需要根据 `dmesg` 实际请求核对固件与板级 NVRAM；本次只确认存在固件二进制，没有证明所有无线固件条件齐全。

当前仓库记录并保留这个已知问题，尚未将未上板验证的 Wi-Fi 设备树修改作为修复发布。临时可用已经验证的有线网络传游戏，见 [传输游戏](TRANSFER-GAMES.md)。

## 只读排查命令

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
modinfo brcmfmac
```

优先看 SDIO 是否出现设备，再区分驱动、固件、rfkill 和扫描问题。只有出现无线接口并能扫描后，才进行 SSID、密码、连接稳定性和传输速度验证。不要公开包含私人 IP、MAC、SSID 或密码的完整配置文件。
