#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

负责加载、保存和管理应用配置。配置存储在JSON文件中，
包括API密钥、代理设置、应用选项等。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """应用配置管理类

    提供配置的加载、保存、获取和设置功能。
    配置文件默认为项目目录下的 config.json。

    Attributes:
        config_path: 配置文件的路径
        _config: 配置字典
    """

    # 默认配置
    DEFAULT_CONFIG: Dict[str, Any] = {
        "api": {
            "api_key": "",
            "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
            "model_id": ""
        },
        "proxy": {
            "host": "127.0.0.1",
            "port": 8080
        },
        "advanced": {
            "lora_id": "0",
            "search_disable": True,
            "max_tokens": 4096,
            "temperature": 0.7
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

        Returns:
            加载成功返回 True，失败返回 False
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
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
