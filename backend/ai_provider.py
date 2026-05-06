import json
import re
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from config import get_env, get_int_env


class AIProviderError(RuntimeError):
    """Raised when the upstream AI provider cannot complete a request."""


@dataclass
class AIProviderStatus:
    enabled: bool
    provider: str
    model: str
    message: str
    base_url: str


class BaseAIProvider:
    def __init__(self, *, provider_name: str, api_key: str, base_url: str, model: str, timeout_seconds: int = 45):
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def get_status(self) -> AIProviderStatus:
        return AIProviderStatus(
            enabled=bool(self.api_key and self.base_url and self.model),
            provider=self.provider_name,
            model=self.model,
            message="ready" if self.api_key else "missing_api_key",
            base_url=self.base_url,
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1400,
    ) -> dict[str, Any]:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseAIProvider):
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1400,
    ) -> dict[str, Any]:
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        raw_response = self._post_json(endpoint, payload)
        content = self._extract_message_content(raw_response)
        return self._parse_json_content(content)

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AIProviderError(f"AI provider HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise AIProviderError(f"AI provider network error: {exc.reason}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise AIProviderError("AI provider returned non-JSON response") from exc

    def _extract_message_content(self, response_json: dict[str, Any]) -> str:
        choices = response_json.get("choices") or []
        if not choices:
            raise AIProviderError("AI provider returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    text_parts.append(item)
            combined = "\n".join(part for part in text_parts if part).strip()
            if combined:
                return combined

        raise AIProviderError("AI provider returned empty content")

    def _parse_json_content(self, content: str) -> dict[str, Any]:
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1))
            except json.JSONDecodeError:
                pass

        object_match = re.search(r"(\{[\s\S]*\})", content)
        if object_match:
            try:
                return json.loads(object_match.group(1))
            except json.JSONDecodeError:
                pass

        raise AIProviderError("AI returned invalid JSON content")


def _build_provider_config() -> tuple[str, str, str, str]:
    provider_name = (get_env("AI_PROVIDER", "alibaba") or "alibaba").strip().lower()

    if provider_name in {"alibaba", "dashscope", "qwen", "aliyun", "bailian"}:
        api_key = (
            get_env("DASHSCOPE_API_KEY")
            or get_env("ALIYUN_DASHSCOPE_API_KEY")
            or get_env("AI_API_KEY")
            or ""
        )
        base_url = get_env(
            "AI_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ) or ""
        model = get_env("AI_MODEL", "qwen-plus") or "qwen-plus"
        return "alibaba", api_key, base_url, model

    if provider_name in {"openai_compatible", "openai", "compatible"}:
        api_key = get_env("AI_API_KEY") or ""
        base_url = get_env("AI_BASE_URL") or ""
        model = get_env("AI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
        return "openai_compatible", api_key, base_url, model

    raise AIProviderError(f"Unsupported AI provider: {provider_name}")


def get_active_ai_provider() -> BaseAIProvider:
    provider_name, api_key, base_url, model = _build_provider_config()
    timeout_seconds = get_int_env("AI_TIMEOUT_SECONDS", 45)
    return OpenAICompatibleProvider(
        provider_name=provider_name,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def get_ai_provider_status() -> AIProviderStatus:
    try:
        provider = get_active_ai_provider()
    except AIProviderError as exc:
        return AIProviderStatus(
            enabled=False,
            provider=(get_env("AI_PROVIDER", "alibaba") or "alibaba").strip().lower(),
            model=get_env("AI_MODEL", "") or "",
            message=str(exc),
            base_url=get_env("AI_BASE_URL", "") or "",
        )

    status = provider.get_status()
    if not status.enabled:
        return AIProviderStatus(
            enabled=False,
            provider=status.provider,
            model=status.model,
            message="missing_api_key",
            base_url=status.base_url,
        )
    return status
