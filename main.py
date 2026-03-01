#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞星辰MaaS代理GUI应用 - 主入口

这是应用的启动入口，负责初始化应用并启动主窗口。
支持命令行参数和单实例运行。
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from src.config import get_config
from src.logger import setup_logger
from src.gui.main_window import MainWindow


def main():
    """应用主函数"""
    # 创建QApplication实例
    app = QApplication(sys.argv)
    app.setApplicationName("讯飞星辰MaaS代理服务")
    app.setOrganizationName("ifly2code")

    # 设置应用样式
    app.setStyle('Fusion')

    # 强制使用浅色主题（覆盖系统深色模式）
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.Highlight, QColor(76, 163, 224))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    # 初始化日志
    config = get_config()
    log_level = config.get('app.log_level', 'INFO')
    logger = setup_logger(level=log_level)

    logger.info("=" * 60)
    logger.info("讯飞星辰MaaS代理GUI应用启动")
    logger.info("=" * 60)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 运行应用事件循环
    exit_code = app.exec_()

    logger.info("应用退出")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
