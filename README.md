# 讯飞星辰MaaS代理GUI应用

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

一个简单易用的桌面代理应用，将讯飞星辰MaaS平台的API转换为Claude Code兼容格式

[功能特性](#功能特性) • [快速开始](#快速开始) • [配置说明](#配置说明) • [常见问题](#常见问题)

</div>

---

## 功能特性

- **图形化界面** - 简洁直观的PyQt5桌面应用
- **一键启动** - 轻松启动/停止代理服务
- **实时日志** - 彩色日志显示，轻松调试
- **系统托盘** - 后台运行，不占用任务栏
- **配置管理** - 可视化配置API参数
- **快捷复制** - 一键复制Claude Code配置命令

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

---

## 配置说明

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

启动代理后，在Claude Code中设置以下环境变量：

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
**A:** 在配置中修改 `port` 参数为其他端口（如8081、8082）

### Q2: 启动后Claude Code连接失败？
**A:** 检查以下几点：
1. 确认代理状态为"运行中"
2. 检查防火墙是否拦截
3. 确认环境变量设置正确

### Q3: 如何获取API Key和Model ID？
**A:** 登录讯飞星辰MaaS平台，在服务管控页面创建服务后获取

### Q4: 支持哪些模型？
**A:** 支持讯飞星辰MaaS平台的所有模型，包括：
- DeepSeek V3 & R1
- Qwen系列
- 其他开源模型

---

## 项目结构

```
ifly2code-gui/
├── main.py                 # 应用入口
├── config.json             # 配置文件
├── requirements.txt        # 依赖列表
├── README.md               # 项目文档
├── build.py                # 打包脚本
│
├── src/                    # 源代码
│   ├── config.py           # 配置管理
│   ├── logger.py           # 日志管理
│   ├── proxy/              # 代理服务器
│   │   ├── server.py       # Flask服务
│   │   └── converter.py    # 格式转换
│   ├── gui/                # 界面
│   │   ├── main_window.py  # 主窗口
│   │   ├── config_panel.py # 配置面板
│   │   ├── control_panel.py# 控制面板
│   │   ├── log_panel.py    # 日志面板
│   │   └── tray_icon.py    # 系统托盘
│   └── utils/              # 工具
│       └── process_helper.py
│
└── assets/                 # 资源文件
    └── icon.ico            # 图标
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

MIT License

---

## 联系方式

如有问题或建议，欢迎提Issue！

<div align="center">

Made with ❤️ by ifly2code

</div>
