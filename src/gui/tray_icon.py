#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统托盘模块

提供系统托盘图标和菜单，支持最小化到托盘、
右键菜单控制等功能。
"""

from typing import Optional, Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget, QApplication


class TrayIcon:
    """系统托盘图标管理类

    提供托盘图标、菜单和交互功能。

    Attributes:
        window: 主窗口实例
        tray: QSystemTrayIcon实例
        icon_running: 运行状态图标
        icon_stopped: 停止状态图标
    """

    def __init__(self, window: QWidget, menu_callback: Optional[Callable] = None):
        """初始化系统托盘

        Args:
            window: 主窗口实例
            menu_callback: 菜单回调函数，用于自定义菜单行为
        """
        self.window = window
        self.menu_callback = menu_callback
        self.tray: Optional[QSystemTrayIcon] = None

        # 创建托盘
        self._create_tray()

    def _create_tray(self) -> None:
        """创建系统托盘图标"""
        # 检查系统是否支持托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QSystemTrayIcon(self.window)

        # 设置图标（使用默认图标，后续可替换为自定义图标）
        self._set_icon(False)

        # 创建托盘菜单
        menu = QMenu()

        # 启动/停止
        self.toggle_action = menu.addAction("🚀 启动代理")
        self.toggle_action.triggered.connect(self._on_toggle)

        menu.addSeparator()

        # 打开窗口
        show_action = menu.addAction("📖 打开窗口")
        show_action.triggered.connect(self._on_show)

        # 复制配置
        copy_action = menu.addAction("📋 复制配置")
        copy_action.triggered.connect(self._on_copy_config)

        menu.addSeparator()

        # 退出
        quit_action = menu.addAction("❌ 退出")
        quit_action.triggered.connect(self._on_quit)

        self.tray.setContextMenu(menu)

        # 双击托盘图标显示/隐藏窗口
        self.tray.activated.connect(self._on_activated)

        # 显示托盘图标
        self.tray.show()

    def _set_icon(self, running: bool) -> None:
        """设置托盘图标状态

        Args:
            running: True表示运行中，False表示已停止
        """
        if running:
            # 绿色图标（运行中）
            # TODO: 替换为自定义图标
            icon = self._create_color_icon(Qt.green)
        else:
            # 红色图标（已停止）
            icon = self._create_color_icon(Qt.red)

        if self.tray:
            self.tray.setIcon(icon)

    def _create_color_icon(self, color) -> QIcon:
        """创建纯色图标（临时方案）

        Args:
            color: QColor颜色值

        Returns:
            QIcon实例
        """
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 画圆形
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        painter.end()

        return QIcon(pixmap)

    def _on_toggle(self) -> None:
        """启动/停止代理"""
        if hasattr(self.window, '_toggle_proxy'):
            self.window._toggle_proxy()
        self._update_menu()

    def _on_show(self) -> None:
        """显示主窗口"""
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _on_copy_config(self) -> None:
        """复制配置"""
        if hasattr(self.window, '_copy_config'):
            self.window._copy_config()

    def _on_quit(self) -> None:
        """退出应用"""
        # 先停止代理
        if hasattr(self.window, '_stop_proxy'):
            self.window._stop_proxy()
        # 强制退出（不触发 closeEvent）
        QApplication.instance().quit()

    def _on_activated(self, reason) -> None:
        """托盘图标激活事件

        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.DoubleClick:
            # 双击显示/隐藏窗口
            if self.window.isVisible():
                self.window.hide()
            else:
                self._on_show()

    def _update_menu(self) -> None:
        """更新托盘菜单状态"""
        if not hasattr(self.window, 'proxy_running'):
            return

        running = self.window.proxy_running

        # 更新菜单文本
        if running:
            self.toggle_action.setText("⏹ 停止代理")
        else:
            self.toggle_action.setText("🚀 启动代理")

        # 更新图标
        self._set_icon(running)

        # 更新提示
        if running:
            port = self.window.config.get('proxy.port', 8080)
            if hasattr(self.window, 'proxy_server') and self.window.proxy_server:
                port = self.window.proxy_server.actual_port or port
            self.tray.setToolTip(
                f"讯飞星辰代理服务 - 运行中\n"
                f"http://127.0.0.1:{port}"
            )
        else:
            self.tray.setToolTip("讯飞星辰代理服务 - 已停止")

    def update_status(self, running: bool) -> None:
        """更新托盘状态（供外部调用）

        Args:
            running: True表示运行中，False表示已停止
        """
        self._update_menu()

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information
    ) -> None:
        """显示托盘通知消息

        Args:
            title: 标题
            message: 消息内容
            icon: 消息图标类型
        """
        if self.tray:
            self.tray.showMessage(title, message, icon, 3000)

    def is_available(self) -> bool:
        """检查系统托盘是否可用

        Returns:
            可用返回True
        """
        return QSystemTrayIcon.isSystemTrayAvailable()

    @staticmethod
    def is_system_tray_available() -> bool:
        """静态方法：检查系统托盘是否可用

        Returns:
            可用返回True
        """
        return QSystemTrayIcon.isSystemTrayAvailable()
