#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞星辰MaaS代理GUI应用 - 主入口

这是应用的启动入口，负责初始化应用并启动主窗口。
支持命令行参数和单实例运行。
"""

import sys
from PyQt5.QtWidgets import QApplication

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
