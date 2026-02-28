#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI主窗口模块

提供应用的主界面，包括配置面板、控制面板和日志面板。
使用PyQt5实现，支持中文界面和系统托盘集成。
"""

import json
import sys
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget, QSpinBox,
    QComboBox
)

from ..config import Config, get_config
from ..logger import ProxyLogger, get_logger
from ..proxy.server import ProxyServer
from .tray_icon import TrayIcon


class LogTextEdit(QTextEdit):
    """支持彩色日志显示的文本编辑器"""

    # 日志颜色映射
    LOG_COLORS = {
        "DEBUG": QColor("#00CED1"),      # 深青色
        "INFO": QColor("#000000"),       # 黑色
        "WARNING": QColor("#FF8C00"),    # 深橙色
        "ERROR": QColor("#DC143C"),      # 深红色
        "CRITICAL": QColor("#8B008B"),   # 深紫色
    }

    def __init__(self, parent=None):
        """初始化日志文本编辑器"""
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))

    def append_log(self, level: str, message: str) -> None:
        """追加日志消息

        Args:
            level: 日志级别
            message: 日志消息
        """
        # 获取颜色
        color = self.LOG_COLORS.get(level, QColor("#000000"))

        # 移动光标到末尾
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

        # 插入带颜色的文本
        char_format = cursor.charFormat()
        char_format.setForeground(color)
        cursor.setCharFormat(char_format)
        cursor.insertText(message + "\n")

        # 自动滚动
        self.ensureCursorVisible()


class MainWindow(QMainWindow):
    """主窗口类

    包含配置面板、控制面板和日志面板。

    Signals:
        log_signal: 日志信号，发送 (level, message)
    """

    # 定义日志信号
    log_signal = pyqtSignal(str, str)

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 配置和日志
        self.config: Config = get_config()
        self.logger: ProxyLogger = get_logger()

        # 代理服务器
        self.proxy_server: Optional[ProxyServer] = None

        # 状态
        self.proxy_running = False

        # 计时器（用于更新运行时间）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)

        # 系统托盘
        self.tray_icon: Optional[TrayIcon] = None

        # 初始化UI
        self._init_ui()

        # 初始化系统托盘
        self._init_tray()

        # 连接日志信号
        self.log_signal.connect(self._on_log_message)
        self.logger.set_gui_callback(self._log_callback)

    def _init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle("讯飞星辰 MaaS 代理服务")
        self.setMinimumSize(700, 600)

        # 从配置恢复窗口大小
        if self.config.get('app.remember_window_size', True):
            width = self.config.get('app.window_width', 800)
            height = self.config.get('app.window_height', 600)
            self.resize(width, height)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 添加各个面板
        main_layout.addWidget(self._create_config_panel())
        main_layout.addWidget(self._create_control_panel())
        main_layout.addWidget(self._create_log_panel(), stretch=1)

    def _create_config_panel(self) -> QGroupBox:
        """创建配置面板

        Returns:
            配置面板分组框
        """
        panel = QGroupBox("📋 配置")
        layout = QVBoxLayout()
        form_layout = QVBoxLayout()

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("API Key:")
        api_key_label.setMinimumWidth(80)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入讯飞星辰MaaS的API Key")
        self.api_key_input.setText(self.config.get('api.api_key', ''))
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        form_layout.addLayout(api_key_layout)

        # Base URL
        base_url_layout = QHBoxLayout()
        base_url_label = QLabel("Base URL:")
        base_url_label.setMinimumWidth(80)
        self.base_url_input = QComboBox()
        self.base_url_input.setEditable(True)
        self.base_url_input.addItem("https://maas-api.cn-huabei-1.xf-yun.com/v2")
        self.base_url_input.addItem("http://maas-api.cn-huabei-1.xf-yun.com/v1")
        current_url = self.config.get('api.base_url', '')
        if current_url:
            index = self.base_url_input.findText(current_url)
            if index >= 0:
                self.base_url_input.setCurrentIndex(index)
            else:
                self.base_url_input.setEditText(current_url)
        base_url_layout.addWidget(base_url_label)
        base_url_layout.addWidget(self.base_url_input)
        form_layout.addLayout(base_url_layout)

        # Model ID
        model_id_layout = QHBoxLayout()
        model_id_label = QLabel("Model ID:")
        model_id_label.setMinimumWidth(80)
        self.model_id_input = QLineEdit()
        self.model_id_input.setPlaceholderText("输入模型ID，如: xopglm47blth2")
        self.model_id_input.setText(self.config.get('api.model_id', ''))
        model_id_layout.addWidget(model_id_label)
        model_id_layout.addWidget(self.model_id_input)
        form_layout.addLayout(model_id_layout)

        # 端口
        port_layout = QHBoxLayout()
        port_label = QLabel("端口:")
        port_label.setMinimumWidth(80)
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(self.config.get('proxy.port', 8080))
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        form_layout.addLayout(port_layout)

        # 保存配置按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_config_btn = QPushButton("💾 保存配置")
        self.save_config_btn.clicked.connect(self._save_config)
        button_layout.addWidget(self.save_config_btn)
        form_layout.addLayout(button_layout)

        layout.addLayout(form_layout)
        panel.setLayout(layout)
        return panel

    def _create_control_panel(self) -> QGroupBox:
        """创建控制面板

        Returns:
            控制面板分组框
        """
        panel = QGroupBox("🎮 控制")
        layout = QHBoxLayout()

        # 启动/停止按钮
        self.start_stop_btn = QPushButton("🚀 启动代理")
        self.start_stop_btn.setMinimumHeight(40)
        self.start_stop_btn.clicked.connect(self._toggle_proxy)
        layout.addWidget(self.start_stop_btn)

        # 状态指示
        status_layout = QVBoxLayout()
        self.status_label = QLabel("● 状态: 已停止")
        self.status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.status_label)

        # 运行时间
        self.uptime_label = QLabel("⏱ 运行时间: 00:00:00")
        status_layout.addWidget(self.uptime_label)

        # 请求计数
        self.request_count_label = QLabel("📊 请求计数: 0")
        status_layout.addWidget(self.request_count_label)

        layout.addLayout(status_layout)

        # 右侧按钮
        right_layout = QVBoxLayout()
        self.copy_config_btn = QPushButton("📋 复制配置")
        self.copy_config_btn.clicked.connect(self._copy_config)
        right_layout.addWidget(self.copy_config_btn)
        layout.addLayout(right_layout)

        panel.setLayout(layout)
        return panel

    def _create_log_panel(self) -> QGroupBox:
        """创建日志面板

        Returns:
            日志面板分组框
        """
        panel = QGroupBox("📝 日志")
        layout = QVBoxLayout()

        # 日志文本框
        self.log_text = LogTextEdit()
        layout.addWidget(self.log_text)

        # 清空按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.clear_log_btn = QPushButton("🗑 清空日志")
        self.clear_log_btn.clicked.connect(self._clear_log)
        button_layout.addWidget(self.clear_log_btn)
        layout.addLayout(button_layout)

        panel.setLayout(layout)
        return panel

    def _init_tray(self) -> None:
        """初始化系统托盘"""
        if TrayIcon.is_system_tray_available():
            self.tray_icon = TrayIcon(self)
            self.tray_icon.update_status(False)

            # 配置最小化到托盘
            if self.config.get('app.minimize_to_tray', True):
                self.setWindowFlags(
                    self.windowFlags() | Qt.WindowCloseButtonHint
                )
        else:
            self.logger.warning("系统托盘不可用")

    def _log_callback(self, level: str, message: str) -> None:
        """日志回调函数（从日志线程调用）

        Args:
            level: 日志级别
            message: 日志消息
        """
        # 通过信号发送到主线程
        self.log_signal.emit(level, message)

    def _on_log_message(self, level: str, message: str) -> None:
        """处理日志消息（在主线程中）

        Args:
            level: 日志级别
            message: 日志消息
        """
        self.log_text.append_log(level, message)

    def _save_config(self) -> None:
        """保存配置"""
        # 更新配置
        self.config.set('api.api_key', self.api_key_input.text())
        self.config.set('api.base_url', self.base_url_input.currentText())
        self.config.set('api.model_id', self.model_id_input.text())
        self.config.set('proxy.port', self.port_input.value())

        # 保存到文件
        if self.config.save():
            self.logger.info("配置已保存")
            # 重新初始化代理服务器
            self._init_proxy_server()
        else:
            self.logger.error("配置保存失败")

    def _init_proxy_server(self) -> None:
        """初始化代理服务器"""
        config_data = self.config.get_all()
        self.proxy_server = ProxyServer(config_data, self.logger)

    def _toggle_proxy(self) -> None:
        """切换代理服务器状态"""
        if self.proxy_running:
            self._stop_proxy()
        else:
            self._start_proxy()

    def _start_proxy(self) -> None:
        """启动代理服务器"""
        if not self.proxy_server:
            self._init_proxy_server()

        if self.proxy_server and self.proxy_server.start():
            self.proxy_running = True
            self.start_stop_btn.setText("⏹ 停止代理")
            self.status_label.setText("● 状态: 运行中")
            self.status_label.setStyleSheet("color: green;")
            self.update_timer.start(1000)  # 每秒更新一次

            # 禁用配置编辑
            self._set_config_enabled(False)

            # 更新托盘状态
            if self.tray_icon:
                self.tray_icon.update_status(True)
                self.tray_icon.show_message(
                    "代理已启动",
                    f"监听端口: {self.port_input.value()}"
                )
        else:
            self.logger.error("代理启动失败")

    def _stop_proxy(self) -> None:
        """停止代理服务器"""
        if self.proxy_server:
            self.proxy_server.stop()

        self.proxy_running = False
        self.start_stop_btn.setText("🚀 启动代理")
        self.status_label.setText("● 状态: 已停止")
        self.status_label.setStyleSheet("color: gray;")
        self.update_timer.stop()

        # 启用配置编辑
        self._set_config_enabled(True)

        # 更新托盘状态
        if self.tray_icon:
            self.tray_icon.update_status(False)

    def _set_config_enabled(self, enabled: bool) -> None:
        """设置配置输入框是否可编辑

        Args:
            enabled: True表示可编辑，False表示禁用
        """
        self.api_key_input.setEnabled(enabled)
        self.base_url_input.setEnabled(enabled)
        self.model_id_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.save_config_btn.setEnabled(enabled)

    def _update_status(self) -> None:
        """更新状态显示"""
        if self.proxy_server and self.proxy_running:
            status = self.proxy_server.get_status()

            # 更新运行时间
            uptime = status.get('uptime', 0)
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            self.uptime_label.setText(
                f"⏱ 运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}"
            )

            # 更新请求计数
            count = status.get('request_count', 0)
            self.request_count_label.setText(f"📊 请求计数: {count}")

    def _copy_config(self) -> None:
        """复制Claude Code配置到剪贴板"""
        port = self.port_input.value()
        model_id = self.model_id_input.text() or "your-model-id"

        config_text = f"""# Windows CMD
