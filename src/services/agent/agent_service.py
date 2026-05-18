from __future__ import annotations

import base64
import json
import logging
import re
from io import BytesIO
from typing import Any, Optional

from src.models.schemas import Action, ChatResponse
from src.services.agent.gemini_client import GeminiClient
from src.services.agent.tool_executor import ToolExecutor
from src.utils.image_fetcher import fetch_cloudinary_image

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class AgentService:
    """Stateless chat agent service that runs a bounded tool-calling loop."""

    def __init__(self, gemini_client: GeminiClient, tool_executor: ToolExecutor) -> None:
        """Initialize agent service with Gemini client and tool executor."""
        self._gemini_client = gemini_client
        self._tool_executor = tool_executor

    async def run(
        self,
        user_id: str,
        message: str,
        history: list[dict[str, Any]],
        cloudinary_public_id: str | None = None,
    ) -> ChatResponse:
        """Run the agentic loop and return user reply plus backend actions."""
        messages = await self._build_messages(history=history)
        backend_actions: list[Action] = []
        messages.append(
            await self._build_current_turn(
                message=message,
                cloudinary_public_id=cloudinary_public_id,
            )
        )

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._gemini_client.generate(messages)
            function_call = self._extract_function_call(response)

            if function_call is None:
                logger.info("Agent response did not include a tool call")
                text_reply = self._extract_text(response)
                if text_reply:
                    safe_reply = self._sanitize_reply(text_reply, backend_actions)
                    return ChatResponse(reply=safe_reply, actions=backend_actions or None)
                return ChatResponse(
                    reply="I couldn't generate a response right now. Please try again.",
                    actions=backend_actions or None,
                )

            tool_name, tool_args = function_call
            logger.info("Agent requested tool call: %s args=%s", tool_name, tool_args)
            tool_args = dict(tool_args or {})
            if tool_name == "get_user_context" and "user_id" not in tool_args:
                tool_args["user_id"] = user_id
                logger.info("Injected missing user_id into get_user_context args")

            tool_result = await self._tool_executor.execute(
                tool_name=tool_name,
                tool_args=tool_args,
            )
            logger.info("Tool execution result for %s: %s", tool_name, tool_result)

            if tool_name == "search_similar_images":
                cloudinary_ids = self._extract_cloudinary_ids(tool_result)
                backend_actions.append(
                    Action(
                        type="search_similar_images_result",
                        parameters={
                            "cloudinary_public_ids": cloudinary_ids,
                            "result": tool_result,
                        },
                    )
                )

            messages.append(
                {
                    "role": "model",
                    "parts": [
                        {
                            "function_call": {
                                "name": tool_name,
                                "args": tool_args,
                            }
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": tool_name,
                                "response": tool_result,
                            }
                        }
                    ],
                }
            )

        return ChatResponse(
            reply="I'm having trouble completing your request. Please try again.",
            actions=backend_actions or None,
        )

    async def _build_messages(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert persisted history records into Gemini message content format."""
        messages: list[dict[str, Any]] = []
        for entry in history or []:
            role = str(entry.get("role", "USER")).upper()
            gemini_role = "model" if role == "ASSISTANT" else "user"

            parts: list[dict[str, Any]] = []
            tool_calls = entry.get("tool_calls")
            if isinstance(tool_calls, dict):
                image_id = tool_calls.get("cloudinary_public_id")
                if image_id:
                    b64_image = await self._fetch_image_as_b64(str(image_id))
                    parts.append(
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_image,
                            }
                        }
                    )

            text_content = str(entry.get("content") or "")
            parts.append({"text": text_content})

            messages.append({"role": gemini_role, "parts": parts})

        return messages

    async def _build_current_turn(
        self,
        message: str,
        cloudinary_public_id: Optional[str],
    ) -> dict[str, Any]:
        """Build current user turn including optional image and required text."""
        parts: list[dict[str, Any]] = []

        if cloudinary_public_id:
            b64_image = await self._fetch_image_as_b64(cloudinary_public_id)
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64_image,
                    }
                }
            )

        parts.append({"text": message})
        return {"role": "user", "parts": parts}

    async def _fetch_image_as_b64(self, cloudinary_public_id: str) -> str:
        """Fetch image from Cloudinary and encode it as base64 JPEG."""
        image = await fetch_cloudinary_image(cloudinary_public_id)
        rgb_image = image.convert("RGB")

        buffer = BytesIO()
        rgb_image.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _extract_function_call(self, response: Any) -> tuple[str, dict[str, Any]] | None:
        """Extract the first function call from Gemini response, if any."""
        # google.genai commonly exposes calls in response.function_calls
        function_calls = getattr(response, "function_calls", None) or []
        if function_calls:
            first_call = function_calls[0]
            name = getattr(first_call, "name", None)
            args: Any = getattr(first_call, "args", None)

            if isinstance(first_call, dict):
                name = first_call.get("name", name)
                args = first_call.get("args", args)

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            if name:
                return str(name), dict(args or {})

        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None

        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []

        for part in parts:
            function_call = getattr(part, "function_call", None)
            if function_call is None and isinstance(part, dict):
                function_call = part.get("function_call")
            if function_call is None:
                continue

            name = getattr(function_call, "name", None)
            args: Any = getattr(function_call, "args", {})
            if isinstance(function_call, dict):
                name = function_call.get("name", name)
                args = function_call.get("args", args)

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            if name:
                return str(name), dict(args or {})

        return None

    def _extract_text(self, response: Any) -> str:
        """Extract plain text from the first candidate parts in Gemini response."""
        direct_text = getattr(response, "text", None)
        if direct_text:
            return str(direct_text).strip()

        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return ""

        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []

        text_parts: list[str] = []
        for part in parts:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            if text:
                text_parts.append(str(text))

        return "\n".join(text_parts).strip()

    def _sanitize_reply(self, reply: str, actions: list[Action]) -> str:
        """Redact cloudinary public IDs from user-facing text replies."""
        sanitized = reply
        action_payload = [action.model_dump() for action in actions]
        for cloudinary_id in self._extract_cloudinary_ids(action_payload):
            sanitized = sanitized.replace(cloudinary_id, "[image]")
        return sanitized

    def _extract_cloudinary_ids(self, payload: Any) -> list[str]:
        """Collect cloudinary public IDs from nested payloads."""
        found: set[str] = set()

        def walk(value: Any, parent_key: str | None = None) -> None:
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    walk(nested_value, str(key))
                return

            if isinstance(value, list):
                for item in value:
                    walk(item, parent_key)
                return

            if not isinstance(value, str):
                return

            lower_key = (parent_key or "").lower()
            looks_like_cloudinary_key = "cloudinary" in lower_key or "public_id" in lower_key
            looks_like_cloudinary_value = bool(re.match(r"^[A-Za-z0-9_\-/]+$", value) and "/" in value)

            if looks_like_cloudinary_key and looks_like_cloudinary_value:
                found.add(value)

        walk(payload)
        return sorted(found)
