#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本 - 讯飞星辰MaaS代理GUI应用
Powered by zecao

用于将应用打包成独立的exe可执行文件。

使用方法:
    python build.py

打包后的文件位于 dist/ 目录下。
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# 应用信息
APP_NAME = "ifly2code"
APP_DISPLAY_NAME = "讯飞星辰代理服务"
APP_VERSION = "1.0.0"
APP_AUTHOR = "zecao"


def clean_build_dirs(project_root: Path) -> None:
    """清理之前的构建目录"""
    dirs_to_clean = ["build", "dist", f"{APP_NAME}.spec"]
    for dir_name in dirs_to_clean:
        path = project_root / dir_name
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"  清理: {dir_name}")


def build():
    """执行打包"""
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("错误: PyInstaller未安装")
        print("请运行: pip install pyinstaller")
        sys.exit(1)

    # 项目根目录
    project_root = Path(__file__).parent.absolute()
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"

    # 打印信息
    print("=" * 60)
    print(f"{APP_DISPLAY_NAME} - 打包工具")
    print("=" * 60)
    print(f"Powered by {APP_AUTHOR}")
    print(f"版本: {APP_VERSION}")
    print(f"项目目录: {project_root}")
    print(f"输出目录: {dist_dir}")
    print()

    # 询问是否清理
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        print("清理之前的构建...")
        clean_build_dirs(project_root)
        print()

    # PyInstaller参数 - 使用 python -m 调用确保能找到 PyInstaller
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        # 主程序入口
        "main.py",
        # 应用名称
        f"--name={APP_NAME}",
        # 单文件模式（生成单个exe，方便分发）
        "--onefile",
        # 窗口模式（不显示控制台）
        "--windowed",
        # 添加数据文件（配置模板）
        "--add-data=config.json.example;.",
        # 隐藏导入（确保所有依赖都被包含）
        "--hidden-import=PySide6",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=openai",
        "--hidden-import=flask",
        "--hidden-import=werkzeug",
        "--hidden-import=httpx",
        "--hidden-import=requests",
        # 收集所有PySide6相关文件
        "--collect-all=PySide6",
        # 排除不需要的模块（减小体积）
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=tkinter",
        # 清理构建目录
        "--clean",
        # 覆盖输出
        "--noconfirm",
    ]

    # 执行打包
    os.chdir(project_root)

    print("开始打包...")
    print("-" * 60)

    result = subprocess.run(pyinstaller_args, capture_output=False)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("打包成功！")
        print("=" * 60)
        print(f"可执行文件位于: {dist_dir / f'{APP_NAME}.exe'}")
        print()

        # 计算文件大小
        exe_path = dist_dir / f'{APP_NAME}.exe'
        if exe_path.exists():
            size = exe_path.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"文件大小: {size_mb:.1f} MB")

        print()
        print("使用说明:")
        print("1. 将 ifly2code.exe 复制到目标电脑")
        print("2. 双击 ifly2code.exe 启动程序")
        print("3. 首次运行会自动生成 config.json 配置文件")
        print("4. 请配置好 API Key 和 Model ID 后使用")
        print()
        print("注意事项:")
        print("- 防火墙可能会拦截程序，请允许网络访问")
        print("- 确保 Windows 系统已安装 VC++ 运行库")
        print("- 首次运行会自动生成 config.json 配置文件")

        # 创建简单的 README
        readme_txt = dist_dir / "README.txt"
        with open(readme_txt, "w", encoding="utf-8") as f:
            f.write(f'{APP_DISPLAY_NAME} v{APP_VERSION}\n')
            f.write('=' * 50 + '\n\n')
            f.write(f'Powered by {APP_AUTHOR}\n\n')
            f.write('使用说明:\n')
            f.write('-' * 30 + '\n')
            f.write('1. 双击 ifly2code.exe 启动程序\n')
            f.write('2. 首次运行会自动生成 config.json 配置文件\n')
            f.write('3. 点击"⚙ 模型管理"添加你的模型配置\n')
            f.write('4. 输入 API Key 和 Model ID\n')
            f.write('5. 点击"🚀 启动代理"开始服务\n\n')
            f.write('配置 CC Switch:\n')
            f.write('-' * 30 + '\n')
            f.write('- Base URL: http://127.0.0.1:8080\n')
            f.write('- API Key: sk-proxy-key (任意填写)\n')
            f.write('- Model: 你设置的 Model ID\n\n')
            f.write('注意事项:\n')
            f.write('-' * 30 + '\n')
            f.write('- 防火墙可能会拦截，请允许网络访问\n')
            f.write('- 程序最小化到系统托盘，双击托盘图标恢复窗口\n\n')
            f.write('技术支持:\n')
            f.write('-' * 30 + '\n')
            f.write(f'Created by {APP_AUTHOR}\n')

        print(f"\n已创建说明文档: {readme_txt}")

    else:
        print()
        print("=" * 60)
        print("打包失败！")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    build()
