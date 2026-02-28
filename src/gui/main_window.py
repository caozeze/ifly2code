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
    QComboBox, QDialog
)

from ..config import Config, get_config
from ..logger import ProxyLogger, get_logger
from ..proxy.server import ProxyServer
from .tray_icon import TrayIcon
from .model_dialog import ModelManageDialog


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

        # 当前选中的模型名称
        self.current_model_name = self.config.get_current_model_name()

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

        # 加载模型列表
        self._load_model_list()

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

        # 模型选择行
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(QLabel("当前模型:"))

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_select_layout.addWidget(self.model_combo)

        self.model_manage_btn = QPushButton("⚙ 模型管理")
        self.model_manage_btn.clicked.connect(self._open_model_manager)
        model_select_layout.addWidget(self.model_manage_btn)

        model_select_layout.addStretch()
        layout.addLayout(model_select_layout)

        # 模型详情显示
        self.model_detail_label = QLabel()
        self.model_detail_label.setWordWrap(True)
        self.model_detail_label.setStyleSheet("padding: 8px; background: #f5f5f5; border-radius: 4px;")
        layout.addWidget(self.model_detail_label)

        # 代理端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("监听端口:"))
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(self.config.get('proxy.port', 8080))
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        panel.setLayout(layout)
        return panel

    def _load_model_list(self) -> None:
        """加载模型列表到下拉框"""
        self.model_combo.clear()
        model_names = self.config.get_model_names()
        self.model_combo.addItems(model_names)

        # 设置当前选中
        current = self.config.get_current_model_name()
        index = self.model_combo.findText(current)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        self._update_model_detail()

    def _on_model_changed(self, name: str) -> None:
        """模型选择变化事件

        Args:
            name: 新选择的模型名称
        """
        if name:
            self.current_model_name = name
            self.config.set_current_model(name)
            self._update_model_detail()

    def _update_model_detail(self) -> None:
        """更新模型详情显示"""
        model = self.config.get_model_by_name(self.current_model_name)
        if model:
            detail = f"""<b>{model.get('name', 'N/A')}</b>
Base URL: {model.get('base_url', 'N/A')}
Model ID: {model.get('model_id', 'N/A')}
最大输出: {model.get('max_tokens', 4096)} tokens
温度: {model.get('temperature', 0.7)}"""
            self.model_detail_label.setText(detail)
        else:
            self.model_detail_label.setText("未选择模型")

    def _open_model_manager(self) -> None:
        """打开模型管理对话框"""
        dialog = ModelManageDialog(self, self.current_model_name)
        dialog.set_models(self.config.get_models())

        if dialog.exec_() == QDialog.Accepted:
            # 保存更新后的模型列表
            updated_models = dialog.get_models()
            selected_name = dialog.get_selected_model_name()

            # 更新配置
            self._config._config["models"] = updated_models
            if selected_name:
                self._config._config["current_model"] = selected_name

            if self.config.save():
                self._load_model_list()
                self.logger.info("模型列表已更新")

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
        """保存配置（仅端口）"""
        self.config.set('proxy.port', self.port_input.value())
        self.config.save()
        self.logger.info("配置已保存")

    def _init_proxy_server(self) -> None:
        """初始化代理服务器"""
        # 使用当前模型的配置
        config_data = self.config.get_current_model_config()
        # 覆盖代理端口配置
        config_data['proxy']['port'] = self.port_input.value()
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
        self.port_input.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.model_manage_btn.setEnabled(enabled)

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
        model = self.config.get_model_by_name(self.current_model_name)
        model_id = model.get('model_id', 'your-model-id') if model else 'your-model-id'

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
