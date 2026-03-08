# ifly2code

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.2-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

**iFlytek MaaS Proxy Service - Enable Claude Code with iFlytek Models**

[Features](#features) • [Quick Start](#quick-start) • [Usage Flow](#usage-flow) • [Configuration](#configuration) • [FAQ](#faq)

[简体中文](README.md)

</div>

---

## Introduction

**ifly2code** is a local proxy service that enables **Claude Code** to use various large language models from the iFlytek MaaS platform.

**How it works:**
- Receives Anthropic API requests from Claude Code
- Converts to OpenAI API format and forwards to iFlytek MaaS
- Converts responses back to Anthropic format for Claude Code

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

## Usage Flow

These steps describe the normal workflow for using the GUI proxy and explain what configuration changes happen at each stage so you know when to restart Claude Code and when manual intervention is required.

1. **Start the app and load saved settings** — Run `python main.py` (or double-click `ifly2code-gui.exe`). The window reads or creates `config.json`, pre-fills the API key, Base URL, and model fields with the last saved values, and prepares the UI for a quick restart.
2. **Choose a model and enter API Key/Base URL** — Pick the MaaS model you want from the dropdown, paste the API key, and only edit the Base URL if you operate in a different region (e.g., `https://maas-api.cn-huabei-1.xf-yun.com/v2`). Advanced settings such as `lora_id` and `search_disable` should generally stay at their defaults unless you have a specific need. Click “Save” and the app writes these values back to `config.json`, refreshing the internal model list so Claude Code sees the latest selection.
3. **Start the proxy and sync Claude’s settings** — Clicking “Start Proxy” launches the local server and rewrites Claude Code’s `settings.json` (usually located at `~/.claude/claude_code_settings.json`) with `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>`, `ANTHROPIC_AUTH_TOKEN=sk-proxy-key`, the selected model, and the configured MaaS base URL so Claude sends traffic through the proxy.
4. **Restart Claude Code** — Claude caches the previous configuration, so restarting the client forces it to reload the rewritten settings and stop sending requests to the old host.
5. **Run `/model` to verify the current model** — Type `/model` inside Claude Code; the response echoes the model from the active settings file, confirming the proxy setup worked.

Saving always rewrites `config.json`, starting the proxy updates Claude’s `settings.json`, and advanced settings stay untouched unless you edit them manually. Restarting Claude and using `/model` are the safest ways to confirm everything has been refreshed.

## Configuration

### Application Configuration

On first run, a configuration file will be automatically generated (located at `~/.claude/ifly_code_settings.json`):

```json
{
  "models": [
    {
      "name": "Kimi K2.5",
      "api_key": "your-api-key",
      "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
      "model_id": "xopkimik25",
      "max_tokens": 32768,
      "temperature": 0.7,
      "lora_id": "0",
      "search_disable": true,
      "enable_thinking": false,
      "disable_tools": false,
      "fix_host_header": false
    }
  ],
  "current_model": "Kimi K2.5",
  "proxy": {
    "host": "127.0.0.1",
    "port": 8080
  },
  "app": {
    "autostart": false,
    "minimize_to_tray": true,
    "log_level": "INFO"
  }
}
```

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `name` | Model display name |
| `api_key` | iFlytek MaaS Platform API Key |
| `base_url` | API request endpoint (supports v1/v2) |
| `model_id` | Model ID |
| `max_tokens` | Maximum output tokens |
| `temperature` | Temperature parameter (0-1) |
| `disable_tools` | Disable tool calls (for old model compatibility) |
| `enable_thinking` | Enable thinking mode |
| `port` | Local proxy listening port |

### Claude Code Configuration

The app **automatically updates** Claude Code configuration on startup. Manual setup is usually not required.

For manual configuration or troubleshooting, you can set these environment variables:

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

## Release Notes

### 1.0.2 Experience Optimization

- Added update check caching mechanism to avoid frequent network requests (24-hour cache)
- Auto-select model after editing for smoother operation
- Support configuration hot reload without restarting the application
- Enhanced tool call compatibility with automatic handling of unsupported parameters for older models
- Fixed Host header signature issue (optional configuration)

### 1.0.1 Stability Enhancement

- Migrated user configuration to `~/.claude/ifly_code_settings.json` with automatic Claude Code settings sync for clear multi-model management
- Added GitHub Release update checker with background notifications and download dialog
- Proxy layer improvements: `_call_with_fallback` copies request data before degradation; tools/enable_thinking/streaming errors auto-retry with fallback; HTTP fallback accepts `application/json` with `charset`
- Both streaming and non-streaming responses pass `has_tool_calls` to `map_stop_reason`; tool call stop_reason is always `tool_use`
- Logs and tray continue to provide runtime status with more stable proxy for better Claude Code experience on MaaS

### 1.0.0 Initial Release

- Provides Anthropic↔OpenAI proxy channel between Claude Code and iFlytek MaaS
- Includes PySide6 GUI, system tray, real-time logs, model management panel, and auto-sync configuration
- Supports direct Python execution and exe package with quick start guide, configuration docs, and FAQ

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
