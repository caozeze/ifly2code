# ifly2code

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

**iFlytek MaaS Proxy Service - Enable Claude Code with iFlytek Models**

[Features](#features) • [Quick Start](#quick-start) • [Configuration](#configuration) • [FAQ](#faq)

[简体中文](README.md)

</div>

---

## Introduction

**ifly2code** is a local proxy service that converts [Anthropic API](https://docs.anthropic.com/) format to [OpenAI API](https://platform.openai.com/) format, enabling **Claude Code** to use various large language models from the iFlytek MaaS platform.

## Features

- **Graphical Interface** - Clean and intuitive PySide6 desktop application
- **One-Click Launch** - Easily start/stop the proxy service
- **Multi-Model Management** - Visually manage multiple iFlytek model configurations
- **Real-time Logs** - Color-coded log display for easy debugging
- **System Tray** - Run in background without cluttering the taskbar
- **Auto Sync** - Automatically update Claude Code configuration files

---

## Quick Start

### Method 1: Run Directly (Requires Python)

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Run Application**

```bash
python main.py
```

### Method 2: Using EXE (No Python Required)

1. Download `ifly2code-gui.exe`
2. Double-click to run

### Method 3: Build Your Own

See [BUILD Guide (BUILD.md)](BUILD.md) for instructions on compiling and packaging.

---

## Configuration

### Application Configuration

On first run, a `config.json` configuration file will be automatically generated:

```json
{
  "api": {
    "api_key": "your-api-key",
    "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
    "model_id": "your-model-id"
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

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `api_key` | iFlytek MaaS Platform API Key |
| `base_url` | API request endpoint (supports v1/v2) |
| `model_id` | Model ID |
| `port` | Local proxy listening port |

### Claude Code Configuration

After starting the proxy, set the following environment variables in Claude Code:

**Windows CMD:**
```cmd
set ANTHROPIC_BASE_URL=http://127.0.0.1:8080
set ANTHROPIC_AUTH_TOKEN=sk-proxy-key
set ANTHROPIC_MODEL=your-model-id
```

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:8080"
$env:ANTHROPIC_AUTH_TOKEN="sk-proxy-key"
$env:ANTHROPIC_MODEL="your-model-id"
```

---

## Interface Preview

### Main Window
```
┌─────────────────────────────────────────┐
│  iFlytek MaaS Proxy Service    ─ □ ✕   │
├─────────────────────────────────────────┤
│  📋 Configuration                       │
│  ────────────────────────────────────  │
│  API Key:  [•••••••••••••••]  👁      │
│  Base URL: [https://...xf-yun.com/v2]  │
│  Model ID: [xopglm47blth2]             │
│  Port:     [8080]                       │
│                                         │
│  🎮 Control                             │
│  ────────────────────────────────────  │
│  [ 🚀 Start Proxy ]  ● Status: Stopped │
│  [ 📋 Copy Config ]  ⏱ Uptime: 00:00:00│
│                                         │
│  📝 Logs                                │
│  ────────────────────────────────────  │
│  ┌─────────────────────────────────┐  │
│  │ [INFO] 2024-02-28 10:30:00 ... │  │
│  │ [ERROR] 2024-02-28 10:30:01 ...│  │
│  └─────────────────────────────────┘  │
│  [Clear Logs]                          │
└─────────────────────────────────────────┘
```

### System Tray
- 🟢 Green icon = Proxy running
- 🔴 Red icon = Proxy stopped
- Right-click menu: Start/Stop, Open Window, Exit

---

## FAQ

### Q1: What if port 8080 is occupied?
**A:** The app automatically detects port conflicts. If port 8080 is occupied, it will automatically find an available port (e.g., 8081, 8082). You can also manually modify the `port` parameter in configuration.

### Q2: Claude Code fails to connect after startup?
**A:** Check the following:
1. Confirm proxy status shows "Running"
2. Check if firewall is blocking
3. Verify environment variables are set correctly

### Q3: How to get API Key and Model ID?
**A:** Log in to iFlytek MaaS platform and obtain them after creating a service on the service management page

### Q4: Which models are supported?

**A:** Supports all models on iFlytek MaaS platform that are compatible with OpenAI API format:

| Model | Model ID | Description |
|-------|----------|-------------|
| Kimi K2.5 | `xopkimik25` | Moonshot Kimi |
| GLM5 | `xopglm5` | Zhipu GLM |
| Minimax M2.5 | `xminimaxm25` | MiniMax |

You can also add other custom models in Model Management.

---

## Project Structure

```
ifly2code-gui/
├── main.py                 # Application entry point
├── build.py                # Build script
├── config.json.example     # Configuration example
├── requirements.txt        # Dependencies
├── README.md               # Project documentation
├── BUILD.md                # Build guide
│
├── src/                    # Source code
│   ├── config.py           # Configuration management (multi-model)
│   ├── logger.py           # Logging
│   ├── api_client.py       # API client
│   ├── proxy/              # Proxy server
│   │   ├── server.py       # Flask service
│   │   └── converter.py    # Anthropic↔OpenAI format converter
│   └── gui/                # Graphical interface
│       ├── main_window.py  # Main window
│       ├── model_dialog.py # Model management dialog
│       └── tray_icon.py    # System tray
│
└── assets/                 # Resource files
    └── (icons, etc.)
```

---

## Development Roadmap

- [x] Phase 1: Project initialization
- [x] Phase 2: Proxy server core functionality
- [x] Phase 3: GUI main window
- [x] Phase 4: System tray integration
- [x] Phase 5: Package as exe

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) - Claude API
- [iFlytek](https://maas.xfyun.cn/) - MaaS Platform
- [PySide6](https://www.qt.io/) - GUI Framework

---

## Contact

For questions or suggestions, feel free to open an Issue!

<div align="center">

Made with ❤️

**Powered by zecao**

</div>
