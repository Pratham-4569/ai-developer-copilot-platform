"""Embedding provider adapter.

Implements the OpenAI-compatible ``/v1/embeddings`` API via
``httpx.AsyncClient``. Supports both single-text and batched embedding
requests, with automatic chunking to respect the configured batch size limit.

Input ordering guarantee: the OpenAI API may return embedding objects in any
order within a batch. This adapter sorts all batch results by the ``index``
field before returning to guarantee the output list maps 1-to-1 to the
input list in the same order.

Consumed by:
    Phase 6  — Repository Ingestion Pipeline (chunk embedding)
    Phase 7  — RAG Foundation (query embedding, HyDE embedding)
"""

from __future__ import annotations

import httpx

from app.config import get_settings


class EmbeddingError(Exception):
    """Raised when the embedding API returns an error or the request times out.

    Args:
        message:     Human-readable error description.
        status_code: HTTP status code from the API, if available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class EmbeddingAdapter:
    """Async adapter for OpenAI-compatible ``/v1/embeddings`` APIs.

    Args:
        base_url:        Root URL of the embedding provider.
        api_key:         Bearer token for the ``Authorization`` header.
        model:           Embedding model identifier
                         (e.g., ``"text-embedding-3-large"``).
        batch_size:      Maximum texts per API request. Larger batches
                         reduce round-trips but increase per-request latency.
        timeout_seconds: Read timeout for each API request.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 512,
        timeout_seconds: int = 60,
    ) -> None:
        self._model = model
        self._batch_size = batch_size
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

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the dense embedding vector.

        Raises:
            EmbeddingError: On API errors or timeout.
        """
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, chunking into sub-batches as needed.

        Automatically splits ``texts`` into chunks of at most ``batch_size``
        and issues sequential API requests. Returned vectors are in the same
        order as the input texts regardless of API response ordering.

        Args:
            texts: List of texts to embed. May be empty.

        Returns:
            A list of embedding vectors, one per input text, in input order.

        Raises:
            EmbeddingError: On API errors or timeout for any sub-batch.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_embeddings = await self._embed_chunk(batch)
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    async def _embed_chunk(self, texts: list[str]) -> list[list[float]]:
        """Issue a single ``/v1/embeddings`` request for one batch.

        Args:
            texts: A batch of texts (length ≤ ``self._batch_size``).

        Returns:
            Embedding vectors sorted by the response ``index`` field.

        Raises:
            EmbeddingError: On non-200 response, timeout, or network error.
        """
        payload: dict[str, object] = {'model': self._model, 'input': texts}
        try:
            response = await self._client.post('/v1/embeddings', json=payload)
        except httpx.TimeoutException as exc:
            raise EmbeddingError(f'Embedding request timed out: {exc}') from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(f'Embedding request failed: {exc}') from exc

        if response.status_code != 200:
            raise EmbeddingError(
                f'Embedding API error {response.status_code}: {response.text}',
                status_code=response.status_code,
            )

        data = response.json()
        # Sort by index to preserve input order — the API spec does not
        # guarantee that embedding objects are returned in input order.
        items: list[dict[str, object]] = sorted(data['data'], key=lambda x: int(x['index']))  # type: ignore[arg-type]
        return [item['embedding'] for item in items]  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Module-level singleton — initialized from app lifespan
# ---------------------------------------------------------------------------

class _EmbeddingState:
    adapter: EmbeddingAdapter | None = None


_state = _EmbeddingState()


def initialize_embedding() -> None:
    """Create the embedding adapter.

    Must be called from the application lifespan startup handler.
    """
    settings = get_settings()
    _state.adapter = EmbeddingAdapter(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )


async def dispose_embedding() -> None:
    """Close the embedding adapter HTTP client.

    Must be called from the application lifespan shutdown handler.
    """
    if _state.adapter is not None:
        await _state.adapter.aclose()
        _state.adapter = None


def get_embedding() -> EmbeddingAdapter:
    """Return the active embedding adapter.

    Raises:
        RuntimeError: If ``initialize_embedding()`` has not been called.
    """
    if _state.adapter is None:
        raise RuntimeError(
            'Embedding adapter not initialized. Call initialize_embedding() from the app lifespan.'
        )
    return _state.adapter
