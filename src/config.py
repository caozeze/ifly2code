#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

负责加载、保存和管理应用配置。支持多模型配置，
配置存储在JSON文件中，包括API密钥、代理设置、应用选项等。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class Config:
    """应用配置管理类

    提供配置的加载、保存、获取和设置功能。
    支持多模型配置，可以添加、删除、切换模型。
    配置文件默认为项目目录下的 config.json。

    Attributes:
        config_path: 配置文件的路径
        _config: 配置字典
    """

    # 默认模型配置
    DEFAULT_MODEL = {
        "name": "默认模型",
        "api_key": "",
        "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
        "model_id": "",
        "max_tokens": 4096,
        "temperature": 0.7,
        "lora_id": "0",
        "search_disable": True
    }

    # 默认配置
    DEFAULT_CONFIG: Dict[str, Any] = {
        "models": [
            {
                "name": "讯飞星辰模型",
                "api_key": "",
                "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
                "model_id": "",
                "max_tokens": 4096,
                "temperature": 0.7,
                "lora_id": "0",
                "search_disable": True
            }
        ],
        "current_model": "讯飞星辰模型",
        "proxy": {
            "host": "127.0.0.1",
            "port": 8080
        },
        "app": {
            "autostart": False,
            "minimize_to_tray": True,
            "log_level": "INFO",
            "remember_window_size": True,
            "window_width": 800,
            "window_height": 600
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为项目目录下的 config.json
        """
        if config_path is None:
            # 默认路径：项目目录下的 config.json
            self.config_path = Path(__file__).parent.parent / "config.json"
        else:
            self.config_path = Path(config_path)

        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> bool:
        """从文件加载配置

        如果配置文件不存在，则使用默认配置。
        支持从旧版本配置格式自动迁移。

        Returns:
            加载成功返回 True，失败返回 False
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                # 检查是否是旧版配置格式（有api字段但没有models字段）
                if "api" in loaded and "models" not in loaded:
                    loaded = self._migrate_old_config(loaded)

                # 合并默认配置和加载的配置（确保所有字段都存在）
                self._config = self._deep_merge(self.DEFAULT_CONFIG, loaded)
            else:
                # 使用默认配置
                self._config = self.DEFAULT_CONFIG.copy()
                self.save()
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"配置文件加载失败: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            return False

    def _migrate_old_config(self, old_config: Dict) -> Dict:
        """将旧版配置格式迁移到新版格式

        Args:
            old_config: 旧版配置字典

        Returns:
            新版配置字典
        """
        api = old_config.get("api", {})
        advanced = old_config.get("advanced", {})

        new_config = {
            "models": [
                {
                    "name": "迁移的模型",
                    "api_key": api.get("api_key", ""),
                    "base_url": api.get("base_url", "https://maas-api.cn-huabei-1.xf-yun.com/v2"),
                    "model_id": api.get("model_id", ""),
                    "max_tokens": advanced.get("max_tokens", 4096),
                    "temperature": advanced.get("temperature", 0.7),
                    "lora_id": advanced.get("lora_id", "0"),
                    "search_disable": advanced.get("search_disable", True)
                }
            ],
            "current_model": "迁移的模型",
            "proxy": old_config.get("proxy", {"host": "127.0.0.1", "port": 8080}),
            "app": old_config.get("app", self.DEFAULT_CONFIG["app"])
        }
        return new_config

    def save(self) -> bool:
        """保存配置到文件

        Returns:
            保存成功返回 True，失败返回 False
        """
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"配置文件保存失败: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值

        支持点号分隔的路径，如 "api.api_key"

        Args:
            key_path: 配置键路径，使用点号分隔
            default: 默认值

        Returns:
            配置值，不存在则返回默认值
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """设置配置值

        支持点号分隔的路径，如 "api.api_key"

        Args:
            key_path: 配置键路径，使用点号分隔
            value: 要设置的值
        """
        keys = key_path.split('.')
        config = self._config

        # 遍历到倒数第二层
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # 设置最后一层的值
        config[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """获取完整配置字典

        Returns:
            完整的配置字典
        """
        return self._config.copy()

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """深度合并两个字典

        Args:
            base: 基础字典
            update: 更新字典

        Returns:
            合并后的字典
        """
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # ==================== 多模型管理方法 ====================

    def get_models(self) -> List[Dict[str, Any]]:
        """获取所有模型列表

        Returns:
            模型列表
        """
        return self._config.get("models", []).copy()

    def get_model_names(self) -> List[str]:
        """获取所有模型名称列表

        Returns:
            模型名称列表
        """
        models = self._config.get("models", [])
        return [m.get("name", "") for m in models]

    def get_current_model_name(self) -> str:
        """获取当前选中的模型名称

        Returns:
            当前模型名称，不存在则返回第一个模型名称
        """
        current = self._config.get("current_model", "")
        models = self.get_models()

        # 如果当前模型不存在，返回第一个模型
        model_names = [m.get("name", "") for m in models]
        if current not in model_names and model_names:
            return model_names[0]
        return current or (model_names[0] if model_names else "")

    def set_current_model(self, name: str) -> bool:
        """设置当前使用的模型

        Args:
            name: 模型名称

        Returns:
            设置成功返回True，模型不存在返回False
        """
        model_names = self.get_model_names()
        if name not in model_names:
            return False

        self._config["current_model"] = name
        return self.save()

    def get_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取模型配置

        Args:
            name: 模型名称

        Returns:
            模型配置字典，不存在返回None
        """
        models = self._config.get("models", [])
        for model in models:
            if model.get("name") == name:
                return model.copy()
        return None

    def get_current_model_config(self) -> Dict[str, Any]:
        """获取当前模型的完整配置（用于ProxyServer）

        Returns:
            包含api, advanced等字段的配置字典
        """
        model_name = self.get_current_model_name()
        model = self.get_model_by_name(model_name)

        if not model:
            # 返回默认配置
            model = self.DEFAULT_MODEL.copy()

        return {
            "api": {
                "api_key": model.get("api_key", ""),
                "base_url": model.get("base_url", "https://maas-api.cn-huabei-1.xf-yun.com/v2"),
                "model_id": model.get("model_id", "")
            },
            "advanced": {
                "lora_id": model.get("lora_id", "0"),
                "search_disable": model.get("search_disable", True),
                "max_tokens": model.get("max_tokens", 4096),
                "temperature": model.get("temperature", 0.7)
            },
            "proxy": self._config.get("proxy", {"host": "127.0.0.1", "port": 8080})
        }

    def add_model(self, model: Dict[str, Any]) -> bool:
        """添加新模型

        Args:
            model: 模型配置字典，必须包含name字段

        Returns:
            添加成功返回True，名称已存在返回False
        """
        name = model.get("name")
        if not name:
            return False

        # 检查名称是否已存在
        if name in self.get_model_names():
            return False

        # 确保所有必需字段存在
        full_model = self.DEFAULT_MODEL.copy()
        full_model.update(model)

        self._config.setdefault("models", []).append(full_model)

        # 如果是第一个模型，设置为当前模型
        if len(self._config["models"]) == 1:
            self._config["current_model"] = name

        return self.save()

    def remove_model(self, name: str) -> bool:
        """删除模型

        Args:
            name: 模型名称

        Returns:
            删除成功返回True，模型不存在或只剩一个模型返回False
        """
        models = self._config.get("models", [])
        if len(models) <= 1:
            return False

        # 查找并删除模型
        for i, model in enumerate(models):
            if model.get("name") == name:
                models.pop(i)

                # 如果删除的是当前模型，切换到第一个模型
                if self._config.get("current_model") == name:
                    self._config["current_model"] = models[0].get("name", "")

                return self.save()

        return False

    def update_model(self, name: str, data: Dict[str, Any]) -> bool:
        """更新模型配置

        Args:
            name: 原模型名称
            data: 新的模型数据（如果包含新name则重命名）

        Returns:
            更新成功返回True，模型不存在返回False
        """
        models = self._config.get("models", [])
        for i, model in enumerate(models):
            if model.get("name") == name:
                # 更新模型配置
                new_name = data.get("name", name)
                model.update(data)
                model["name"] = new_name

                # 如果重命名了，更新current_model
                if new_name != name and self._config.get("current_model") == name:
                    self._config["current_model"] = new_name

                return self.save()

        return False


# 全局配置实例（单例模式）
_global_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例

    Returns:
        全局配置实例
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


if __name__ == "__main__":
    # 测试代码
    config = Config()
    print("当前配置:")
    print(json.dumps(config.get_all(), ensure_ascii=False, indent=2))

    # 测试获取和设置
    print(f"\nAPI Base URL: {config.get('api.base_url')}")
    config.set('api.test_value', 'hello')
    print(f"测试值: {config.get('api.test_value')}")
