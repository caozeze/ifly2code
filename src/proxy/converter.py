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
    def anthropic_to_openai_messages(anthropic_messages: List[Dict]) -> List[Dict[str, str]]:
        """将Anthropic消息格式转换为OpenAI格式

        Anthropic格式的content可以是字符串或数组（包含text和image等类型）。
        OpenAI格式使用简单的role/content结构。

        Args:
            anthropic_messages: Anthropic格式的消息列表

        Returns:
            OpenAI格式的消息列表

        Examples:
            输入: [{"role": "user", "content": "你好"}]
            输出: [{"role": "user", "content": "你好"}]

            输入: [{"role": "user", "content": [{"type": "text", "text": "你好"}]}]
            输出: [{"role": "user", "content": "你好"}]
        """
        openai_messages = []

        for msg in anthropic_messages:
            role = msg.get('role', 'user')
            content = msg.get('content')

            if isinstance(content, str):
                # 简单字符串内容
                openai_messages.append({"role": role, "content": content})

            elif isinstance(content, list):
                # 数组格式内容（可能包含text、image等类型）
                text_parts = []
                for part in content:
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    # 暂时忽略其他类型（如image）
                if text_parts:
                    openai_messages.append({
                        "role": role,
                        "content": ''.join(text_parts)
                    })
                else:
                    # 如果没有text部分，添加空内容
                    openai_messages.append({"role": role, "content": ""})

            else:
                # 其他情况，添加默认内容
                openai_messages.append({"role": role, "content": ""})

        return openai_messages

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
        if hasattr(openai_response, 'choices') and openai_response.choices:
            message = openai_response.choices[0].message
            if hasattr(message, 'content'):
                content = message.content or ""

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
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        }

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
        """创建流式响应的开始事件

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

        # content_block_start 事件
        content_block_start_data = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        }
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_CONTENT_BLOCK_START, content_block_start_data
        ))

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
    def create_stream_end_events(output_tokens: int = 0) -> str:
        """创建流式响应的结束事件

        Args:
            output_tokens: 输出token数量

        Returns:
            SSE格式的事件字符串
        """
        events = []

        # content_block_stop 事件
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_CONTENT_BLOCK_STOP,
            {"type": "content_block_stop", "index": 0}
        ))

        # message_delta 事件
        events.append(APIConverter.create_sse_event(
            APIConverter.EVENT_MESSAGE_DELTA,
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
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

        # 限制max_tokens
        if max_tokens > 16384:
            max_tokens = 16384

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
