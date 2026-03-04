# ifly2code

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

讯飞星辰 MaaS 代理服务 - 让 Claude Code 支持讯飞星辰大模型

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用流程](#使用流程) • [配置说明](#配置说明) • [常见问题](#常见问题)

[English](README_en.md)

</div>

---

## 简介

ifly2code 是一个本地代理服务，让 **Claude Code** 能够使用讯飞星辰 MaaS 平台的各种大模型。

**工作原理：**
- 接收 Claude Code 的 Anthropic API 请求
- 转换为 OpenAI API 格式转发到讯飞星辰
- 将讯飞的响应转换回 Anthropic 格式返回给 Claude Code

## 功能特性

- **图形化界面** - 简洁直观的 PySide6 桌面应用
- **一键启动** - 轻松启动/停止代理服务
- **多模型管理** - 可视化管理多个讯飞星辰模型配置
- **实时日志** - 彩色日志显示，轻松调试
- **系统托盘** - 后台运行，不占用任务栏
- **自动同步** - 自动更新 Claude Code 配置文件

---

## 快速开始

### 方法一：直接运行（需要Python环境）

1. **安装依赖**

```bash
pip install -r requirements.txt
```

2. **运行应用**

```bash
python main.py
```

### 方法二：使用exe（无需Python环境）

1. 下载 `ifly2code-gui.exe`
2. 双击运行即可

### 方法三：自行打包

查看 [打包指南 (BUILD.md)](BUILD.md) 了解如何自行编译打包。

---

## 使用流程

以下步骤展示了使用 GUI 代理的标准流程，同时说明了每一步背后会进行的配置更新，帮助你理解为什么需要重启 Claude Code 以及何时需要手动干预。

1. **启动应用并加载现有配置** – 运行 `python main.py`（或双击 `ifly2code-gui.exe`）。应用会读取或创建 `config.json`，并把之前保存的 API Key、Base URL 与模型预填入对应输入框，方便直接复用。
2. **选择模型与填写 API Key / Base URL** – 在模型下拉菜单中选中想用的 MaaS 模型，粘贴 API Key，只有在指定地区或自定义域名时才需要调整 Base URL（例如 `https://maas-api.cn-huabei-1.xf-yun.com/v2`）。高级设置（如 `lora_id`、`search_disable`）默认保持不动即可，只有特殊需求才要改。点击「保存」后，GUI 会把这些信息写回 `config.json`，并刷新内部模型列表供 Claude 使用。
3. **启动代理并同步 Claude 配置** – 点击「启动代理」会启动本地服务，并同步 Claude Code 的 `settings.json`（通常位于 `~/.claude/claude_code_settings.json`），写入 `ANTHROPIC_BASE_URL=http://127.0.0.1:<端口>`、`ANTHROPIC_AUTH_TOKEN=sk-proxy-key`、`ANTHROPIC_MODEL=<所选模型>` 以及所配置的 MaaS `base_url`，保证 Claude 通过本地代理请求讯飞星辰服务。
4. **重启 Claude Code** – Claude 会缓存旧的配置，必须重新打开才能加载被代理覆盖后的 `settings.json`，否则仍会请求旧的地址或模型。
5. **运行 `/model` 验证当前模型** – 在 Claude Chat 界面输入 `/model`，收到的回应会显示当前 `settings.json` 中的模型 ID，确认代理与模型都已经生效。

在上述流程中，点击「保存」会持续更新 `config.json`，启动代理会覆盖 Claude 的 `settings.json`，而高级设置则会默认保持当前值，除非你手动修改。每次重新启动 Claude 并运行 `/model`，都是确认代理配置被正确刷新的好方法。


### 应用配置

首次运行会自动生成 `config.json` 配置文件：

```json
{
  "api": {
    "api_key": "你的API Key",
    "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
    "model_id": "你的模型ID"
  },
  "proxy": {
    "host": "127.0.0.1",
    "port": 8080
  },
  "advanced": {
    "lora_id": "0",
    "search_disable": true
  }
}
```

### 配置项说明

| 参数 | 说明 |
|------|------|
| `api_key` | 讯飞星辰MaaS平台的API Key |
| `base_url` | API请求地址（支持v1/v2） |
| `model_id` | 模型ID |
| `port` | 本地代理监听端口 |

### Claude Code配置

应用启动后会**自动更新** Claude Code 的配置文件，通常无需手动配置。

如需手动配置或排查问题，可以设置以下环境变量：

**Windows CMD:**
```cmd
set ANTHROPIC_BASE_URL=http://127.0.0.1:8080
set ANTHROPIC_AUTH_TOKEN=sk-proxy-key
set ANTHROPIC_MODEL=你的模型ID
```

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:8080"
$env:ANTHROPIC_AUTH_TOKEN="sk-proxy-key"
$env:ANTHROPIC_MODEL="你的模型ID"
```

---

## 界面预览

### 主窗口
```
┌─────────────────────────────────────────┐
│  讯飞星辰 MaaS 代理服务    ─ □ ✕      │
├─────────────────────────────────────────┤
│  📋 配置                                │
│  ────────────────────────────────────  │
│  API Key:  [•••••••••••••••]  👁      │
│  Base URL: [https://...xf-yun.com/v2]  │
│  Model ID: [xopglm47blth2]             │
│  端口:     [8080]                       │
│                                         │
│  🎮 控制                                │
│  ────────────────────────────────────  │
│  [ 🚀 启动代理 ]  ● 状态: 已停止        │
│  [ 📋 复制配置 ]  ⏱ 运行时间: 00:00:00 │
│                                         │
│  📝 日志                                │
│  ────────────────────────────────────  │
│  ┌─────────────────────────────────┐  │
│  │ [INFO] 2024-02-28 10:30:00 ... │  │
│  │ [ERROR] 2024-02-28 10:30:01 ...│  │
│  └─────────────────────────────────┘  │
│  [清空日志]                            │
└─────────────────────────────────────────┘
```

### 系统托盘
- 🟢 绿色图标 = 代理运行中
- 🔴 红色图标 = 代理已停止
- 右键菜单：启动/停止、打开窗口、退出

---

## 常见问题

### Q1: 端口8080被占用怎么办？
**A:** 应用会自动检测端口占用，如果8080被占用会自动寻找可用端口（如8081、8082）。你也可以在配置中手动修改 `port` 参数。

### Q2: 启动后Claude Code连接失败？
**A:** 检查以下几点：
1. 确认代理状态为"运行中"
2. 检查防火墙是否拦截
3. 确认环境变量设置正确

### Q3: 如何获取API Key和Model ID？
**A:** 登录讯飞星辰MaaS平台，在服务管控页面创建服务后获取

### Q4: 支持哪些模型？

**A:** 支持讯飞星辰 MaaS 平台的所有兼容 OpenAI API 格式的模型，包括：

| 模型 | Model ID | 说明 |
|------|----------|------|
| Kimi K2.5 | `xopkimik25` | 月之暗面 Kimi |
| GLM5 | `xopglm5` | 智谱 GLM |
| Minimax M2.5 | `xminimaxm25` | MiniMax |

你还可以在模型管理中添加其他自定义模型。

---

## 发布记录

### 1.0.1 稳定性增强

- 迁移用户配置到 `~/.claude/ifly_code_settings.json`，并在 GUI 中自动同步 Claude Code 设置，实现清晰的多模型管理。
- 新增 GitHub Release 更新检查线程，主界面会在后台提示版本更新并跳出下载对话框。
- 代理层改进：`_call_with_fallback` 复制请求数据后再降级，工具/enable_thinking/流式错误可自动降级重试；HTTP fallback 接受带 `charset` 的 `application/json`。
- 流式与非流式响应都传递 `has_tool_calls` 给 `map_stop_reason`，工具调用的 stop_reason 始终是 `tool_use`。
- 日志与托盘继续提供运行状态，配合更稳定的代理，提升 Claude Code 在 MaaS 上的使用体验。

### 1.0.0 初始发布

- 提供 Claude Code 与讯飞星辰 MaaS 之间的 Anthropic↔OpenAI 代理通道。
- 包含 PySide6 GUI、系统托盘、实时日志、模型管理面板与自动同步配置的体验。
- 支持直接运行（Python）与 exe 包，文档里有快速开始、配置说明与常见问题。

---

## 项目结构

```
ifly2code-gui/
├── main.py                 # 应用入口
├── build.py                # 打包脚本
├── config.json.example     # 配置文件示例
├── requirements.txt        # 依赖列表
├── README.md               # 项目文档
├── BUILD.md                # 打包指南
│
├── src/                    # 源代码
│   ├── config.py           # 配置管理（支持多模型）
│   ├── logger.py           # 日志管理
│   ├── api_client.py       # API客户端
│   ├── proxy/              # 代理服务器
│   │   ├── server.py       # Flask服务
│   │   └── converter.py    # Anthropic↔OpenAI格式转换
│   └── gui/                # 图形界面
│       ├── main_window.py  # 主窗口
│       ├── model_dialog.py # 模型管理对话框
│       └── tray_icon.py    # 系统托盘
│
└── assets/                 # 资源文件
    └── (图标等)
```

---

## 开发计划

- [x] Phase 1: 项目初始化
- [x] Phase 2: 代理服务器核心功能
- [x] Phase 3: GUI主窗口
- [x] Phase 4: 系统托盘集成
- [x] Phase 5: 打包成exe

---

## 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [Anthropic](https://www.anthropic.com/) - Claude API
- [讯飞星辰](https://maas.xfyun.cn/) - MaaS 平台
- [PySide6](https://www.qt.io/) - GUI 框架

---

## 联系方式

如有问题或建议，欢迎提Issue！

<div align="center">

Made with ❤️

**Powered by zecao**

</div>
