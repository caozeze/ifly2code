#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask代理服务器模块

提供HTTP代理服务，将Anthropic API格式的请求转换为OpenAI API格式，
并转发到讯飞星辰MaaS平台。
"""

import json
import socket
import threading
import time
from typing import Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, stream_with_context
from openai import OpenAI
from werkzeug.exceptions import BadRequest
from werkzeug.serving import make_server

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
        self.http_server = None
        self.converter = APIConverter()

        # 请求计数统计（使用线程锁保护）
        self._request_lock = threading.Lock()
        self.request_count = 0
        self.start_time: Optional[float] = None

        # 实际使用的端口（可能与配置不同）
        self.actual_port: Optional[int] = None

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
            model_id = self.config.get('api', {}).get('model_id', '')
            if not model_id:
                return jsonify({
                    "data": [],
                    "error": "No model configured. Please set model_id in the proxy configuration."
                }), 503
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
            with self._request_lock:
                request_count = self.request_count
            return jsonify({
                "status": "ok" if self.running else "stopped",
                "model": model_id,
                "api": "anthropic",
                "request_count": request_count,
                "uptime": self._get_uptime() if self.start_time else 0
            })

    def _handle_create_message(self) -> Response:
        """处理create_message请求

        Returns:
            Flask响应对象
        """
        with self._request_lock:
            self.request_count += 1
            current_count = self.request_count
        request_id = f"req_{int(time.time() * 1000)}"
        self.logger.info(f"[{request_id}] ========== 收到请求 (#{current_count}) ==========")

        try:
            data = request.get_json()
            if not isinstance(data, dict):
                self.logger.warning(f"[{request_id}] 请求体不是JSON对象")
                return jsonify({
                    "type": "error",
                    "error": {"type": "invalid_request_error", "message": "请求体必须是JSON对象"}
                }), 400
            model = data.get('model', 'unknown')

            self.logger.info(f"[{request_id}] model={model}, stream={data.get('stream', False)}")

            # 提取 system（如果有）
            system_prompt = data.get('system', '')
            anthropic_messages = data.get('messages', [])

            # 转换消息格式
            openai_messages = []

            # 如果有 system，插入到消息开头
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})

            # 转换剩余消息
            converted_messages = self.converter.anthropic_to_openai_messages(anthropic_messages)
            openai_messages.extend(converted_messages)

            # 调试：只打印 tool 相关的消息
            tool_call_count = 0
            tool_msg_count = 0
            for msg in openai_messages:
                role = msg.get('role', 'unknown')
                if role == 'assistant' and 'tool_calls' in msg:
                    tool_call_count += 1
                    tc_ids = [tc.get('id', '?') for tc in msg.get('tool_calls', [])]
                    tc_names = [tc.get('function', {}).get('name', '?') for tc in msg.get('tool_calls', [])]
                    self.logger.debug(f"Assistant tool_call #{tool_call_count}: ids={tc_ids}, names={tc_names}")
                elif role == 'tool':
                    tool_msg_count += 1
                    content = msg.get('content', '')
                    # 显示更多内容，特别是错误信息
                    self.logger.debug(f"Tool msg #{tool_msg_count}: tool_call_id={msg.get('tool_call_id')}, content={content[:300]}...")

            self.logger.debug(f"消息总数: {len(openai_messages)}, tool_calls: {tool_call_count}, tool_msgs: {tool_msg_count}")

            # 提取 tools 并转换
            anthropic_tools = data.get('tools', [])
            openai_tools = None
            if anthropic_tools:
                openai_tools = self.converter.anthropic_to_openai_tools(anthropic_tools)
                self.logger.info(f"检测到 {len(openai_tools)} 个工具定义")

                # 调试：打印前3个工具的定义（特别是 input_schema）
                for i, tool in enumerate(openai_tools[:3]):
                    func = tool.get('function', {})
                    params = func.get('parameters', {})
                    required = params.get('required', [])
                    self.logger.debug(f"工具#{i+1}: name={func.get('name')}, required={required}, properties有{len(params.get('properties', {}))}个")

                # 调试：打印 Write 工具的完整定义
                for tool in openai_tools:
                    if tool.get('function', {}).get('name') == 'Write':
                        self.logger.debug(f"Write 工具完整定义: {json.dumps(tool, ensure_ascii=False)[:500]}...")
                        break

            # tool_choice 兼容转换（Anthropic -> MaaS）
            anthropic_tool_choice = data.get('tool_choice')
            openai_tool_choice = None
            if anthropic_tool_choice is not None:
                openai_tool_choice = self.converter.anthropic_to_openai_tool_choice(
                    anthropic_tool_choice
                )
                if openai_tool_choice is None:
                    self.logger.warning(f"无法识别 tool_choice，已忽略: {anthropic_tool_choice}")
                else:
                    self.logger.debug(f"tool_choice 映射: {anthropic_tool_choice} -> {openai_tool_choice}")

            stream = data.get('stream', False)
            _, _, max_tokens, temperature = self.converter.extract_stream_params(data)

            # 获取模型ID
            model_id = self.config.get('api', {}).get('model_id', '')
            if not model_id:
                return jsonify({
                    "type": "error",
                    "error": {"type": "api_error", "message": "Model ID未配置"}
                }), 500

            # 获取高级配置
            advanced = self.config.get('advanced', {})
            lora_id = advanced.get('lora_id', '0')
            search_disable = advanced.get('search_disable', True)
            enable_thinking = advanced.get('enable_thinking', False)

            # 构建 extra_body
            extra_body = {"search_disable": search_disable}
            if enable_thinking:
                extra_body["enable_thinking"] = True

            # 构建调用参数
            call_kwargs = {
                "model": model_id,
                "messages": openai_messages,
                "stream": stream,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "extra_headers": {"lora_id": lora_id},
                "stream_options": {"include_usage": True},
                "extra_body": extra_body
            }

            # 如果有 tools，添加到调用
            if openai_tools:
                call_kwargs["tools"] = openai_tools
                if openai_tool_choice is not None:
                    call_kwargs["tool_choice"] = openai_tool_choice
                # 调试：打印 Bash 工具的完整定义
                for tool in openai_tools:
                    if tool.get('function', {}).get('name') == 'Bash':
                        self.logger.debug(f"Bash 工具完整定义: {json.dumps(tool, ensure_ascii=False)}")
                        break

            # 调试：打印请求参数摘要
            self.logger.debug(f"API 请求: model={model_id}, stream={stream}, has_tools={bool(openai_tools)}, messages={len(openai_messages)}条")

            # 调用OpenAI API（支持自动降级重试）
            response, used_stream = self._call_with_fallback(call_kwargs, stream)

            if used_stream:
                return self._handle_stream_response(response)
            else:
                return self._handle_normal_response(response, model_id)

        except BadRequest:
            self.logger.warning(f"[{request_id}] 无效的JSON请求体")
            return jsonify({
                "type": "error",
                "error": {"type": "invalid_request_error", "message": "请求体不是合法JSON"}
            }), 400
        except Exception as e:
            self.logger.error(f"请求处理错误: {e}")
            return jsonify({
                "type": "error",
                "error": {"type": "api_error", "message": str(e)}
            }), 500

    def _call_with_fallback(self, call_kwargs, stream):
        """调用 API，失败时自动降级重试

        降级策略：
        - tools 相关错误 → 去掉 tools 重试
        - enable_thinking 相关错误 → 去掉 enable_thinking 重试
        - 流式错误（WebSocket/EOF）→ 非流式重试

        Returns:
            (response, used_stream)
        """
        call_kwargs = call_kwargs.copy()
        try:
            resp = self.client.chat.completions.create(**call_kwargs)
            return resp, stream
        except Exception as e:
            err_msg = str(e).lower()

            # tool_choice 不兼容 → 降级为 auto / 移除后重试
            if "tool_choice" in err_msg and "tool_choice" in call_kwargs:
                self.logger.warning("当前模型/网关不兼容 tool_choice，尝试降级重试")
                original = call_kwargs.get("tool_choice")

                retry_choices = []
                if original != "auto":
                    retry_choices.append("auto")
                retry_choices.append(None)  # 表示移除 tool_choice

                for fallback_choice in retry_choices:
                    try:
                        if fallback_choice is None:
                            call_kwargs.pop("tool_choice", None)
                        else:
                            call_kwargs["tool_choice"] = fallback_choice
                        resp = self.client.chat.completions.create(**call_kwargs)
                        return resp, stream
                    except Exception:
                        continue
                # 所有降级都失败，继续走后续兜底逻辑

            # tools 不支持 → 去掉 tools 重试
            if "tools" in err_msg and "tools" in call_kwargs:
                self.logger.warning(f"模型不支持 tools，去掉 tools 重试")
                call_kwargs.pop("tools", None)
                call_kwargs.pop("tool_choice", None)
                resp = self.client.chat.completions.create(**call_kwargs)
                return resp, stream

            # enable_thinking 不支持 → 去掉重试
            if "thinking" in err_msg and call_kwargs.get("extra_body", {}).get("enable_thinking"):
                self.logger.warning(f"模型不支持 enable_thinking，去掉重试")
                call_kwargs["extra_body"].pop("enable_thinking", None)
                resp = self.client.chat.completions.create(**call_kwargs)
                return resp, stream

            # 流式错误（WebSocket/EOF）→ 非流式重试
            if stream and ("websocket" in err_msg or "eof" in err_msg or "1006" in err_msg):
                self.logger.warning(f"流式传输失败，降级为非流式重试")
                call_kwargs["stream"] = False
                call_kwargs.pop("stream_options", None)
                resp = self.client.chat.completions.create(**call_kwargs)
                return resp, False

            raise

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
                self.logger.debug("Stream started, waiting for chunks...")

                # Anthropic content block 索引必须单调递增，且同一索引类型不能冲突
                next_block_index = 0
                text_block_index = None
                text_block_open = False
                tool_states = {}
                # tool_states:
                # {openai_index: {"anthropic_index": int, "id": str, "name": str, "started": bool, "args": str}}

                has_tool_calls = False
                final_finish_reason = None
                output_tokens = 0
                chunk_count = 0

                for chunk in response:
                    chunk_count += 1
                    choices = getattr(chunk, 'choices', None) or []

                    # include_usage=True 时，usage 可能出现在无 choices 的 chunk 中
                    usage = getattr(chunk, 'usage', None)
                    if usage and hasattr(usage, 'completion_tokens'):
                        output_tokens = usage.completion_tokens or output_tokens

                    if chunk_count <= 5:
                        has_content = False
                        if choices and hasattr(choices[0], 'delta'):
                            has_content = bool(getattr(choices[0].delta, 'content', None))
                        self.logger.debug(
                            f"chunk #{chunk_count}: choices={bool(choices)}, delta has content={has_content}"
                        )

                    if not choices:
                        continue

                    choice = choices[0]
                    delta = choice.delta
                    if getattr(choice, 'finish_reason', None) is not None:
                        final_finish_reason = choice.finish_reason

                    # 处理文本内容
                    if delta.content:
                        # 如果还没有开始文本内容块，先开始
                        if not text_block_open:
                            text_block_index = next_block_index
                            next_block_index += 1
                            yield self.converter.create_sse_event(
                                self.converter.EVENT_CONTENT_BLOCK_START,
                                {"type": "content_block_start", "index": text_block_index,
                                 "content_block": {"type": "text", "text": ""}}
                            )
                            text_block_open = True

                        content = delta.content
                        yield self.converter.create_content_delta_event(content, text_block_index)

                    # 处理 tool_calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        has_tool_calls = True

                        # 如果之前有文本内容，先结束它
                        if text_block_open and text_block_index is not None:
                            yield self.converter.create_content_block_stop_event(text_block_index)
                            text_block_open = False

                        for tool_call in delta.tool_calls:
                            tc_index = tool_call.index if tool_call.index is not None else len(tool_states)
                            function = getattr(tool_call, 'function', None)
                            call_id = getattr(tool_call, 'id', None)
                            func_name = getattr(function, 'name', None) if function else None
                            args_delta = getattr(function, 'arguments', None) if function else None

                            state = tool_states.get(tc_index)
                            if state is None:
                                state = {
                                    "anthropic_index": next_block_index,
                                    "id": call_id or f"call_{tc_index}",
                                    "name": func_name or f"tool_{tc_index}",
                                    "started": False,
                                    "args": ""
                                }
                                tool_states[tc_index] = state
                                next_block_index += 1
                            else:
                                if call_id:
                                    state["id"] = call_id
                                if func_name:
                                    state["name"] = func_name

                            if not state["started"]:
                                yield self.converter.create_tool_use_start_event(
                                    state["anthropic_index"],
                                    state["id"],
                                    state["name"]
                                )
                                state["started"] = True
                                self.logger.debug(
                                    f"新工具调用: openai_index={tc_index}, anthropic_index={state['anthropic_index']}, id={state['id']}, name={state['name']}"
                                )

                            # 按协议发送“增量片段”，而不是累计字符串
                            if args_delta:
                                state["args"] += args_delta
                                yield self.converter.create_tool_use_delta_event(
                                    state["anthropic_index"],
                                    args_delta
                                )

                # 结束所有未结束的内容块
                if text_block_open and text_block_index is not None:
                    yield self.converter.create_content_block_stop_event(text_block_index)

                for tc_index in sorted(tool_states.keys()):
                    state = tool_states[tc_index]
                    if state.get("started"):
                        yield self.converter.create_content_block_stop_event(
                            state["anthropic_index"]
                        )

                self.logger.debug(
                    f"Stream ending: has_tool_calls={has_tool_calls}, chunks={chunk_count}, finish_reason={final_finish_reason}"
                )

                # 发送结束事件
                stop_reason = self.converter.map_stop_reason(
                    final_finish_reason, has_tool_calls=has_tool_calls
                )
                yield self.converter.create_stream_end_events(
                    output_tokens=output_tokens,
                    stop_reason=stop_reason
                )

                self.logger.debug("Stream completed successfully")

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
        import time

        # 检查是否有 tool_calls
        if response.choices and response.choices[0].message:
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # 转换 tool_calls 到 Anthropic 格式
                content_blocks = []

                # 兼容“文本 + 工具调用”同回合输出
                text_content = getattr(message, 'content', None)
                if text_content and str(text_content).strip():
                    content_blocks.append({
                        "type": "text",
                        "text": str(text_content)
                    })

                for tc in message.tool_calls:
                    try:
                        # 解析 arguments
                        import json as json_lib
                        arguments = tc.function.arguments
                        if isinstance(arguments, str):
                            input_data = json_lib.loads(arguments)
                        else:
                            input_data = arguments

                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.function.name,
                            "input": input_data
                        })
                    except Exception as e:
                        self.logger.warning(f"解析 tool_call 参数失败: {e}")
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.function.name,
                            "input": {}
                        })

                # 提取使用量
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, 'usage') and response.usage:
                    if hasattr(response.usage, 'prompt_tokens'):
                        input_tokens = response.usage.prompt_tokens
                    if hasattr(response.usage, 'completion_tokens'):
                        output_tokens = response.usage.completion_tokens

                anthropic_response = {
                    "id": f"msg_{int(time.time() * 1000)}",
                    "type": "message",
                    "role": "assistant",
                    "content": content_blocks,
                    "model": model_id,
                    "stop_reason": self.converter.map_stop_reason(
                        response.choices[0].finish_reason, has_tool_calls=True
                    ),
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }
                }
                self.logger.info(f"响应成功: {len(content_blocks)} 个工具调用")
                return jsonify(anthropic_response)

        # 普通文本响应（原有逻辑）
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

    def _is_port_available(self, port: int, host: str = '127.0.0.1') -> bool:
        """检查端口是否可用

        Args:
            port: 端口号
            host: 主机地址

        Returns:
            端口可用返回True，否则返回False
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
            return True
        except OSError:
            return False

    def _find_available_port(self, start_port: int, host: str = '127.0.0.1', max_tries: int = 100) -> int:
        """从 start_port 开始寻找可用端口

        Args:
            start_port: 起始端口号
            host: 主机地址
            max_tries: 最大尝试次数

        Returns:
            可用的端口号，如果都不可用则返回start_port
        """
        for port in range(start_port, start_port + max_tries):
            if self._is_port_available(port, host):
                return port
        return start_port

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
        requested_port = port or proxy_config.get('port', 8080)

        # 检查端口是否可用，如果不可用则寻找新端口
        if not self._is_port_available(requested_port, host):
            self.logger.warning(f"端口 {requested_port} 被占用，正在寻找可用端口...")
            actual_port = self._find_available_port(requested_port, host)
            if actual_port != requested_port:
                self.logger.info(f"使用备用端口: {actual_port}")
                port = actual_port
            else:
                self.logger.error(f"无法找到可用端口（尝试了 {requested_port}-{requested_port + 100}）")
                return False
        else:
            port = requested_port

        if not self.client:
            self.logger.error("OpenAI客户端未初始化，无法启动代理")
            return False

        try:
            # 使用可关闭的WSGI Server，确保 stop() 能真正停止监听
            self.http_server = make_server(host, port, self.app, threaded=True)
        except OSError as e:
            self.logger.error(f"创建HTTP服务器失败: {e}")
            self.http_server = None
            return False

        def run_flask():
            """在单独线程中运行Flask"""
            try:
                if self.http_server:
                    self.http_server.serve_forever()
            except Exception as e:
                if self.running:
                    self.logger.error(f"HTTP服务器运行异常: {e}")

        self.thread = threading.Thread(target=run_flask, daemon=True)
        self.running = True
        self.actual_port = port  # 保存实际使用的端口
        self.start_time = time.time()
        self.request_count = 0
        self.thread.start()

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

        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except Exception as e:
                self.logger.warning(f"关闭HTTP服务器失败: {e}")
            finally:
                self.http_server = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        self.thread = None
        self.actual_port = None

        self.logger.info("代理服务器已停止")

        return True

    def get_status(self) -> Dict:
        """获取服务器状态

        Returns:
            状态字典
        """
        with self._request_lock:
            request_count = self.request_count
        return {
            "running": self.running,
            "request_count": request_count,
            "uptime": self._get_uptime(),
            "host": self.config.get('proxy', {}).get('host', '127.0.0.1'),
            "port": self.actual_port or self.config.get('proxy', {}).get('port', 8080)
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
