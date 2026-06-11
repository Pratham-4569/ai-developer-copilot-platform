"""LLM provider adapter.

Implements the OpenAI-compatible ``/v1/chat/completions`` API via
``httpx.AsyncClient``. Switch providers without code changes by setting
``LLM_BASE_URL`` to any compatible endpoint:

    OpenAI:        https://api.openai.com
    Azure OpenAI:  https://<resource>.openai.azure.com/openai
    Groq:          https://api.groq.com/openai
    Together AI:   https://api.together.xyz
    Ollama:        http://localhost:11434

Provides two calling modes:
    ``complete()`` — single-shot request, returns the full response string.
    ``stream()``   — streaming SSE request, yields token fragments as they arrive.

This adapter is consumed by the Chat Service (Phase 8) and all LangGraph
agents (Phases 10–18). Neither the Chat Service nor any agent imports
``httpx`` directly — all LLM I/O goes through this adapter.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings


class LLMError(Exception):
    """Raised when the LLM API returns an error or the request times out.

    Args:
        message:     Human-readable error description.
        status_code: HTTP status code from the API, if available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMAdapter:
    """Async adapter for OpenAI-compatible ``/v1/chat/completions`` APIs.

    Args:
        base_url:        Root URL of the LLM provider (no trailing slash needed).
        api_key:         Bearer token sent in the ``Authorization`` header.
        model:           Model identifier (e.g., ``"gpt-4o"``).
        timeout_seconds: Read timeout in seconds for non-streaming requests.
        max_retries:     Number of retry attempts on transient errors.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 3,
    ) -> None:
        self._model = model
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip('/'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(timeout_seconds),
                write=30.0,
                pool=5.0,
            ),
        )

    async def aclose(self) -> None:
        """Close the underlying ``httpx.AsyncClient``."""
        await self._client.aclose()

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request and return the full response text.

        Args:
            messages:      Conversation history as a list of
                           ``{"role": "user"|"assistant", "content": "..."}`` dicts.
            system_prompt: Optional system message prepended before all turns.
            temperature:   Sampling temperature (0–2). Lower = more deterministic.
            max_tokens:    Maximum completion tokens. ``None`` uses the model default.

        Returns:
            The assistant's response content as a plain string.

        Raises:
            LLMError: On API errors, non-200 responses, or timeout after all retries.
        """
        payload = self._build_payload(
            messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = await self._client.post('/v1/chat/completions', json=payload)
                if response.status_code != 200:
                    raise LLMError(
                        f'LLM API error {response.status_code}: {response.text}',
                        status_code=response.status_code,
                    )
                data = response.json()
                return str(data['choices'][0]['message']['content'])
            except LLMError:
                raise  # Do not retry API-level errors (4xx, 5xx)
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    continue
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    continue

        raise LLMError(f'LLM request failed after {self._max_retries} retries: {last_exc}')

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion, yielding text token fragments as they arrive.

        Uses the OpenAI server-sent events (SSE) streaming format:
        each line starting with ``data: `` contains a JSON chunk; the
        stream ends with ``data: [DONE]``.

        Args:
            messages:      Conversation history.
            system_prompt: Optional system message.
            temperature:   Sampling temperature.
            max_tokens:    Maximum completion tokens.

        Yields:
            String fragments (delta tokens) as they arrive from the API.

        Raises:
            LLMError: On API errors or connection timeout.
        """
        payload = self._build_payload(
            messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        try:
            async with self._client.stream(
                'POST', '/v1/chat/completions', json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise LLMError(
                        f'LLM streaming error {response.status_code}: {body.decode()}',
                        status_code=response.status_code,
                    )
                async for line in response.aiter_lines():
                    if not line or line == 'data: [DONE]':
                        continue
                    if not line.startswith('data: '):
                        continue
                    raw = line[len('data: '):]
                    try:
                        chunk = json.loads(raw)
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content')
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue  # Malformed chunk — skip silently
        except httpx.TimeoutException as exc:
            raise LLMError('LLM streaming request timed out') from exc
        except httpx.RequestError as exc:
            raise LLMError(f'LLM streaming connection failed: {exc}') from exc

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict[str, object]:
        """Assemble the ``/v1/chat/completions`` request body."""
        conversation: list[dict[str, str]] = []
        if system_prompt:
            conversation.append({'role': 'system', 'content': system_prompt})
        conversation.extend(messages)

        payload: dict[str, object] = {
            'model': self._model,
            'messages': conversation,
            'temperature': temperature,
            'stream': stream,
        }
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        return payload


# ---------------------------------------------------------------------------
# Module-level singleton — initialized from app lifespan
# ---------------------------------------------------------------------------

class _LLMState:
    adapter: LLMAdapter | None = None


_state = _LLMState()


def initialize_llm() -> None:
    """Create the LLM adapter.

    Must be called from the application lifespan startup handler.
    """
    settings = get_settings()
    _state.adapter = LLMAdapter(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


async def dispose_llm() -> None:
    """Close the LLM adapter HTTP client.

    Must be called from the application lifespan shutdown handler.
    """
    if _state.adapter is not None:
        await _state.adapter.aclose()
        _state.adapter = None


def get_llm() -> LLMAdapter:
    """Return the active LLM adapter.

    Raises:
        RuntimeError: If ``initialize_llm()`` has not been called.
    """
    if _state.adapter is None:
        raise RuntimeError(
            'LLM adapter not initialized. Call initialize_llm() from the app lifespan.'
        )
    return _state.adapter
