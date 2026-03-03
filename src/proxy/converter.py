#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API格式转换模块

负责将Anthropic API格式与OpenAI API格式进行相互转换。
Claude Code使用Anthropic API格式，而讯飞星辰MaaS使用OpenAI API格式。
"""

import json
from typing import Any, Dict, List, Optional


class APIConverter:
    """Anthropic API 与 OpenAI API 格式转换器

    提供双向转换功能：
    - Anthropic → OpenAI：将请求从Anthropic格式转换为OpenAI格式
    - OpenAI → Anthropic：将响应从OpenAI格式转换为Anthropic格式
    """

    # Anthropic事件类型
    EVENT_MESSAGE_START = "message_start"
    EVENT_CONTENT_BLOCK_START = "content_block_start"
    EVENT_CONTENT_BLOCK_DELTA = "content_block_delta"
    EVENT_CONTENT_BLOCK_STOP = "content_block_stop"
    EVENT_MESSAGE_DELTA = "message_delta"
    EVENT_MESSAGE_STOP = "message_stop"
    EVENT_ERROR = "error"

    @staticmethod
    def anthropic_to_openai_messages(anthropic_messages: List[Dict]) -> List[Dict[str, Any]]:
        """将Anthropic消息格式转换为OpenAI格式

        Anthropic格式的content可以是字符串或数组（包含text、tool_use、tool_result等类型）。
        OpenAI格式使用简单的role/content结构，工具调用使用tool_calls和role:tool。

        Args:
            anthropic_messages: Anthropic格式的消息列表

        Returns:
            OpenAI格式的消息列表

        Examples:
            输入: [{"role": "user", "content": "你好"}]
            输出: [{"role": "user", "content": "你好"}]

            工具调用输入: [{"role": "assistant", "content": [{"type": "tool_use", "name": "bash", ...}]}]
            工具调用输出: [{"role": "assistant", "content": "", "tool_calls": [...]}]
        """
        openai_messages = []

        for msg in anthropic_messages:
            role = msg.get('role', 'user')
            content = msg.get('content')

            if isinstance(content, str):
                # 简单字符串内容
                openai_messages.append({"role": role, "content": content})

            elif isinstance(content, list):
                # 数组格式内容 - 需要特殊处理 tool_use
                # 检查是否有 tool_use
                has_tool_use = any(p.get('type') == 'tool_use' for p in content)

                if has_tool_use:
                    # 如果有 tool_use，将所有内容合并到一条 assistant 消息中
                    # OpenAI 格式：assistant 消息可以同时有 content 和 tool_calls
                    text_parts = []
                    tool_calls = []

                    for part in content:
                        part_type = part.get('type')

                        if part_type == 'text':
                            text_parts.append(part.get('text', ''))
                        elif part_type == 'tool_use':
                            tool_call = {
                                "id": part.get('id', f"call_{len(openai_messages)}"),
                                "type": "function",
                                "function": {
                                    "name": part.get('name', ''),
                                    "arguments": json.dumps(part.get('input', {}), ensure_ascii=False)
                                }
                            }
                            tool_calls.append(tool_call)

                    # 创建一条 assistant 消息，同时包含 content 和 tool_calls
                    openai_messages.append({
                        "role": "assistant",
                        "content": ''.join(text_parts),
                        "tool_calls": tool_calls
                    })

                    # 处理 tool_result（如果有的话）
                    for part in content:
                        if part.get('type') == 'tool_result':
                            tool_use_id = part.get('tool_use_id', '')
                            result_content = part.get('content', '')

                            if isinstance(result_content, list):
                                result_content = json.dumps(result_content, ensure_ascii=False)
                            elif result_content is None:
                                result_content = ""

                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_use_id,
                                "content": str(result_content)
                            })
                else:
                    # 没有 tool_use，正常处理 text 和 tool_result
                    for part in content:
                        part_type = part.get('type')

                        if part_type == 'text':
                            openai_messages.append({
                                "role": role,
                                "content": part.get('text', '')
                            })
                        elif part_type == 'tool_result':
                            tool_use_id = part.get('tool_use_id', '')
                            result_content = part.get('content', '')

                            if isinstance(result_content, list):
                                result_content = json.dumps(result_content, ensure_ascii=False)
                            elif result_content is None:
                                result_content = ""

                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_use_id,
                                "content": str(result_content)
                            })

            else:
                # 其他情况，添加默认内容
                openai_messages.append({"role": role, "content": ""})

        return openai_messages

    @staticmethod
    def anthropic_to_openai_tools(anthropic_tools: List[Dict]) -> List[Dict]:
        """将 Anthropic tools 格式转换为 OpenAI 格式

        Anthropic 格式:
        {
            "name": "bash",
            "description": "...",
            "input_schema": {...}
        }

        OpenAI 格式:
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "...",
                "parameters": {...}
            }
        }

        Args:
            anthropic_tools: Anthropic格式的工具定义列表

        Returns:
            OpenAI格式的工具定义列表
        """
        openai_tools = []

        for tool in anthropic_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get('name', ''),
                    "description": tool.get('description', ''),
                    "parameters": tool.get('input_schema', {})
                }
            })

        return openai_tools

    @staticmethod
    def anthropic_to_openai_tool_choice(tool_choice: Any) -> Optional[str]:
        """将 Anthropic tool_choice 转换为 MaaS 兼容格式

        MaaS 当前兼容层要求 tool_choice 为字符串：
        - "auto"
        - "none"
        - "required"

        对于 Anthropic 的特定工具选择（type=tool, name=xxx），
        降级为 "required" 以保证至少触发工具调用。
        """
        if tool_choice is None:
            return None

        if isinstance(tool_choice, str):
            normalized = tool_choice.strip().lower()
            if normalized in {"auto", "none", "required"}:
                return normalized
            # 不支持的字符串值默认降级为 auto
            return "auto"

        if isinstance(tool_choice, dict):
            tc_type = str(tool_choice.get("type", "")).strip().lower()
            if tc_type in {"auto", "none", "required"}:
                return tc_type
            if tc_type == "any":
                return "required"
            if tc_type == "tool":
                # MaaS 不支持对象格式的指定工具，降级为 required
                return "required"

        return None

    @staticmethod
    def openai_to_anthropic_response(
        openai_response: Any,
        model_id: str,
        message_id: Optional[str] = None
    ) -> Dict:
        """将OpenAI响应格式转换为Anthropic格式

        Args:
            openai_response: OpenAI SDK返回的响应对象
            model_id: 模型ID
            message_id: 可选的消息ID，默认自动生成

        Returns:
            Anthropic格式的响应字典

        Examples:
            {
                "id": "msg_1234567890",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "回复内容"}],
                "model": "xopglm47blth2",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }
        """
        import time

        if message_id is None:
            message_id = f"msg_{int(time.time() * 1000)}"

        # 提取内容
        content = ""
        has_tool_calls = False
        if hasattr(openai_response, 'choices') and openai_response.choices:
            message = openai_response.choices[0].message
            if hasattr(message, 'content'):
                content = message.content or ""

            if hasattr(message, 'tool_calls') and message.tool_calls:
                has_tool_calls = True

        # 提取使用量信息
        input_tokens = 0
        output_tokens = 0
        if hasattr(openai_response, 'usage') and openai_response.usage:
            usage = openai_response.usage
            if hasattr(usage, 'prompt_tokens'):
                input_tokens = usage.prompt_tokens
            if hasattr(usage, 'completion_tokens'):
                output_tokens = usage.completion_tokens

        # 获取停止原因
        stop_reason = "end_turn"
        if hasattr(openai_response, 'choices') and openai_response.choices:
            finish_reason = openai_response.choices[0].finish_reason
            if finish_reason:
                stop_reason = finish_reason

        return {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "model": model_id,
            "stop_reason": APIConverter.map_stop_reason(stop_reason),
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        }

    @staticmethod
    def map_stop_reason(
        finish_reason: Optional[str],
        has_tool_calls: bool = False
    ) -> str:
        """将 OpenAI finish_reason 映射为 Anthropic stop_reason"""
        if finish_reason:
            fr = str(finish_reason).strip().lower()
            if fr in {"tool_calls", "function_call"}:
                return "tool_use"
            if fr == "length":
                return "max_tokens"
            if fr in {"stop", "content_filter"}:
                return "end_turn"

        return "tool_use" if has_tool_calls else "end_turn"

    @staticmethod
    def create_sse_event(event_type: str, data: Dict) -> str:
        """创建服务器发送事件（SSE）格式的字符串

        Args:
            event_type: 事件类型
            data: 事件数据

        Returns:
            SSE格式的字符串

        Examples:
            输入: ("message_start", {"type": "message_start", ...})
            输出: "event: message_start\\ndata: {...}\\n\\n"
        """
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    @staticmethod
    def create_stream_start_events(message_id: str, model_id: str) -> str:
        """创建流式响应的开始事件（只包含 message_start）

        注意：content_block_start 事件将在实际内容到达时动态创建

        Args:
            message_id: 消息ID
            model_id: 模型ID

        Returns:
            SSE格式的事件字符串
        """
        events = []

        # message_start 事件
        message_start_data = {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model_id,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }
        }
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_MESSAGE_START, message_start_data
        ))

        # 注意：不在这里创建 content_block_start
        # 它将在 generate() 中根据实际内容类型（text 或 tool_use）动态创建

        return "".join(events)

    @staticmethod
    def create_content_delta_event(content: str, index: int = 0) -> str:
        """创建内容增量事件

        Args:
            content: 新增的文本内容
            index: 内容块索引，默认为0

        Returns:
            SSE格式的事件字符串
        """
        delta_data = {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": content}
        }
        return APIConverter.create_sse_event(
            APIConverter.EVENT_CONTENT_BLOCK_DELTA, delta_data
        )

    @staticmethod
    def create_stream_end_events(output_tokens: int = 0, stop_reason: str = "end_turn") -> str:
        """创建流式响应的结束事件

        注意：content_block_stop 应该在 generate() 中根据实际 index 发送

        Args:
            output_tokens: 输出token数量
            stop_reason: 停止原因（"end_turn" 或 "tool_use"）

        Returns:
            SSE格式的事件字符串
        """
        events = []

        # content_block_stop 事件已在 generate() 中根据实际 index 发送，不在这里重复

        # message_delta 事件 - 使用动态 stop_reason
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_MESSAGE_DELTA,
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": output_tokens}
            }
        ))

        # message_stop 事件
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_MESSAGE_STOP,
            {"type": "message_stop"}
        ))

        return "".join(events)

    @staticmethod
    def create_tool_use_start_event(index: int, tool_id: str, tool_name: str) -> str:
        """创建 tool_use 开始事件

        Args:
            index: 内容块索引
            tool_id: 工具调用ID
            tool_name: 工具名称

        Returns:
            SSE格式的事件字符串
        """
        data = {
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "tool_use",
                "id": tool_id,
                "name": tool_name,
                "input": {}
            }
        }
        return APIConverter.create_sse_event(APIConverter.EVENT_CONTENT_BLOCK_START, data)

    @staticmethod
    def create_tool_use_delta_event(index: int, json_fragment: str) -> str:
        """创建 tool_use 参数增量事件

        Args:
            index: 内容块索引
            json_fragment: 本次新增的JSON片段（增量）

        Returns:
            SSE格式的事件字符串
        """
        data = {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "input_json_delta", "partial_json": json_fragment}
        }
        return APIConverter.create_sse_event(APIConverter.EVENT_CONTENT_BLOCK_DELTA, data)

    @staticmethod
    def create_content_block_stop_event(index: int) -> str:
        """创建内容块停止事件

        Args:
            index: 内容块索引

        Returns:
            SSE格式的事件字符串
        """
        data = {"type": "content_block_stop", "index": index}
        return APIConverter.create_sse_event(APIConverter.EVENT_CONTENT_BLOCK_STOP, data)

    @staticmethod
    def create_final_tool_use_input_event(index: int, full_input: dict) -> str:
        """创建最终的 tool_use input 事件

        在 stream 结束时发送，确保完整的 input 被正确传递给客户端。
        这是为了解决某些客户端可能无法正确累积 input_json_delta 的问题。

        Args:
            index: 内容块索引
            full_input: 完整的工具输入参数（已解析的 dict）

        Returns:
            SSE格式的事件字符串
        """
        import json
        # 将完整的 input 作为 JSON 字符串发送
        input_json = json.dumps(full_input, ensure_ascii=False)
        data = {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "input_json_delta", "partial_json": input_json}
        }
        return APIConverter.create_sse_event(APIConverter.EVENT_CONTENT_BLOCK_DELTA, data)

    @staticmethod
    def create_error_event(error_message: str) -> str:
        """创建错误事件

        Args:
            error_message: 错误消息

        Returns:
            SSE格式的错误事件字符串
        """
        error_data = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": error_message
            }
        }
        return APIConverter.create_sse_event(APIConverter.EVENT_ERROR, error_data)

    @staticmethod
    def extract_stream_params(request_data: Dict) -> tuple:
        """从请求中提取流式调用参数

        Args:
            request_data: Anthropic格式的请求数据

        Returns:
            (messages, stream, max_tokens, temperature) 元组
        """
        messages = request_data.get('messages', [])
        stream = request_data.get('stream', False)
        max_tokens = request_data.get('max_tokens', 4096)

        temperature = request_data.get('temperature', 0.7)

        return messages, stream, max_tokens, temperature


if __name__ == "__main__":
    # 测试代码
    # 测试消息转换
    anthropic_msg = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"},
        {"role": "user", "content": [{"type": "text", "text": "介绍一下你自己"}]}
    ]

    converter = APIConverter()
    openai_msg = converter.anthropic_to_openai_messages(anthropic_msg)
    print("消息转换结果:")
    print(json.dumps(openai_msg, ensure_ascii=False, indent=2))

    # 测试SSE事件
    print("\n流式开始事件:")
    print(converter.create_stream_start_events("msg_123", "test_model"))

    print("\n内容增量事件:")
    print(converter.create_content_delta_event("你好", 0))

    print("\n流式结束事件:")
    print(converter.create_stream_end_events(10))