set ANTHROPIC_BASE_URL=http://127.0.0.1:{port}
set ANTHROPIC_AUTH_TOKEN=sk-proxy-key
set ANTHROPIC_MODEL={model_id}

# Windows PowerShell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:{port}"
$env:ANTHROPIC_AUTH_TOKEN="sk-proxy-key"
$env:ANTHROPIC_MODEL="{model_id}"
"""

        clipboard = QApplication.clipboard()
        clipboard.setText(config_text)
        self.logger.info("配置已复制到剪贴板")

    def _clear_log(self) -> None:
        """清空日志"""
        self.log_text.clear()

    def closeEvent(self, event) -> None:
        """窗口关闭事件

        Args:
            event: 关闭事件
        """
        # 如果启用最小化到托盘，则隐藏窗口而不是退出
        if (self.config.get('app.minimize_to_tray', True) and
                self.tray_icon and TrayIcon.is_system_tray_available()):
            self.hide()
            event.ignore()
            if self.tray_icon:
                self.tray_icon.show_message(
                    "最小化到托盘",
                    "双击托盘图标可恢复窗口"
                )
            return

        # 停止代理
        if self.proxy_running:
            self._stop_proxy()

        # 保存窗口大小
        self.config.set('app.window_width', self.width())
        self.config.set('app.window_height', self.height())
        self.config.save()

        event.accept()


if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
