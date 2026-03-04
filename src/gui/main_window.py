#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI主窗口模块

提供应用的主界面，包括配置面板、控制面板和日志面板。
使用PySide6实现，支持中文界面和系统托盘集成。
"""

import json
import sys
import threading
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import Config, get_config
from ..logger import ProxyLogger, get_logger
from ..proxy.server import ProxyServer
from ..version import __version__
from .model_dialog import ModelManageDialog
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
    log_signal = Signal(str, str)
    # 更新检查信号 (version, url)
    update_signal = Signal(str, str)

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

        # 启动时后台检查更新
        self.update_signal.connect(self._on_update_available)
        threading.Thread(target=self._check_update, daemon=True).start()

    def _init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle("讯飞星辰 MaaS 代理服务")
        self.setMinimumSize(420, 560)

        # 从配置恢复窗口大小
        if self.config.get('app.remember_window_size', True):
            width = self.config.get('app.window_width', 500)
            height = self.config.get('app.window_height', 700)
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

        # 底部状态行：版本号 + 对齐
        bottom_layout = QHBoxLayout()
        self.version_label = QLabel(f"Version {__version__}")
        self.version_label.setStyleSheet("color: #888; font-size: 11px;")
        bottom_layout.addWidget(self.version_label)
        bottom_layout.addStretch()

        credit_label = QLabel("Powered by zecao")
        credit_label.setAlignment(Qt.AlignRight)
        credit_label.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        bottom_layout.addWidget(credit_label)

        main_layout.addLayout(bottom_layout)

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
            # 自动更新 Claude Code 配置
            self._update_claude_settings()

            # 如果代理正在运行，提示用户重启
            if self.proxy_running:
                reply = QMessageBox.question(
                    self,
                    "模型已切换",
                    "模型已切换，需要重启代理才能生效。\n是否立即重启代理？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self._stop_proxy()
                    self._start_proxy()

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
            self.config.set_models(updated_models)
            if selected_name:
                self.config.set_current_model(selected_name)
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
        # 先保存端口配置，避免异常退出时端口变更丢失
        self.config.set('proxy.port', self.port_input.value())
        self.config.save()

        if not self.proxy_server:
            self._init_proxy_server()

        if self.proxy_server and self.proxy_server.start():
            self.proxy_running = True
            self.start_stop_btn.setText("⏹ 停止代理")
            self.status_label.setText("● 状态: 运行中")
            self.status_label.setStyleSheet("color: green;")
            self.update_timer.start(1000)  # 每秒更新一次

            # 获取实际使用的端口
            actual_port = self.proxy_server.actual_port or self.port_input.value()

            # 禁用配置编辑
            self._set_config_enabled(False)

            # 更新托盘状态
            if self.tray_icon:
                self.tray_icon.update_status(True)
                self.tray_icon.show_message(
                    "代理已启动",
                    f"监听端口: {actual_port}"
                )

            # 用实际端口更新 Claude Code 配置
            self._update_claude_settings_with_port(actual_port)
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

    def _update_claude_settings(self) -> None:
        """自动更新 Claude Code 的 settings.json

        同步 api_key、base_url、model_id 到 Claude Code 配置
        """
        from pathlib import Path

        model = self.config.get_model_by_name(self.current_model_name)
        if not model:
            return

        api_key = model.get('api_key', '')
        base_url = model.get('base_url', '')
        model_id = model.get('model_id', '')

        # Claude Code settings.json 路径
        settings_path = Path.home() / '.claude' / 'settings.json'

        try:
            # 读取现有配置
            settings = {}
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

            # 确保 env 字段存在
            if 'env' not in settings:
                settings['env'] = {}

            # 同步配置（保留用户原有的其他配置）
            # 注意：Claude Code 只使用 ANTHROPIC_AUTH_TOKEN，不需要 ANTHROPIC_API_KEY
            # ANTHROPIC_BASE_URL 应该指向本地代理，而不是讯飞 API
            proxy_port = self.port_input.value()
            settings['env']['ANTHROPIC_BASE_URL'] = f"http://127.0.0.1:{proxy_port}"
            settings['env']['ANTHROPIC_AUTH_TOKEN'] = api_key
            settings['env']['ANTHROPIC_MODEL'] = model_id
            settings['env']['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = model_id
            settings['env']['ANTHROPIC_DEFAULT_SONNET_MODEL'] = model_id
            settings['env']['ANTHROPIC_DEFAULT_OPUS_MODEL'] = model_id

            # 写入
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            self.logger.info(f"已更新 Claude Code 配置: {settings_path}")
        except Exception as e:
            self.logger.warning(f"更新 Claude Code 配置失败: {e}")

    def _clear_log(self) -> None:
        """清空日志"""
        self.log_text.clear()

    def _check_update(self) -> None:
        """后台线程：检查 GitHub Release 新版本"""
        from ..updater import check_update
        has_update, version, url = check_update()
        if has_update and version and url:
            self.update_signal.emit(version, url)

    def _on_update_available(self, version: str, url: str) -> None:
        """收到新版本信号时弹窗提醒"""
        QMessageBox.information(
            self,
            "发现新版本",
            f"新版本 v{version} 已发布！\n\n下载地址：\n{url}",
        )

    def _update_claude_settings_with_port(self, port: int) -> None:
        """使用指定端口更新 Claude Code 的 settings.json

        Args:
            port: 实际使用的端口号
        """
        from pathlib import Path

        model = self.config.get_model_by_name(self.current_model_name)
        if not model:
            return

        api_key = model.get('api_key', '')
        model_id = model.get('model_id', '')

        # Claude Code settings.json 路径
        settings_path = Path.home() / '.claude' / 'settings.json'

        try:
            # 读取现有配置
            settings = {}
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

            # 确保 env 字段存在
            if 'env' not in settings:
                settings['env'] = {}

            # 同步配置（使用实际端口）
            settings['env']['ANTHROPIC_BASE_URL'] = f"http://127.0.0.1:{port}"
            settings['env']['ANTHROPIC_AUTH_TOKEN'] = api_key
            settings['env']['ANTHROPIC_MODEL'] = model_id

            # 写入
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            self.logger.info(f"已更新 Claude Code 配置 (端口 {port}): {settings_path}")
        except Exception as e:
            self.logger.warning(f"更新 Claude Code 配置失败: {e}")

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

        # 保存端口配置
        self.config.set('proxy.port', self.port_input.value())

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
