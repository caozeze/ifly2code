# 减小打包体积的方法

> 当前打包配置已经排除了一些不必要的模块，但仍有优化空间

## 当前体积分析

PyInstaller 打包的 `--onefile` 模式会将以下内容打包：
- Python 解释器 (~15 MB)
- PyQt5 及其依赖 (~50-80 MB) - **这是主要体积来源**
- Flask, Werkzeug, openai, httpx (~30 MB)
- 其他依赖和 DLL (~20 MB)

**总计约 100-150 MB 是正常的**

---

## 优化方法

### 1. 使用精简的虚拟环境（推荐）

打包前创建一个只包含必要依赖的新环境：

```bash
# 创建新环境
conda create -n ifly-build python=3.11 -y
conda activate ifly-build

# 只安装必要依赖
pip install PyQt5==5.15.10
pip install Flask==3.0.0 Werkzeug==3.0.1
pip install "openai>=1.50.0,<2.0.0"
pip install "httpx>=0.24.0,<0.28.0"
pip install pyinstaller

# 然后打包
python build.py
```

### 2. 使用 UPX 压缩（可减少 30-50%）

```bash
# 下载 UPX: https://upx.github.io/

# 在 build.py 中添加或手动运行：
upx --best --lzma dist/ifly2code.exe
```

### 3. 排除更多不需要的模块

在 build.py 中已经排除了：
- matplotlib, numpy, pandas（科学计算）
- tkinter（自带的 GUI）

还可以考虑排除：
```python
"--exclude-module=PIL",           # 如果不用图像处理
"--exclude-module=email",         # 如果不用邮件功能
"--exclude-module=pydoc",         # 文档生成
"--exclude-module=doctest",       # 测试框架
```

### 4. 考虑更轻量的 GUI 框架

PyQt5 是最大的体积来源。如果介意体积，可以考虑：
- **tkinter**: Python 内置，体积小但界面简陋
- **Dear PyGui**: 更现代且体积小
- **Web 界面**: Flask + HTML，无需 PyQt

---

## 体积对比参考

| 配置 | 预估大小 |
|------|---------|
| 当前配置 (PyQt5 + --onefile) | 100-150 MB |
| 使用 UPX 压缩后 | 50-80 MB |
| --onedir 模式 | 150-200 MB（但启动更快） |
| 使用 tkinter 替代 PyQt5 | 30-50 MB |

---

## 结论

对于 PyQt5 应用，**100 MB 左右的体积是正常的**。如果用户只是自己使用，这个大小完全可以接受。

如果需要公开发布，可以：
1. 使用 UPX 压缩
2. 提供 --onedir 版本（虽然文件多，但用户下载体验更好）
3. 考虑制作安装程序（Inno Setup 等）
