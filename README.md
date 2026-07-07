# Xray Pilot

一个纯 Python 的命令行代理工具包，提供节点管理、代理服务控制、健康检查和自动切换等功能，支持 xray 后端。

## 特性

- 支持 VMess、VLESS、Trojan、Shadowsocks 协议
- 智能节点健康检测（延迟/连通性）
- 自动节点切换（基于延迟阈值）
- 订阅自动导入（Base64/JSON/Clash 格式）
- macOS 系统代理集成
- 灵活的路由规则管理（代理/直连/拦截）

## 安装

> **说明**：本工具是一个 Python CLI，需要先安装 [Xray-core](https://github.com/XTLS/Xray-core) 作为代理后端。整个安装过程可交给你的 AI 助手完成——把本章节内容发给它，并告知你的操作系统，它应能端到端帮你装好。安装完成后，工具的配置默认与 Xray 官方安装路径一致，无需手动改任何配置即可使用。

### 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.8+ | 运行 CLI 工具本体 |
| **Xray-core** | **v26.3.27**（固定） | 代理后端，请安装此版本 |

> **为什么固定 Xray 版本？** 不同版本的 Xray-core 在协议实现、配置字段上可能存在差异。本工具已基于 `v26.3.27` 验证通过，请安装该版本以确保兼容。如需升级到更新版本，请先在本仓库内验证后再调整。

### 第一步：安装 Xray-core（固定版本）

Xray 官方提供安装脚本，支持通过 `--version` 参数安装指定版本。在终端执行：

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install --version v26.3.27
```

安装完成后：

- 二进制文件位于 `/usr/local/bin/xray`（macOS / Linux，官方脚本默认路径）。
- 验证安装是否成功：

```bash
xray version
# 应输出类似：Xray 26.3.27 (Xray, Penetrates Everything.)
```

<details>
<summary>macOS 用户：若没装 Homebrew 的 curl/cert，或上述命令失败，可改用以下方式</summary>

```bash
# 1. 下载安装脚本
curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh -o /tmp/install-release.sh

# 2. 用固定版本执行安装
bash /tmp/install-release.sh install --version v26.3.27

# 3. 清理
rm /tmp/install-release.sh
```

Windows 用户：官方脚本不支持 Windows，请从 [Xray-core Releases](https://github.com/XTLS/Xray-core/releases/tag/v26.3.27) 下载对应 `windows.zip`，解压后将 `xray.exe` 放到某个目录（如 `C:\xray\xray.exe`），并在安装本工具后把 `settings.json` 里的 `xray_bin` 指向该路径。
</details>

### 第二步：安装 Xray Pilot

从源码安装（开发模式）：

```bash
git clone https://github.com/xhqing/xray-pilot.git
cd xray-pilot
pip install -e .
```

或仅安装依赖后直接以模块方式运行：

```bash
pip install click 'requests[socks]' pyyaml
python3 -m xray_pilot.cli --help
```

安装完成后，会得到 `xray-pilot` 命令：

```bash
xray-pilot --help
```

> **默认配置无需改动**：`xray-pilot init` 生成的默认配置中，`xray_bin` 已指向 `/usr/local/bin/xray`，与上一步官方脚本的安装路径一致。若你把 xray 装在了其他位置（例如 Windows 或自定义路径），修改 `~/.xray-pilot/settings.json`（或项目 `config/settings.json`）里的 `xray_bin` 字段指向实际路径即可。

### 第三步：交给 AI 助手安装（可选）

如果你不想手动执行上述命令，可以直接把本章节内容复制给你的 AI 助手（Claude、ChatGPT、Gemini 等），并附上：

- 你的操作系统（macOS / Windows / Linux 发行版）和芯片架构（Apple Silicon / Intel / x64 / arm64）
- 你已有的代理节点信息（如有），或让助手引导你用 `xray-pilot node add` 添加

AI 助手应能：识别并安装固定版本 `v26.3.27` 的 Xray-core → 安装本工具 → `xray-pilot init` 初始化 → 协助你添加节点并启动代理。

## 快速开始

```bash
# 1. 初始化配置
xray-pilot init

# 2. 添加节点
xray-pilot node add --name "My Node" --protocol vmess --address server.example.com --port 443 --uuid your-uuid

# 3. 启动代理（自动选择最快节点）
xray-pilot start

# 4. 查看状态
xray-pilot status

# 5. 测试所有节点连通性
xray-pilot test --all-nodes

# 6. 停止代理
xray-pilot stop
```

## 常用命令

日常使用最频繁的命令：

| 命令 | 说明 | 示例 |
|------|------|------|
| `xray-pilot start` | 启动代理服务（自动选择最快节点） | `xray-pilot start` |
| `xray-pilot stop` | 停止代理服务 | `xray-pilot stop` |
| `xray-pilot status` | 查看代理运行状态 | `xray-pilot status -v` |
| `xray-pilot restart` | 重启代理服务（自动选择最快节点） | `xray-pilot restart` |
| `xray-pilot test --all-nodes` | 测试所有节点延迟和连通性 | `xray-pilot test -a` |

---

## 命令详解

### 基础命令

#### `init` - 初始化配置文件

在 `~/.config/xray-pilot/` 目录下创建默认配置文件（`nodes.json`、`routing.json`、`settings.json`）。

```bash
xray-pilot init
```

强制覆盖已有配置：

```bash
xray-pilot init -f
```

---

#### `start` - 启动代理服务

启动 xray 代理进程并设置系统代理。

使用默认节点启动：

```bash
xray-pilot start
```

使用指定节点启动：

```bash
xray-pilot start my_node
```

---

#### `stop` - 停止代理服务

停止 xray 进程并关闭系统代理。

```bash
xray-pilot stop
```

---

#### `restart` - 重启代理服务

先停止再启动，使用当前默认节点。

```bash
xray-pilot restart
```

---

#### `status` - 查看代理状态

显示代理是否运行、当前节点、端口等信息。

```bash
xray-pilot status
```

显示详细信息：

```bash
xray-pilot status -v
```

---

#### `switch` - 切换节点

切换到指定节点并重启代理服务。

```bash
xray-pilot switch another_node
```

---

### 节点管理命令

#### `node list` - 列出所有节点

显示所有已保存的节点信息（ID、名称、协议、地址、延迟）。

```bash
xray-pilot node list
```

按分组筛选：

```bash
xray-pilot node list -g work
```

---

#### `node add` - 添加节点

向配置中添加一个新的代理节点。

添加 VMess 节点：

```bash
xray-pilot node add --name "日本节点" --protocol vmess --address jp.example.com --port 443 --uuid xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --tls --servername jp.example.com
```

添加 Trojan 节点：

```bash
xray-pilot node add --name "美国节点" --protocol trojan --address us.example.com --port 443 --password yourpassword --tls
```

添加 Shadowsocks 节点：

```bash
xray-pilot node add --name "SS节点" --protocol ss --address ss.example.com --port 8388 --password ss_password --security chacha20-ietf-poly1305
```

添加 VLESS 节点：

```bash
xray-pilot node add --name "VLESS节点" --protocol vless --address vless.example.com --port 443 --uuid xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --tls --network ws --servername vless.example.com
```

带分组添加：

```bash
xray-pilot node add --name "工作节点" --protocol vmess --address work.example.com --port 443 --uuid work-uuid --group work
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--name` | str | 是 | 节点名称 |
| `--protocol` | str | 是 | 协议类型（vmess/vless/trojan/ss） |
| `--address` | str | 是 | 服务器地址 |
| `--port` | int | 是 | 服务器端口 |
| `--uuid` | str | 部分 | UUID（VMess/VLESS 必填） |
| `--password` | str | 部分 | 密码（Trojan/SS 必填） |
| `--alter-id` | int | 否 | VMess alterId，默认 0 |
| `--security` | str | 否 | 加密方式，默认 auto |
| `--network` | str | 否 | 传输层（tcp/ws/h2/grpc），默认 tcp |
| `--tls` | flag | 否 | 是否启用 TLS |
| `--servername` | str | 否 | TLS 服务器名称（SNI） |
| `--group` | str | 否 | 分组名称，默认 default |

---

#### `node remove` - 删除节点

从配置中删除指定节点。

```bash
xray-pilot node remove my_node
```

---

#### `node edit` - 编辑节点

修改已有节点的配置信息。

修改节点名称：

```bash
xray-pilot node edit my_node --name "新名称"
```

修改服务器地址：

```bash
xray-pilot node edit my_node --address new.example.com
```

修改端口：

```bash
xray-pilot node edit my_node --port 8443
```

修改分组：

```bash
xray-pilot node edit my_node --group work
```

修改 UUID：

```bash
xray-pilot node edit my_node --uuid new-uuid-here
```

修改 TLS 设置：

```bash
xray-pilot node edit my_node --tls --servername new.example.com
```

---

#### `node import` - 从订阅导入节点

从订阅链接解析并批量导入节点。支持 Base64、JSON、Clash 格式。

```bash
xray-pilot node import "https://example.com/subscription/link"
```

---

#### `node export` - 导出节点配置

将当前所有节点导出为 JSON 或 YAML 格式。

导出为 JSON：

```bash
xray-pilot node export
```

导出为 YAML：

```bash
xray-pilot node export -f yaml
```

---

### 测试命令

#### `test` - 测试节点连通性

测试节点的延迟和连通性。

测试指定节点：

```bash
xray-pilot test my_node
```

测试所有节点：

```bash
xray-pilot test --all-nodes
```

使用简写：

```bash
xray-pilot test -a
```

测试当前默认节点：

```bash
xray-pilot test --current
```

测试指定分组的所有节点：

```bash
xray-pilot test --group work
```

---

### 路由规则命令

#### `routing list` - 查看路由规则

列出当前所有代理、直连、拦截规则。

```bash
xray-pilot routing list
```

---

#### `routing add` - 添加路由规则

添加新的路由规则到代理、直连或拦截列表。

添加代理规则：

```bash
xray-pilot routing add proxy "geosite:google"
```

添加直连规则：

```bash
xray-pilot routing add direct "geosite:cn"
```

添加拦截规则：

```bash
xray-pilot routing add block "geosite:ads"
```

---

#### `routing remove` - 删除路由规则

从所有规则列表中移除指定规则。

```bash
xray-pilot routing remove "geosite:google"
```

---

### 域名路由命令（特定网站走特定节点）

通过域名路由功能，可以让指定的域名使用特定的代理节点。例如让 GitHub 走专门的节点，而其他流量走默认节点。

#### `routing domain add` - 添加域名路由规则

将一组域名指向指定的代理节点。

让 GitHub 相关域名走 `github_node` 节点：

```bash
xray-pilot routing domain add -d github.com -d '*.github.io' -d api.github.com -n github_node --desc "GitHub"
```

让 OpenAI 走另一个节点：

```bash
xray-pilot routing domain add -d openai.com -d '*.openai.com' -d chatgpt.com -n openai_node --desc "OpenAI"
```

让 Google 服务走专属节点：

```bash
xray-pilot routing domain add -d google.com -d '*.google.com' -d youtube.com -d '*.youtube.com' -n google_node --desc "Google & YouTube"
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `-d, --domains` | str | 是 | 域名模式，可多次指定 |
| `-n, --node` | str | 是 | 目标节点的 ID |
| `--desc` | str | 否 | 规则描述，默认使用域名列表 |

---

#### `routing list` - 查看路由规则（含域名路由）

列出当前所有代理、直连、拦截规则以及域名到节点的映射规则。

```bash
xray-pilot routing list
```

输出示例：

```
Proxy rules:
  [PROXY] geosite:google

Direct rules:
  [DIRECT] geosite:cn

Domain-to-node rules:
  [0] GitHub -> github_node
  [1] OpenAI -> openai_node
```

其中 `[0]`、`[1]` 是规则的索引编号，删除时使用。

---

#### `routing domain remove` - 删除域名路由规则

通过索引删除指定的域名规则。

删除索引为 0 的规则：

```bash
xray-pilot routing domain remove 0
```

---

#### `routing domain clear` - 清空所有域名路由规则

删除所有域名到节点的映射规则。

```bash
xray-pilot routing domain clear
```

强制清空（不确认）：

```bash
xray-pilot routing domain clear -f
```

---

### 订阅管理命令

#### `subscription add` - 添加订阅源

保存一个订阅链接供后续更新使用。

```bash
xray-pilot subscription add "https://example.com/subscription" --name "My Subscription"
```

---

#### `subscription update` - 更新订阅

从已保存的订阅源导入节点。

更新所有订阅源：

```bash
xray-pilot subscription update
```

更新指定订阅源：

```bash
xray-pilot subscription update "My Subscription"
```

---

#### `subscription list` - 列出订阅源

显示所有已保存的订阅源。

```bash
xray-pilot subscription list
```

---

#### `subscription remove` - 删除订阅源

移除一个已保存的订阅源。

```bash
xray-pilot subscription remove "My Subscription"
```

---

### 配置管理命令

#### `config show` - 查看当前配置

显示 `settings.json` 的全部内容。

```bash
xray-pilot config show
```

---

#### `config set` - 设置配置项

修改设置文件中的配置值，支持点符号路径访问嵌套配置。

修改日志级别：

```bash
xray-pilot config set log_level debug
```

修改 SOCKS 端口：

```bash
xray-pilot config set socks_port 7890
```

启用自动切换：

```bash
xray-pilot config set auto_switch.enabled true
```

修改自动切换阈值：

```bash
xray-pilot config set auto_switch.threshold 300
```

启用系统代理：

```bash
xray-pilot config set system_proxy.enabled true
```

---

#### `config reset` - 重置配置

将所有配置文件恢复为默认值。

```bash
xray-pilot config reset
```

强制重置（不确认）：

```bash
xray-pilot config reset -f
```

---

## 配置文件

配置文件位于 `~/.config/xray-pilot/`：

| 文件 | 用途 |
|------|------|
| `nodes.json` | 节点配置（地址、协议、UUID 等） |
| `routing.json` | 路由规则（代理/直连/拦截列表） |
| `settings.json` | 全局设置（端口、xray 路径、自动切换等） |

### settings.json 字段说明

```json
{
  "xray_bin": "/usr/local/bin/xray",
  "socks_port": 1080,
  "http_port": 1087,
  "log_level": "warning",
  "log_file": "/tmp/xray-pilot.log",
  "auto_switch": {
    "enabled": false,
    "interval": 300,
    "strategy": "latency",
    "threshold": 200
  },
  "subscription": {
    "auto_update": false,
    "update_interval": 3600
  },
  "system_proxy": {
    "enabled": true,
    "bypass_local": true
  }
}
```

---

## VPS 服务商对比（自建代理）

> 以下按**国内访问速度**和**性价比**排序，适合搭建代理服务或建站使用。

| 服务商 | 官网地址 | 年付约 | CN2 GIA | 优势 | 劣势 |
|---|---|---|---|---|---|
| **搬瓦工** (BandwagonHost) | https://bandwagonhost.com<br>https://bwh81.net | $50-170 | 有 | 老牌稳定，线路优秀，支持支付宝/微信 | 价格偏贵，热门套餐常缺货 |
| **DMIT** | https://www.dmit.io | $90-120 | 有 | 洛杉矶 CN2 GIA 线路极好，延迟低 | 价格较高，特价经常缺货 |
| **Vultr** | https://www.vultr.com | $30-60 | 有(加价) | 全球 17+ 机房，按小时计费，支持支付宝 | CN2 GIA 需额外付费，普通线路质量一般 |
| **DigitalOcean** | https://www.digitalocean.com | $48-120 | 无 | 开发者友好，文档完善，按小时计费 | 国内线路差，无优化回国线路 |
| **HostDare** | https://hostdare.com | $20-40 | 有 | 有 CN2 GIA 和香港节点，性价比高 | 品牌知名度一般，偶尔有售后问题 |
| **CloudCone** | https://cloudcone.com | $20-30 | 无 | 超便宜，洛杉矶 MC 机房，按小时计费 | 普通线路，晚高峰延迟较高 |
| **RackNerd** | https://racknerd.com | $18-25 | 无 | 地板价，多机房可选，支持支付宝 | 线路一般，特价常缺货 |
| **ColoCrossing** | https://www.cologix.com | $15-20 | 无 | 极便宜，适合练手/探针 | 延迟 180-220ms，不适合代理 |
| **AWS** | https://aws.amazon.com | 免费层 | 无 | 有免费层 (12个月)，全球覆盖 | IP 段容易被封，免费层限制多 |
| **GCP** | https://cloud.google.com | 免费层 | 无 | 有 $300 免费额度，全球覆盖 | IP 段容易被封，新手配置复杂 |

### 选购建议

| 需求 | 推荐 |
|---|---|
| **追求极致速度和稳定** | 搬瓦工、DMIT（CN2 GIA） |
| **性价比优先** | HostDare（有 CN2 GIA）、RackNerd |
| **便宜够用就行** | CloudCone、RackNerd |
| **需要多节点/灵活** | Vultr、DigitalOcean |
| **开发测试为主** | AWS 免费层、GCP 免费额度 |
| **香港节点** | 搬瓦工、HostDare |

---

## JMS (Just My Socks) 官网及镜像站

> Just My Socks 是搬瓦工官方推出的代理服务（机场），所有站点数据完全互通，账号同步。

| 站点 | 地址 | 国内可访问 | 说明 |
|---|---|---|---|
| **官网主站** | https://justmysocks.net | ❌ 被 DNS 污染 | 原生官方网站 |
| 镜像站 1 | https://justmysocks1.net | ❌ 被墙 | 数据与主站互通 |
| 镜像站 2 | https://justmysocks2.net | ❌ 部分地区被墙 | 数据与主站互通 |
| **镜像站 3** | https://justmysocks3.net | ✅ 可访问 | **推荐国内使用** |
| 镜像站 4 | https://justmysocks5.net | ❌ 部分地区被墙 | 备用镜像 |
| **镜像站 5** | https://justmysocks6.net | ✅ 可访问 | **推荐国内使用** |

### 说明

1. **所有站点完全互通**：官网和所有镜像站的数据（账号、订单、服务）完全一致，仅域名不同
2. **国内访问**：`justmysocks3.net` 和 `justmysocks6.net` 是国内网络环境下最稳定的可访问地址
3. **优惠码**：`JMS9272283`（5.2% 终身折扣，可与年付优惠叠加）
4. **支付方式**：支持支付宝、PayPal
5. **退款政策**：7 天无理由退款
6. **套餐起价**：LA 500 套餐 $5.88/月（500GB @ 2.5Gbps）

---

## 备用服务

### CyLink

> [cylink.vip](https://cylink.vip) 可作为 JMS 之外的备用代理服务。

| 项目 | 信息 |
|---|---|
| 官网 | https://cylink.vip |
| 支付方式 | 支持支付宝、PayPal 等 |

---

## 搬瓦工教程网 & 优惠码备忘

> 搬瓦工教程网整理了大量搬瓦工 VPS 和 JMS 的教程、优惠码、套餐对比等信息。

| 网站 | 地址 | 说明 |
|---|---|---|
| **搬瓦工教程网** | https://www.bwgss.org | 搬瓦工 + JMS 教程、套餐指南、客户端配置 |
| **搬瓦工中文网** | https://www.bandwagonhost.net | 搬瓦工中文教程、优惠通知、补货提醒 |
| **搬瓦工优惠网** | https://www.bwgyhw.cn | 搬瓦工优惠码实时更新、库存监控 |
| **搬瓦工百科** | https://bwg.net | 搬瓦工方案整理、教程汇总 |
| **搬瓦工补货通知** | https://stock.bwg.net | 实时库存监控 |
| **搬瓦工库存监控** | https://status.bwgyhw.cn | 库存状态实时查看 |

### 搬瓦工优惠码（历史汇总，仅供参考，请以官网实际为准）

| 优惠码 | 折扣 | 状态 | 说明 |
|---|---|---|---|
| `NODESEEK2026` | 6.77% | 已失效（2026.3） | NodeSeek 社区专属，仅上线约 2 天 |
| `ILOVEBANDWAGON` | 11% | 已失效（2025.11） | 双十一限时活动 |
| `BWHCGLUKKB` | 6.58% | 已失效 | 曾长期可用，2025年底取消 |
| `ireallyreadtheterms8` | 5.5% | 已失效 | 阅读服务条款获取 |
| `BWHCCNCXVV` | 6.78% | 已失效 | - |
| `BWHWYWWYVY` | 5.96% | 已失效 | - |
| `BWHZCCWCCZ` | 5.8% | 已失效 | - |
| `BWH2021BF` | 10% | 已失效 | 2021 黑五活动 |
| `BWH20201111` | 11% | 已失效 | 2020 双十一活动 |

> **注意**：自 2025 年底起，搬瓦工取消了常规循环优惠码，目前购买需按原价结算。优惠码通常在双十一、黑五等大促期间临时放出，建议关注上方教程网站获取最新优惠通知。

### 关注渠道

- **QQ 群**：697178487 / 554576821 / 451796455（禁言通知群）
- **TG 频道**：[@BandwagonHostNews](https://t.me/BandwagonHostNews)
- **微信公众号**：搬砖部落

---

## 常见问题

### Q: 启动代理失败？

- 确认 xray 已正确安装：`which xray`
- 检查端口是否被占用
- 查看日志：`cat /tmp/xray-pilot.log`

### Q: 系统代理无法设置？

- macOS 上设置系统代理需要网络权限
- 可以在系统设置 → 网络 → 高级 → 代理中手动检查

### Q: 健康检查超时？

- 检查网络连接是否正常
- 确认节点配置是否正确
- 增加测试超时时间

---
