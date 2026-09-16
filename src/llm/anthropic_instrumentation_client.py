"""Anthropic native SDK adapter for instrumentation requests."""
from typing import Any, Dict, List, Tuple

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class AnthropicInstrumentationClient:
    """Adapter for official Anthropic SDK used for insert_print instrumentation."""

    def __init__(self, api_key: str, base_url: str, timeout: int):
        if not Anthropic:
            raise ImportError("anthropic package required for provider=anthropic")
        self.client = Anthropic(api_key=api_key, base_url=base_url, timeout=timeout)

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        effort: str,
        temperature: Any,
    ) -> Tuple[str, Dict[str, int]]:
        """Generate response using Anthropic SDK and normalize to OpenAI-compatible format."""

        # Split system messages from the rest
        system_messages = []
        user_assistant_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg["content"])
            elif msg.get("role") in ("user", "assistant"):
                user_assistant_messages.append(msg)

        # Build request
        request_kwargs = {
            "model": model,
            "messages": user_assistant_messages,
            "max_tokens": max_tokens,
        }

        # Add system with prompt caching
        if system_messages:
            combined_system = "\n\n".join(system_messages)
            request_kwargs["system"] = [
                {
                    "type": "text",
                    "text": combined_system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Add output_config with effort if provided
        if effort:
            request_kwargs["output_config"] = {"effort": effort}

        # Make request
        response = self.client.messages.create(**request_kwargs)

        # Extract text content from response blocks
        content_parts = []
        for block in response.content:
            if isinstance(block, dict) and block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif hasattr(block, "type") and block.type == "text":
                content_parts.append(getattr(block, "text", ""))

        content = "".join(content_parts)

        # Normalize usage to OpenAI keys
        usage_dict = {}
        raw_usage = getattr(response, "usage", None)
        if raw_usage:
            if isinstance(raw_usage, dict):
                input_tokens = raw_usage.get("input_tokens")
                output_tokens = raw_usage.get("output_tokens")
            else:
                input_tokens = getattr(raw_usage, "input_tokens", None)
                output_tokens = getattr(raw_usage, "output_tokens", None)

            if isinstance(input_tokens, (int, float)):
                usage_dict["prompt_tokens"] = int(input_tokens)
            if isinstance(output_tokens, (int, float)):
                usage_dict["completion_tokens"] = int(output_tokens)
            if "prompt_tokens" in usage_dict and "completion_tokens" in usage_dict:
                usage_dict["total_tokens"] = (
                    usage_dict["prompt_tokens"] + usage_dict["completion_tokens"]
                )

        return content, usage_dict
