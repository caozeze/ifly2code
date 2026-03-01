# 打包指南 - 讯飞星辰 MaaS 代理服务

> Powered by zecao

本文档说明如何将 `ifly2code` 应用打包成独立的 Windows 可执行文件。

## 目录

- [环境准备](#环境准备)
- [打包步骤](#打包步骤)
- [打包后文件说明](#打包后文件说明)
- [分发说明](#分发说明)
- [常见问题](#常见问题)

---

## 环境准备

### 1. 确保已安装 Python

```bash
python --version
```

建议使用 Python 3.9 - 3.11

### 2. 安装依赖

```bash
cd ifly2code-gui
pip install -r requirements.txt
```

### 3. 安装 PyInstaller

```bash
pip install pyinstaller
```

---

## 打包步骤

### 方法一：使用打包脚本（推荐）

```bash
# 基础打包
python build.py

# 清理之前的构建后重新打包
python build.py --clean
```

### 方法二：手动使用 PyInstaller

```bash
pyinstaller main.py \
    --name=ifly2code \
    --onedir \
    --windowed \
    --add-data="config.json.example;." \
    --hidden-import=PyQt5 \
    --hidden-import=openai \
    --hidden-import=flask \
    --collect-all=PyQt5 \
    --clean \
    --noconfirm
```

### 方法三：单文件打包（体积更小，启动稍慢）

如果希望打包成单个 exe 文件：

```bash
pyinstaller main.py \
    --name=ifly2code \
    --onefile \
    --windowed \
    --add-data="config.json.example;." \
    --hidden-import=PyQt5 \
    --hidden-import=openai \
    --hidden-import=flask \
    --clean \
    --noconfirm
```

---

## 打包后文件说明

打包完成后，在 `dist/ifly2code/` 目录下会生成以下文件：

```
dist/ifly2code/
├── ifly2code.exe          # 主程序
├── start.bat              # 快速启动脚本
├── start_debug.bat        # 调试模式启动（显示控制台）
├── README.txt             # 使用说明
├── config.json.example    # 配置文件示例
└── [依赖库文件]           # PyQt5、Flask 等依赖
```

---

## 分发说明

### 打包成压缩包

使用以下命令创建分发压缩包：

```bash
# 使用 PowerShell
Compress-Archive -Path dist\ifly2code -DestinationPath ifly2code-v1.0.0.zip

# 或使用 7-Zip / WinRAR 手动压缩
```

### 分发包内容

将 `dist/ifly2code/` 整个目录打包分发给用户。

用户需要：
1. 解压缩到任意目录
2. 双击 `ifly2code.exe` 或 `start.bat` 启动

---

## 常见问题

### 1. 杀毒软件误报

**问题**: 某些杀毒软件可能将 PyInstaller 打包的程序识别为病毒。

**解决**:
- 添加到白名单
- 使用代码签名证书（需要购买）

### 2. 缺少 VC++ 运行库

**问题**: 启动时提示缺少 mfc140.dll 或类似文件。

**解决**: 安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 3. 打包后程序无法启动

**检查步骤**:
1. 运行 `start_debug.bat` 查看错误信息
2. 检查是否被防火墙拦截
3. 确认所有依赖文件都存在

### 4. 减小打包体积

**方法**:
- 使用 `--onefile` 模式
- 添加 `--exclude-module` 排除不需要的模块
- 使用 UPX 压缩（需要单独安装）

---

## 技术细节

### 版本信息

在打包时，版本信息硬编码在 `build.py` 中：

```python
APP_NAME = "ifly2code"
APP_DISPLAY_NAME = "讯飞星辰代理服务"
APP_VERSION = "1.0.0"
APP_AUTHOR = "zecao"
```

### 添加图标

准备一个 `.ico` 文件（推荐 256x256），放在 `assets/` 目录下：

```bash
# 在 build.py 中取消注释并修改：
--icon=assets/icon.ico
```

### 数字签名

为 exe 添加数字签名可以避免杀毒软件误报：

```bash
signtool sign /f certificate.pfx /p password dist/ifly2code/ifly2code.exe
```

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2025-02 | 初始版本，支持多模型配置 |

---

**Created by zecao**
