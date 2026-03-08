#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理对话框模块

提供模型列表管理界面，支持添加、编辑、删除模型配置。
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget,
    QMessageBox, QInputDialog
)


class ModelEditDialog(QDialog):
    """模型编辑对话框

    用于添加或编辑单个模型的配置。
    """

    def __init__(self, parent=None, model: Optional[Dict] = None):
        """初始化对话框

        Args:
            parent: 父窗口
            model: 模型配置字典，为None则表示添加新模式
        """
        super().__init__(parent)
        self.model = model or {}
        self.is_edit_mode = model is not None

        self._init_ui()
        self._load_model()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("编辑模型" if self.is_edit_mode else "添加模型")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如: DeepSeek V3")
        basic_layout.addRow("模型名称*:", self.name_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入讯飞星辰MaaS的API Key")
        basic_layout.addRow("API Key*:", self.api_key_input)

        self.base_url_input = QComboBox()
        self.base_url_input.setEditable(True)
        self.base_url_input.addItem("https://maas-api.cn-huabei-1.xf-yun.com/v2")
        self.base_url_input.addItem("http://maas-api.cn-huabei-1.xf-yun.com/v1")
        basic_layout.addRow("Base URL*:", self.base_url_input)

        # Model ID 输入（下拉框 + 可编辑）
        self.model_id_input = QComboBox()
        self.model_id_input.setEditable(True)
        # 预设常用模型
        preset_models = [
            "xopkimik25",      # Kimi
            "xopglm5",         # ChatGLM
            "xminimaxm25",     # MiniMax
            "xopqwen35397b",   # Qwen
        ]
        self.model_id_input.addItems(preset_models)
        self.model_id_input.setPlaceholderText("请选择或输入模型ID")
        self.model_id_input.setToolTip("模型ID需要从讯飞星辰MaaS平台获取")
        basic_layout.addRow("Model ID*:", self.model_id_input)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout()

        self.lora_id_input = QLineEdit()
        self.lora_id_input.setPlaceholderText("默认: 0")
        advanced_layout.addRow("LoRA ID:", self.lora_id_input)

        self.search_disable_check = QCheckBox("关闭联网搜索")
        self.search_disable_check.setChecked(True)
        advanced_layout.addRow("", self.search_disable_check)

        self.enable_thinking_check = QCheckBox("开启深度思考模式")
        self.enable_thinking_check.setChecked(False)
        self.enable_thinking_check.setToolTip("仅部分模型支持，开启后模型会进行更深入的推理思考")
        advanced_layout.addRow("", self.enable_thinking_check)

        self.disable_tools_check = QCheckBox("禁用工具调用（兼容老模型）")
        self.disable_tools_check.setChecked(False)
        self.disable_tools_check.setToolTip("开启后将不再向模型发送 tools/tool_choice 参数")
        advanced_layout.addRow("", self.disable_tools_check)

        self.fix_host_header_check = QCheckBox("修复 Host 头签名问题")
        self.fix_host_header_check.setChecked(False)
        self.fix_host_header_check.setToolTip("如果遇到 HMAC 401 签名错误，尝试启用此选项")
        advanced_layout.addRow("", self.fix_host_header_check)

        # 最大输出（下拉框 + 可编辑）
        self.max_tokens_input = QComboBox()
        self.max_tokens_input.setEditable(True)
        preset_tokens = ["512", "1024", "2048", "4096", "8192", "16384", "32768", "65536", "131072"]
        self.max_tokens_input.addItems(preset_tokens)
        self.max_tokens_input.setCurrentText("32768")  # 默认值
        self.max_tokens_input.setPlaceholderText("最大输出 tokens 数")
        advanced_layout.addRow("最大输出:", self.max_tokens_input)

        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0, 1)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(0.7)
        advanced_layout.addRow("温度:", self.temperature_input)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self._save)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _load_model(self) -> None:
        """加载模型数据到表单"""
        self.name_input.setText(self.model.get("name", ""))
        self.api_key_input.setText(self.model.get("api_key", ""))
        self.base_url_input.setEditText(self.model.get("base_url", ""))
        # Model ID - 如果值在预设中则选中，否则显示在编辑框
        model_id = self.model.get("model_id", "")
        if model_id:
            self.model_id_input.setEditText(model_id)
        # LoRA ID
        self.lora_id_input.setText(self.model.get("lora_id", "0"))
        self.search_disable_check.setChecked(self.model.get("search_disable", True))
        self.enable_thinking_check.setChecked(self.model.get("enable_thinking", False))
        self.disable_tools_check.setChecked(self.model.get("disable_tools", False))
        self.fix_host_header_check.setChecked(self.model.get("fix_host_header", False))
        # Max tokens - 如果值在预设中则选中，否则显示在编辑框
        max_tokens = str(self.model.get("max_tokens", 32768))
        self.max_tokens_input.setEditText(max_tokens)
        # Temperature
        self.temperature_input.setValue(self.model.get("temperature", 0.7))

    def _save(self) -> None:
        """保存模型配置"""
        # 验证必填字段
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入模型名称")
            return
        if not self.api_key_input.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入API Key")
            return
        if not self.model_id_input.currentText().strip():
            QMessageBox.warning(self, "验证失败", "请输入Model ID")
            return

        max_tokens_text = self.max_tokens_input.currentText().strip() or "32768"
        try:
            max_tokens = int(max_tokens_text)
            if max_tokens <= 0:
                raise ValueError("max_tokens must be positive")
        except ValueError:
            QMessageBox.warning(self, "验证失败", "最大输出必须是大于0的整数")
            return

        self.model_data = {
            "name": self.name_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "base_url": self.base_url_input.currentText().strip(),
            "model_id": self.model_id_input.currentText().strip(),
            "lora_id": self.lora_id_input.text().strip() or "0",
            "search_disable": self.search_disable_check.isChecked(),
            "enable_thinking": self.enable_thinking_check.isChecked(),
            "disable_tools": self.disable_tools_check.isChecked(),
            "fix_host_header": self.fix_host_header_check.isChecked(),
            "max_tokens": max_tokens,
            "temperature": self.temperature_input.value()
        }

        self.accept()

    def get_model_data(self) -> Optional[Dict[str, Any]]:
        """获取模型数据

        Returns:
            模型数据字典，取消返回None
        """
        return getattr(self, "model_data", None)


