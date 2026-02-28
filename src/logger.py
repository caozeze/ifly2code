#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块

提供统一的日志记录功能，支持多级别日志输出，
并可发送信号通知GUI更新日志显示。
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


class GUILogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到GUI

    这个处理器会将日志记录通过回调函数发送给GUI进行显示。

    Attributes:
        callback: 日志回调函数，接收 (level, message) 参数
    """

    def __init__(self, callback: Optional[Callable[[str, str], None]] = None):
        """初始化GUI日志处理器

        Args:
            callback: 日志回调函数，签名为 callback(level: str, message: str)
        """
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录

        Args:
            record: 日志记录对象
        """
        try:
            if self.callback:
                # 格式化日志消息
                message = self.format(record)
                # 发送给GUI
                self.callback(record.levelname, message)
        except Exception:
            # 防止日志处理器本身出错导致程序崩溃
            self.handleError(record)


class ProxyLogger:
    """代理服务器日志管理类

    提供统一的日志记录接口，支持控制台输出、文件输出和GUI显示。

    Attributes:
        name: 日志器名称
        logger: Python logger 实例
        gui_callback: GUI日志回调函数
    """

    # 日志级别映射
    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    # 日志颜色代码（用于控制台）
    LOG_COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[37m",       # 白色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
        "RESET": "\033[0m"        # 重置
    }

    def __init__(
        self,
        name: str = "ifly2code",
        level: str = "INFO",
        log_file: Optional[str] = None,
        gui_callback: Optional[Callable[[str, str], None]] = None
    ):
        """初始化日志管理器

        Args:
            name: 日志器名称
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: 日志文件路径，为 None 则不写文件
            gui_callback: GUI日志回调函数
        """
        self.name = name
        self.gui_callback = gui_callback

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.LOG_LEVELS.get(level, logging.INFO))

        # 清除已有的处理器
        self.logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(
            fmt='[%(levelname)s] %(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 添加文件处理器（如果指定）
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # 添加GUI处理器（如果指定回调）
        if gui_callback:
            gui_handler = GUILogHandler(gui_callback)
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)

    def set_gui_callback(self, callback: Callable[[str, str], None]) -> None:
        """设置GUI日志回调函数

        Args:
            callback: 日志回调函数
        """
        self.gui_callback = callback
        # 移除旧的GUI处理器
        self.logger.handlers = [
            h for h in self.logger.handlers
            if not isinstance(h, GUILogHandler)
        ]
        # 添加新的GUI处理器
        if callback:
            gui_handler = GUILogHandler(callback)
            formatter = logging.Formatter(
                fmt='[%(levelname)s] %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)

    def debug(self, message: str) -> None:
        """记录DEBUG级别日志"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """记录INFO级别日志"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """记录WARNING级别日志"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """记录ERROR级别日志"""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """记录CRITICAL级别日志"""
        self.logger.critical(message)

    def exception(self, message: str) -> None:
        """记录异常信息"""
        self.logger.exception(message)

    @staticmethod
    def format_colored(level: str, message: str) -> str:
        """格式化带颜色的日志消息（用于控制台）

        Args:
            level: 日志级别
            message: 日志消息

        Returns:
            带颜色代码的日志消息
        """
        color = ProxyLogger.LOG_COLORS.get(level, "")
        reset = ProxyLogger.LOG_COLORS["RESET"]
        return f"{color}[{level}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}{reset}"

    @staticmethod
    def strip_colors(message: str) -> str:
        """移除日志消息中的颜色代码

        Args:
            message: 带颜色代码的日志消息

        Returns:
            纯文本日志消息
        """
        for color in ProxyLogger.LOG_COLORS.values():
            message = message.replace(color, "")
        return message


# 全局日志实例
_global_logger: Optional[ProxyLogger] = None


def get_logger() -> ProxyLogger:
    """获取全局日志实例

    Returns:
        全局日志实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = ProxyLogger()
    return _global_logger


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    gui_callback: Optional[Callable[[str, str], None]] = None
) -> ProxyLogger:
    """设置并返回全局日志实例

    Args:
        level: 日志级别
        log_file: 日志文件路径
        gui_callback: GUI日志回调函数

    Returns:
        配置好的日志实例
    """
    global _global_logger
    _global_logger = ProxyLogger(
        level=level,
        log_file=log_file,
        gui_callback=gui_callback
    )
    return _global_logger


if __name__ == "__main__":
    # 测试代码
    def test_callback(level: str, message: str):
        """测试回调函数"""
        print(f"[GUI回调] {level}: {message}")

    logger = ProxyLogger(gui_callback=test_callback)
    logger.debug("这是DEBUG日志")
    logger.info("这是INFO日志")
    logger.warning("这是WARNING日志")
    logger.error("这是ERROR日志")
