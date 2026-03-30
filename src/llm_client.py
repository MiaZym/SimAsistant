from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator, Iterable, Optional

import requests


class CancelledError(RuntimeError):
    pass


def _should_cancel(cancel_check: Optional[Callable[[], bool]]) -> bool:
    return bool(cancel_check and cancel_check())


@dataclass(frozen=True)
class LLMModels:
    models: list[str]
    api_type: str | None = None  # for ollama: native|openai


class LLMClient:
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        timeout_sec: int = 600,
        ollama_api_type: str | None = None,
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.ollama_api_type = ollama_api_type  # native|openai for provider=ollama

    @staticmethod
    def normalize_provider(provider: str) -> str:
        provider = (provider or "").lower().strip()
        if provider in {"ollama", "vllm", "custom"}:
            return provider
        return "custom"

    def detect_ollama_api_type(self) -> str:
        if self.ollama_api_type in {"native", "openai"}:
            return self.ollama_api_type

        # Try native Ollama: /api/tags + /api/chat returns NDJSON chunks
        try:
            url = f"{self.base_url}/api/tags"
            r = requests.get(url, timeout=self.timeout_sec)
            if r.ok:
                data = r.json() or {}
                models = data.get("models") or []
                if models:
                    self.ollama_api_type = "native"
                    return "native"
        except Exception:
            pass

        self.ollama_api_type = "openai"
        return "openai"

    def list_models(self) -> LLMModels:
        provider = self.normalize_provider(self.provider)

        if provider == "ollama":
            api_type = self.detect_ollama_api_type()
            if api_type == "native":
                r = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout_sec)
                r.raise_for_status()
                data = r.json() or {}
                models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
                return LLMModels(models=models, api_type="native")

            r = requests.get(f"{self.base_url}/v1/models", timeout=self.timeout_sec)
            r.raise_for_status()
            data = r.json() or {}
            models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
            return LLMModels(models=models, api_type="openai")

        # vllm or custom: OpenAI compatible
        r = requests.get(f"{self.base_url}/v1/models", timeout=self.timeout_sec)
        r.raise_for_status()
        data = r.json() or {}
        models = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
        return LLMModels(models=models, api_type=None)

    def _build_messages(self, system_prompt: str | None, user_prompt: str) -> list[dict]:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        return msgs

    def _openai_stream(self, *, url: str, payload: dict, cancel_check: Optional[Callable[[], bool]]) -> Generator[str, None, None]:
        with requests.post(url, json=payload, stream=True, timeout=self.timeout_sec) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if _should_cancel(cancel_check):
                    resp.close()
                    raise CancelledError()

                if not line:
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    import json

                    chunk = json.loads(data)
                except Exception:
                    try:
                        import json

                        chunk = json.loads(data)
                    except Exception:
                        continue

                delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content

    def _ollama_native_stream(
        self, *, url: str, payload: dict, cancel_check: Optional[Callable[[], bool]]
    ) -> Generator[str, None, None]:
        with requests.post(url, json=payload, stream=True, timeout=self.timeout_sec) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if _should_cancel(cancel_check):
                    resp.close()
                    raise CancelledError()
                if not line:
                    continue
                try:
                    import json

                    chunk = json.loads(line)
                except Exception:
                    try:
                        import json

                        chunk = json.loads(line)
                    except Exception:
                        continue

                content = (chunk.get("message") or {}).get("content")
                if content:
                    yield str(content)

    def chat_completion(
        self,
        *,
        model: str,
        system_prompt: str | None,
        user_prompt: str,
        temperature: float = 0.2,
        stream: bool = False,
        cancel_check: Optional[Callable[[], bool]] = None,
        messages: list[dict] | None = None,
    ) -> str | Generator[str, None, None]:
        """
        Возвращает либо полный текст (stream=False),
        либо генератор токенов (stream=True).

        Если передан messages — используется как есть (system_prompt добавляется в начало).
        Иначе формируется из system_prompt + user_prompt.
        """
        provider = self.normalize_provider(self.provider)
        if messages:
            msgs: list[dict] = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend(messages)
        else:
            msgs = self._build_messages(system_prompt, user_prompt)
        temperature = float(temperature)

        if provider == "ollama" and self.detect_ollama_api_type() == "native":
            url = f"{self.base_url}/api/chat"
            payload = {"model": model, "messages": msgs, "stream": bool(stream), "options": {"temperature": temperature}}
            if not stream:
                r = requests.post(url, json=payload, timeout=self.timeout_sec)
                r.raise_for_status()
                data = r.json() or {}
                return (data.get("message") or {}).get("content") or ""

            return self._ollama_native_stream(url=url, payload=payload, cancel_check=cancel_check)

        # OpenAI compatible endpoint
        url = f"{self.base_url}/v1/chat/completions"
        payload = {"model": model, "messages": msgs, "stream": bool(stream), "temperature": temperature}

        if not stream:
            r = requests.post(url, json=payload, timeout=self.timeout_sec)
            r.raise_for_status()
            data = r.json() or {}
            return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""

        return self._openai_stream(url=url, payload=payload, cancel_check=cancel_check)

