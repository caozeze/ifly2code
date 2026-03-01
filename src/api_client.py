#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞星辰MaaS API客户端模块

提供与讯飞星辰MaaS平台交互的功能，包括获取模型列表等。
"""

from typing import Any, Dict, List, Optional

from openai import OpenAI


class ApiError(Exception):
    """API调用错误"""

    pass


class IflyMaaSClient:
    """讯飞星辰MaaS API客户端类

    封装与讯飞星辰MaaS平台交互的常用操作。

    提供的功能:
    - 获取可用模型列表
    - 验证API Key有效性
    """

    # 请求超时时间（秒）
    TIMEOUT = 30

    @staticmethod
    def get_models(api_key: str, base_url: str, timeout: int = None) -> List[Dict[str, Any]]:
        """获取可用的模型列表

        调用讯飞星辰MaaS的 /v1/models 接口获取当前账户可用的所有模型。

        Args:
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒），默认使用类默认值

        Returns:
            模型列表，每个模型包含以下字段:
            - id: 模型ID
            - created: 创建时间戳
            - object: 对象类型（通常为"model"）

        Raises:
            ApiError: API调用失败时抛出
        """
        timeout = timeout or IflyMaaSClient.TIMEOUT

        try:
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout
            )

            # 调用模型列表接口
            response = client.models.list()

            # 转换为字典列表
            models = []
            for model in response.data:
                models.append({
                    "id": str(model.id),
                    "created": getattr(model, "created", 0),
                    "object": getattr(model, "object", "model")
                })

            return models

        except Exception as e:
            # 统一转换为ApiError抛出
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                raise ApiError("API Key验证失败，请检查是否正确")
            elif "403" in error_msg or "permission" in error_msg.lower():
                raise ApiError("没有权限访问模型列表")
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise ApiError("请求超时，请检查网络连接")
            elif "connection" in error_msg.lower():
                raise ApiError("网络连接失败，请检查Base URL是否正确")
            else:
                raise ApiError(f"获取模型列表失败: {error_msg}")

    @staticmethod
    def validate_credentials(api_key: str, base_url: str) -> tuple[bool, str]:
        """验证API凭据是否有效

        Args:
            api_key: API密钥
            base_url: API基础URL

        Returns:
            (is_valid, message) 元组
            - is_valid: 验证是否成功
            - message: 结果消息
        """
        try:
            # 尝试获取模型列表来验证
            models = IflyMaaSClient.get_models(api_key, base_url, timeout=10)
            if models:
                return True, f"验证成功，找到 {len(models)} 个可用模型"
            else:
                return False, "未找到可用模型"
        except ApiError as e:
            return False, str(e)
        except Exception as e:
            return False, f"验证失败: {str(e)}"

    @staticmethod
    def test_connection(api_key: str, base_url: str, model_id: str) -> tuple[bool, str]:
        """测试与指定模型的连接

        Args:
            api_key: API密钥
            base_url: API基础URL
            model_id: 要测试的模型ID

        Returns:
            (is_valid, message) 元组
        """
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=10
            )

            # 发送一个简单的测试请求
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )

            return True, "连接测试成功"

        except ApiError as e:
            return False, str(e)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                return False, "API Key验证失败"
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                return False, f"模型 {model_id} 不存在或无权访问"
            else:
                return False, f"连接测试失败: {error_msg}"


if __name__ == "__main__":
    # 测试代码
    print("讯飞星辰MaaS API客户端")
    print("=" * 50)

    # 示例：获取模型列表
    test_api_key = "your-api-key"
    test_base_url = "https://maas-api.cn-huabei-1.xf-yun.com/v2"

    print(f"Base URL: {test_base_url}")
    print("请填入有效的API Key进行测试")
