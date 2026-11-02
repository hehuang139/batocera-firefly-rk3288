# 构建与来源

## 系统来源

基础文件：`batocera-rk3288-miqi-39-20240301.img.gz`，1,626,041,381 字节。

下载地址：
https://mirrors.o2switch.fr/batocera/miqi/stable/last/batocera-rk3288-miqi-39-20240301.img.gz

本次下载内容的 SHA-256：
`4280732daf9fb32ee59f56f727134c5a5e5c8a2b64add593a5e8e50c78654a01`

此哈希固定本次输入文件。基础系统源码：[Batocera 提交 9cbda965212c51ecebb4b79c2b77c91f55715bb7](https://github.com/batocera-linux/batocera.linux/tree/9cbda965212c51ecebb4b79c2b77c91f55715bb7)。

## 重新编译引导和设备树

仓库根目录的 `source/` 包含 U-Boot 构建配方、完整 U-Boot 配置、DTS 源文件及依赖、选定的 Batocera DTS 补丁及其哈希、构建脚本和 Dockerfile。构建脚本在需要时下载固定的 U-Boot v2024.01 源码包并校验 SHA-256。U-Boot 源码未修改，配置差异见 `uboot-manifest.json`。DTS 的许可证保留在各源文件中。

在仓库根目录执行：

```sh
./build-boot-assets.sh
```

顶层脚本创建 Docker 工具环境，运行 `source/rebuild-u-boot.sh` 和 `source/build-dtb.sh`，将生成的 `idbloader.img`、`u-boot-dtb.img` 和 `rk3288-firefly.dtb` 复制到 `boot-assets/`。仓库只跟踪源码和启动配置，编译产物由此步骤生成。

DTS 使用 Linux v6.1.55 依赖树，按顺序应用 Batocera 的七个相关补丁。省略 CPU 1.8 GHz/boost 补丁，保留上游 1.608 GHz 上限。`source/dts-patch-audit/` 保存选中的补丁及来源记录；输入头文件 `linux-event-codes.h` 在此仓库中保存为符号链接所指向的实际头文件内容，方便源码归档与跨平台处理；更新后的文件哈希位于同目录 manifest。

Dockerfile 使用 Ubuntu 22.04 和 apt 软件包；上游源码版本与配置已记录。工具链软件包随更新可能变化，清单中的二进制哈希对应首次构建环境，不要求未来工具链更新后的产物逐字节相同。

## 重新组装整盘镜像

先把上述官方压缩镜像放到仓库根目录，执行：

```sh
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/package" -w /package firefly-batocera-build:20261102 \
  python3 make-image.py batocera-rk3288-miqi-39-20240301.img.gz rebuilt.img
gzip -1 -n rebuilt.img
```

脚本先核对基础 SHA-256，要求输出是新的普通 `.img` 文件，拒绝覆盖已有路径；不接收块设备。组装时保留官方内核、initrd、SquashFS 系统和 SHARE 分区，替换引导区域、DTB、extlinux，将板型标识改为 firefly-rk3288，并加入日志脚本。不同 mtools 写入时间会使整盘镜像哈希不同；关键文件可比对 `source/uboot-manifest.json` 和 [验证记录](TESTING.md) 中的校验值。

布局（每扇区 512 字节）：

| 内容 | 偏移/起始扇区 | 大小 |
| --- | --- | --- |
| MBR | 0 | 512 字节 |
| Firefly idbloader | 32 KiB / 64 | 63,488 字节 |
| Firefly u-boot-dtb.img | 8 MiB / 16,384 | 554,688 字节 |
| BATOCERA FAT32 | 16 MiB / 32,768 | 4 GiB |
| SHARE ext4 | 4,311,744,512 / 8,421,376 | 512 MiB，首启扩容 |

完整 `.img` 大小为 4,848,615,424 字节。引导区原来的 MiQi loader 和环境区域在写入 Firefly loader 前清零。新的 U-Boot 不读取或保存持久环境；它自己的设备编号中 SD 是 `mmc1`。该编号不应用于用户板上现有的未知旧 U-Boot。
