#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask代理服务器模块

提供HTTP代理服务，将Anthropic API格式的请求转换为OpenAI API格式，
并转发到讯飞星辰MaaS平台。
"""

import json
import threading
import time
from typing import Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, stream_with_context
from openai import OpenAI

from .converter import APIConverter
from ..logger import ProxyLogger


class ProxyServer:
    """讯飞星辰MaaS代理服务器

    将Anthropic API请求转换为OpenAI API格式，转发到讯飞星辰MaaS平台。

    Attributes:
        config: 服务器配置字典
        running: 服务器运行状态
        logger: 日志管理器
        app: Flask应用实例
        client: OpenAI客户端
        thread: Flask服务器运行线程
    """

    def __init__(self, config: Dict, logger: Optional[ProxyLogger] = None):
        """初始化代理服务器

        Args:
            config: 配置字典，包含api_key, base_url, model_id等
            logger: 日志管理器实例
        """
        self.config = config
        self.logger = logger or ProxyLogger()
        self.running = False
        self.app = None
        self.client = None
        self.thread: Optional[threading.Thread] = None
        self.converter = APIConverter()

        # 请求计数统计
        self.request_count = 0
        self.start_time: Optional[float] = None

        # 初始化Flask应用
        self._init_flask_app()

        # 初始化OpenAI客户端
        self._init_openai_client()

    def _init_flask_app(self) -> None:
        """初始化Flask应用"""
        self.app = Flask(__name__)
        self.app.config['JSON_AS_ASCII'] = False

        # 注册路由
        self._register_routes()

    def _init_openai_client(self) -> None:
        """初始化OpenAI客户端"""
        api_key = self.config.get('api', {}).get('api_key', '')
        base_url = self.config.get('api', {}).get('base_url', '')

        if not api_key or not base_url:
            self.logger.warning("API Key或Base URL未配置，代理功能可能无法正常工作")
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.logger.info(f"OpenAI客户端已初始化: {base_url}")

    def _register_routes(self) -> None:
        """注册Flask路由"""

        @self.app.route('/v1/messages', methods=['POST'])
        def create_message():
            """处理Anthropic messages API请求"""
            return self._handle_create_message()

        @self.app.route('/v1/models', methods=['GET'])
        def list_models():
            """返回支持的模型列表"""
            model_id = self.config.get('api', {}).get('model_id', 'unknown')
            return jsonify({
                "data": [{
                    "id": model_id,
                    "type": "model",
                    "display_name": model_id,
                    "created_at": "2024-01-01T00:00:00Z"
                }]
            })

        @self.app.route('/health', methods=['GET'])
        def health():
            """健康检查端点"""
            model_id = self.config.get('api', {}).get('model_id', 'unknown')
            return jsonify({
                "status": "ok" if self.running else "stopped",
                "model": model_id,
                "api": "anthropic",
                "request_count": self.request_count,
                "uptime": self._get_uptime() if self.start_time else 0
            })

    def _handle_create_message(self) -> Response:
        """处理create_message请求

        Returns:
            Flask响应对象
        """
        try:
            data = request.get_json()
            model = data.get('model', 'unknown')

            self.logger.info(f"收到请求: model={model}")

            # 提取参数
            anthropic_messages = data.get('messages', [])
            stream = data.get('stream', False)

            messages, _, max_tokens, temperature = self.converter.extract_stream_params(data)

            # 转换消息格式
            openai_messages = self.converter.anthropic_to_openai_messages(messages)

            # 获取模型ID
            model_id = self.config.get('api', {}).get('model_id', '')
            if not model_id:
                return jsonify({
                    "type": "error",
                    "error": {"type": "api_error", "message": "Model ID未配置"}
                }), 500

            # 增加请求计数
            self.request_count += 1

            # 获取高级配置
            advanced = self.config.get('advanced', {})
            lora_id = advanced.get('lora_id', '0')
            search_disable = advanced.get('search_disable', True)

            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=model_id,
                messages=openai_messages,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers={"lora_id": lora_id},
                stream_options={"include_usage": True},
                extra_body={"search_disable": search_disable}
            )

            if stream:
                return self._handle_stream_response(response)
            else:
                return self._handle_normal_response(response, model_id)

        except Exception as e:
            self.logger.error(f"请求处理错误: {e}")
            return jsonify({
                "type": "error",
                "error": {"type": "api_error", "message": str(e)}
            }), 500

    def _handle_stream_response(self, response) -> Response:
        """处理流式响应

        Args:
            response: OpenAI流式响应对象

        Returns:
            Flask流式响应
        """
        message_id = f"msg_{int(time.time() * 1000)}"
        model_id = self.config.get('api', {}).get('model_id', 'unknown')

        def generate():
            """生成流式响应"""
            try:
                # 发送开始事件
                yield self.converter.create_stream_start_events(message_id, model_id)

                # 发送内容增量
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield self.converter.create_content_delta_event(content)

                # 发送结束事件
                yield self.converter.create_stream_end_events()

            except Exception as e:
                self.logger.error(f"流式响应错误: {e}")
                yield self.converter.create_error_event(str(e))

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'anthropic-version': '2023-06-01'
            }
        )

    def _handle_normal_response(self, response, model_id: str):
        """处理非流式响应

        Args:
            response: OpenAI响应对象
            model_id: 模型ID

        Returns:
            Flask JSON响应
        """
        anthropic_response = self.converter.openai_to_anthropic_response(
            response, model_id
        )

        content = anthropic_response['content'][0]['text']
        self.logger.info(f"响应成功: {len(content)} 字符")

        return jsonify(anthropic_response)

    def _get_uptime(self) -> float:
        """获取运行时间（秒）

        Returns:
            运行时间，未运行返回0
        """
        if self.start_time is None:
            return 0
        return time.time() - self.start_time

    def start(self, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """启动代理服务器

        Args:
            host: 监听地址，默认从配置读取
            port: 监听端口，默认从配置读取

        Returns:
            启动成功返回True，失败返回False
        """
        if self.running:
            self.logger.warning("代理服务器已在运行")
            return True

        proxy_config = self.config.get('proxy', {})
        host = host or proxy_config.get('host', '127.0.0.1')
        port = port or proxy_config.get('port', 8080)

        if not self.client:
            self.logger.error("OpenAI客户端未初始化，无法启动代理")
            return False

        def run_flask():
            """在单独线程中运行Flask"""
            self.app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )

        self.thread = threading.Thread(target=run_flask, daemon=True)
        self.thread.start()

        self.running = True
        self.start_time = time.time()
        self.request_count = 0

        self.logger.info("=" * 60)
        self.logger.info("Anthropic API 代理服务器启动")
        self.logger.info("=" * 60)
        self.logger.info(f"本地地址: http://{host}:{port}")
        self.logger.info(f"API端点: http://{host}:{port}/v1/messages")
        self.logger.info(f"目标模型: {self.config.get('api', {}).get('model_id', 'unknown')}")
        self.logger.info("=" * 60)

        return True

    def stop(self) -> bool:
        """停止代理服务器

        Returns:
            停止成功返回True
        """
        if not self.running:
            return True

        self.running = False
        self.start_time = None

        self.logger.info("代理服务器已停止")

        return True

    def get_status(self) -> Dict:
        """获取服务器状态

        Returns:
            状态字典
        """
        return {
            "running": self.running,
            "request_count": self.request_count,
            "uptime": self._get_uptime(),
            "host": self.config.get('proxy', {}).get('host', '127.0.0.1'),
            "port": self.config.get('proxy', {}).get('port', 8080)
        }

    def is_running(self) -> bool:
        """检查服务器是否运行

        Returns:
            运行中返回True
        """
        return self.running


if __name__ == "__main__":
    # 测试代码
    test_config = {
        "api": {
            "api_key": "test_key",
            "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
            "model_id": "test_model"
        },
        "proxy": {
            "host": "127.0.0.1",
            "port": 8080
        },
        "advanced": {
            "lora_id": "0",
            "search_disable": True
        }
    }

    server = ProxyServer(test_config)
    print("服务器状态:", server.get_status())