class ModelManageDialog(QDialog):
    """模型管理对话框

    提供模型列表管理功能，包括添加、编辑、删除模型。
    """

    def __init__(self, parent=None, current_model_name: str = ""):
        """初始化对话框

        Args:
            parent: 父窗口
            current_model_name: 当前选中的模型名称
        """
        super().__init__(parent)
        self.current_model_name = current_model_name
        self.models: List[Dict[str, Any]] = []
        self.selected_model_name = current_model_name

        self._init_ui()
        self._load_models()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("模型管理")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel(
            "在这里管理多个讯飞星辰MaaS模型配置。"
            "每个模型可以有不同的API Key、Model ID和参数设置。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(info_label)

        # 模型列表
        list_layout = QHBoxLayout()
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self._edit_model)
        list_layout.addWidget(self.model_list)

        # 右侧按钮
        btn_layout = QVBoxLayout()
        self.add_btn = QPushButton("➕ 添加")
        self.add_btn.clicked.connect(self._add_model)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏ 编辑")
        self.edit_btn.clicked.connect(self._edit_model)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑 删除")
        self.delete_btn.clicked.connect(self._delete_model)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)

        layout.addLayout(list_layout, stretch=1)

        # 详情显示
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("padding: 5px; background: #f5f5f5; border-radius: 3px;")
        layout.addWidget(self.detail_label)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self._ok)
        button_layout.addWidget(self.ok_btn)

        layout.addLayout(button_layout)

        # 连接选择变化事件
        self.model_list.itemSelectionChanged.connect(self._on_selection_changed)

    def set_models(self, models: List[Dict[str, Any]]) -> None:
        """设置模型列表

        Args:
            models: 模型列表
        """
        self.models = models.copy()
        self._load_models()

    def _load_models(self) -> None:
        """加载模型到列表"""
        self.model_list.clear()
        target_name = self.selected_model_name or self.current_model_name

        for model in self.models:
            name = model.get("name", "未命名")
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, model)
            self.model_list.addItem(item)

            # 优先选中用户当前选择的模型，其次选中初始模型
            if name == target_name:
                self.model_list.setCurrentItem(item)

    def _on_selection_changed(self) -> None:
        """选择变化事件"""
        current_item = self.model_list.currentItem()
        if current_item:
            model = current_item.data(Qt.UserRole)
            self._show_model_detail(model)

    def _show_model_detail(self, model: Dict[str, Any]) -> None:
        """显示模型详情

        Args:
            model: 模型数据
        """
        detail = f"""<b>模型名称:</b> {model.get('name', 'N/A')}
<b>Base URL:</b> {model.get('base_url', 'N/A')}
<b>Model ID:</b> {model.get('model_id', 'N/A')}
<b>最大输出:</b> {model.get('max_tokens', 4096)} tokens
<b>温度:</b> {model.get('temperature', 0.7)}
<b>LoRA ID:</b> {model.get('lora_id', '0')}"""
        self.detail_label.setText(detail)

    def _add_model(self) -> None:
        """添加新模型"""
        dialog = ModelEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            model_data = dialog.get_model_data()
            if model_data:
                self.models.append(model_data)
                # 自动选择新添加的模型
                self.selected_model_name = model_data.get("name")
                self._load_models()

    def _edit_model(self) -> None:
        """编辑选中的模型"""
        current_item = self.model_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择要编辑的模型")
            return

        model = current_item.data(Qt.UserRole)
        dialog = ModelEditDialog(self, model)
        if dialog.exec_() == QDialog.Accepted:
            model_data = dialog.get_model_data()
            if model_data:
                # 找到原模型并替换
                old_name = model.get("name")
                new_name = model_data.get("name")
                for i, m in enumerate(self.models):
                    if m.get("name") == old_name:
                        self.models[i] = model_data
                        break
                # 自动选择编辑后的模型
                self.selected_model_name = new_name
                self._load_models()

    def _delete_model(self) -> None:
        """删除选中的模型"""
        current_item = self.model_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择要删除的模型")
            return

        if len(self.models) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个模型配置")
            return

        model = current_item.data(Qt.UserRole)
        name = model.get("name", "")

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模型 \"{name}\" 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.models = [m for m in self.models if m.get("name") != name]
            self._load_models()

    def _ok(self) -> None:
        """确定按钮"""
        current_item = self.model_list.currentItem()
        if current_item:
            model = current_item.data(Qt.UserRole)
            self.selected_model_name = model.get("name", "")
        self.accept()

    def get_models(self) -> List[Dict[str, Any]]:
        """获取更新后的模型列表

        Returns:
            模型列表
        """
        return self.models.copy()

    def get_selected_model_name(self) -> str:
        """获取选中的模型名称

        Returns:
            模型名称
        """
        return self.selected_model_name
