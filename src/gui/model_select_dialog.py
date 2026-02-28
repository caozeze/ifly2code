#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型选择对话框模块

提供从API获取的模型列表选择界面。
"""

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLineEdit, QMessageBox, QProgressDialog
)

from ..api_client import IflyMaaSClient, ApiError


class FetchModelsThread(QThread):
    """获取模型列表的后台线程"""

    # 信号：成功时发送模型列表，失败时发送错误消息
    success = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, base_url: str):
        """初始化线程

        Args:
            api_key: API密钥
            base_url: API基础URL
        """
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url

    def run(self) -> None:
        """执行后台任务"""
        try:
            models = IflyMaaSClient.get_models(self.api_key, self.base_url)
            self.success.emit(models)
        except ApiError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"未知错误: {str(e)}")


class ModelSelectDialog(QDialog):
    """模型选择对话框

    显示从API获取的可用模型列表，供用户选择。
    """

    # 信号：用户选择了模型后发送模型ID
    model_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        """初始化对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.models: List[Dict[str, Any]] = []
        self.selected_model_id: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("选择模型")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel("从API获取的可用模型列表：")
        layout.addWidget(info_label)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入模型名称过滤...")
        self.search_input.textChanged.connect(self._filter_models)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 模型列表
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self.model_list)

        # 统计标签
        self.count_label = QLabel("共 0 个模型")
        layout.addWidget(self.count_label)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        button_layout.addWidget(self.refresh_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.select_btn = QPushButton("确定")
        self.select_btn.clicked.connect(self._on_select)
        button_layout.addWidget(self.select_btn)

        layout.addLayout(button_layout)

    def load_models(self, api_key: str, base_url: str, parent_widget=None) -> bool:
        """加载模型列表

        Args:
            api_key: API密钥
            base_url: API基础URL
            parent_widget: 父窗口（用于进度对话框）

        Returns:
            加载成功返回True
        """
        # 显示进度对话框
        progress = QProgressDialog(
            "正在获取模型列表...",
            "取消",
            0, 0,
            parent_widget or self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        # 创建后台线程
        self.fetch_thread = FetchModelsThread(api_key, base_url)

        # 连接信号
        self.fetch_thread.success.connect(lambda models: self._on_fetch_success(models, progress))
        self.fetch_thread.error.connect(lambda error: self._on_fetch_error(error, progress))

        # 启动线程
        self.fetch_thread.start()

        return True

    def _on_fetch_success(self, models: List[Dict[str, Any]], progress: QProgressDialog) -> None:
        """获取成功回调

        Args:
            models: 模型列表
            progress: 进度对话框
        """
        progress.close()
        self.models = models
        self._display_models()

    def _on_fetch_error(self, error: str, progress: QProgressDialog) -> None:
        """获取失败回调

        Args:
            error: 错误消息
            progress: 进度对话框
        """
        progress.close()
        QMessageBox.warning(self, "获取失败", f"无法获取模型列表:\n{error}")

    def _display_models(self, filter_text: str = "") -> None:
        """显示模型列表

        Args:
            filter_text: 过滤文本
        """
        self.model_list.clear()

        filter_lower = filter_text.lower().strip()
        count = 0

        for model in self.models:
            model_id = model.get("id", "")

            # 过滤
            if filter_lower and filter_lower not in model_id.lower():
                continue

            # 创建列表项
            item = QListWidgetItem(f"📦 {model_id}")
            item.setData(Qt.UserRole, model_id)
            self.model_list.addItem(item)
            count += 1

        self.count_label.setText(f"共 {count} 个模型")

        # 如果只有一个模型，自动选中
        if count == 1:
            self.model_list.setCurrentRow(0)

    def _filter_models(self, text: str) -> None:
        """过滤模型列表

        Args:
            text: 过滤文本
        """
        self._display_models(text)

    def _on_select(self) -> None:
        """确定选择"""
        current_item = self.model_list.currentItem()
        if current_item:
            model_id = current_item.data(Qt.UserRole)
            self.selected_model_id = model_id
            self.accept()
        else:
            QMessageBox.information(self, "提示", "请先选择一个模型")

    def _refresh(self) -> None:
        """刷新模型列表"""
        # 这个方法需要传入api_key和base_url
        # 实际使用时由调用方处理
        QMessageBox.information(self, "提示", "请从编辑对话框点击'获取模型'按钮刷新")

    def get_selected_model_id(self) -> Optional[str]:
        """获取选中的模型ID

        Returns:
            模型ID，未选择返回None
        """
        return self.selected_model_id


class QuickModelSelectDialog(ModelSelectDialog):
    """快速模型选择对话框（带API参数）"""

    def __init__(self, api_key: str, base_url: str, parent=None):
        """初始化对话框

        Args:
            api_key: API密钥
            base_url: API基础URL
            parent: 父窗口
        """
        super().__init__(parent)
        self.api_key = api_key
        self.base_url = base_url

        # 自动加载模型列表
        self.load_models(api_key, base_url, parent)

    def _refresh(self) -> None:
        """刷新模型列表"""
        self.load_models(self.api_key, self.base_url, self.parent())
