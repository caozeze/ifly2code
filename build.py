#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本

用于将讯飞星辰MaaS代理GUI应用打包成独立的exe可执行文件。

使用方法:
    python build.py

打包后的文件位于 dist/ 目录下。
"""

import os
import sys
from pathlib import Path


def build():
    """执行打包"""
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
    except ImportError:
        print("错误: PyInstaller未安装")
        print("请运行: pip install pyinstaller")
        sys.exit(1)

    # 项目根目录
    project_root = Path(__file__).parent
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"

    # PyInstaller参数
    pyinstaller_args = [
        "pyinstaller",
        # 主程序入口
        "main.py",
        # 应用名称
        "--name=讯飞星辰代理服务",
        # 单文件模式（可选，改为单文件或单目录）
        "--onedir",
        # 窗口模式（不显示控制台）
        "--windowed",
        # 图标（如果有）
        # "--icon=assets/icon.ico",
        # 添加数据文件（config.json模板等）
        # "--add-data=config.json;.",
        # 隐藏导入（确保所有依赖都被包含）
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=openai",
        "--hidden-import=flask",
        # 清理构建目录
        "--clean",
        # 覆盖输出
        "--noconfirm",
    ]

    # 打印信息
    print("=" * 60)
    print("讯飞星辰MaaS代理GUI应用 - 打包工具")
    print("=" * 60)
    print(f"项目目录: {project_root}")
    print(f"输出目录: {dist_dir}")
    print()

    # 执行打包
    import subprocess
    os.chdir(project_root)

    print("开始打包...")
    result = subprocess.run(pyinstaller_args, capture_output=False)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("打包成功！")
        print("=" * 60)
        print(f"可执行文件位于: {dist_dir / '讯飞星辰代理服务'}")
        print()
        print("注意事项:")
        print("1. 首次运行会自动生成config.json配置文件")
        print("2. 请确保在运行前配置好API Key和Model ID")
        print("3. 防火墙可能会拦截程序，请允许网络访问")
    else:
        print()
        print("=" * 60)
        print("打包失败！")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    build()
