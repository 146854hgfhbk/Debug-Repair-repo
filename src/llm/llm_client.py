from config import InstrumentationLLMConfig, LLMConfig
from openai import OpenAI
from typing import Any, Dict, Tuple
import threading


_log_lock = threading.Lock()

class LLMClient:
    def __init__(self):
        if not OpenAI:
            raise ImportError("OpenAI import失败")

        self.client = OpenAI(api_key=LLMConfig.API_KEY, base_url=LLMConfig.BASE_URL)

        # Conditionally create instrumentation client based on provider
        if InstrumentationLLMConfig.PROVIDER == "anthropic":
            from llm.anthropic_instrumentation_client import AnthropicInstrumentationClient
            self.instrumentation_client = AnthropicInstrumentationClient(
                api_key=InstrumentationLLMConfig.API_KEY,
                base_url=InstrumentationLLMConfig.BASE_URL,
                timeout=LLMConfig.TIMEOUT_LIMIT,
            )
        else:
            # Default to OpenAI
            self.instrumentation_client = OpenAI(
                api_key=InstrumentationLLMConfig.API_KEY,
                base_url=InstrumentationLLMConfig.BASE_URL,
            )

        print(f"LLMClient 已为模型 '{LLMConfig.MODEL}' 初始化。")

    def generate_response(self, msg: list, prompt_name: str):
        """
        调用LLM生成响应

        Args:
            msg: 请求消息, 包括系统消息和用户消息, 格式为[{"role": "system", "content": "xxx"}, {"role": "user", "content": "xxx"}]
            prompt_name: 请求名称, 用于记录日志

        Returns:
            tuple:
                - content: 响应内容
                - usage_info: token 用量信息
        """
        is_instrumentation = prompt_name == "insert_print"
        config = InstrumentationLLMConfig if is_instrumentation else LLMConfig
        print(f"====== BEGIN: Sending Request to LLM : {prompt_name} ======")
        print(f"Model: {config.MODEL}, Temperature: {config.TEMPERATURE}")

        # Use Anthropic adapter for instrumentation when provider=anthropic
        if is_instrumentation and InstrumentationLLMConfig.PROVIDER == "anthropic":
            from llm.anthropic_instrumentation_client import AnthropicInstrumentationClient
            if isinstance(self.instrumentation_client, AnthropicInstrumentationClient):
                for attempt in range(LLMConfig.MAX_RETRIES):
                    try:
                        content, usage_dict = self.instrumentation_client.generate_response(
                            messages=msg,
                            model=config.MODEL,
                            max_tokens=LLMConfig.MAX_TOKEN,
                            effort=config.REASONING_EFFORT,
                            temperature=config.TEMPERATURE,
                        )
                        self._log_to_file(prompt_name, msg, content, "response", usage_dict)
                        return content, usage_dict
                    except Exception as e:
                        print(f"API 调用在第 {attempt + 1}/{LLMConfig.MAX_RETRIES} 次尝试时失败。错误: {e}")
                return "", {}

        # OpenAI path (for repair and provider=openai instrumentation)
        client = self.instrumentation_client if is_instrumentation else self.client

        for attempt in range(LLMConfig.MAX_RETRIES):
            try:
                request = dict(
                    model=config.MODEL,
                    messages=msg,
                    timeout=LLMConfig.TIMEOUT_LIMIT
                )
                if is_instrumentation and config.REASONING_EFFORT:
                    request["reasoning_effort"] = config.REASONING_EFFORT
                if config.TEMPERATURE is not None:
                    request["temperature"] = config.TEMPERATURE
                response = client.chat.completions.create(**request)

                content = ""
                try:
                    choices = getattr(response, "choices", None) or []
                    if choices:
                        first_choice = choices[0]
                        message = getattr(first_choice, "message", None)
                        if isinstance(message, dict):
                            content = message.get("content", "")
                        elif message is not None:
                            content = getattr(message, "content", "")
                        else:
                            content = getattr(first_choice, "text", "")
                except Exception as choice_exc:
                    print(f"解析模型返回内容时出错: {choice_exc}")

                usage_dict = self._parse_usage_info(getattr(response, "usage", None))
                if not usage_dict and hasattr(response, "model_dump"):
                    try:
                        dumped = response.model_dump()
                        usage_dict = self._parse_usage_info(dumped.get("usage"))
                    except Exception as dump_exc:
                        print(f"无法从 model_dump 中解析 usage: {dump_exc}")
                self._log_to_file(prompt_name, msg, content, "response", usage_dict)
                return content or "", usage_dict

            except Exception as e:
                print(f"API 调用在第 {attempt + 1}/{LLMConfig.MAX_RETRIES} 次尝试时失败。错误: {e}")
        return "", {}

    def _parse_usage_info(self, raw_usage: Any) -> Dict[str, int]:
        """将模型返回的 usage 信息规范为简单的字典"""
        usage = {}
        if not raw_usage:
            return usage

        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        if isinstance(raw_usage, dict):
            for key in keys:
                value = raw_usage.get(key)
                if isinstance(value, (int, float)):
                    usage[key] = int(value)
        else:
            for key in keys:
                value = getattr(raw_usage, key, None)
                if isinstance(value, (int, float)):
                    usage[key] = int(value)
        return usage

    def _log_to_file(self, prompt_name, messages, response, log_type, usage=None):
        """日志函数"""
        try:
            import json
            import os
            from datetime import datetime
            from config import BasicConfig
            
            if not BasicConfig.DEBUG_MODE:  # DEBUG模式下记录日志
                return

            log_data = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": prompt_name,
                "type": log_type,
                "request": messages,
                "response": response,
                "tokens": usage
            }
            
            if not os.path.exists(f"{BasicConfig.LOG_PATH}/{LLMConfig.LLM_MODEL}"):
                os.makedirs(f"{BasicConfig.LOG_PATH}/{LLMConfig.LLM_MODEL}")

            with _log_lock:
                with open(f"{BasicConfig.LOG_PATH}/{LLMConfig.LLM_MODEL}/llm_log.jsonl", "a", encoding="utf-8") as f:
                    json.dump(log_data, f, ensure_ascii=False)
                    f.write("\n")
        except:
            print("日志写入失败")
            pass
