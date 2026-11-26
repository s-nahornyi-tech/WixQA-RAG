"""Calls to the embedding provider, the token count and the price (research.md, section 13).

The model, the vector size and the price are attributes of the class, so that a build can
compare them with an existing index before a client or a key is needed. The client is made at
the first request, and only then is `OPENAI_API_KEY` read.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from wixqa_rag import settings

# The limits of one request. By the bound of research.md, section 12, 75,000 characters are at
# most 300,000 tokens, the provider's limit for one request.
MAX_TEXTS = 96
MAX_CHARACTERS = 75_000

# The library waits and tries again after a rate-limit answer or a temporary error.
_RETRIES = 8


@dataclass(frozen=True)
class Embedded:
    """The answer for a list of texts."""

    # One vector for each text, in the order of the texts.
    vectors: list[list[float]]
    # The sum of the usage that the provider reported.
    tokens: int
    # The model name in the provider's responses.
    model: str


def cost_usd(tokens: int, price_usd_per_million_tokens: float) -> float:
    """data-model.md, "Build record": tokens × price per million tokens ÷ 1,000,000."""
    return tokens * price_usd_per_million_tokens / 1_000_000


def _requests(texts: Sequence[str]) -> Iterator[list[str]]:
    """The texts in order, in requests of at most 96 texts and at most 75,000 characters."""
    request: list[str] = []
    characters = 0
    for text in texts:
        if len(text) > MAX_CHARACTERS:
            raise ValueError(f"a text of {len(text)} characters is too long for one request")
        if request and (len(request) == MAX_TEXTS or characters + len(text) > MAX_CHARACTERS):
            yield request
            request, characters = [], 0
        request.append(text)
        characters += len(text)
    if request:
        yield request


class Embedder:
    """Embeds texts with OpenAI `text-embedding-3-small`, one request after another."""

    provider = "openai"
    model = "text-embedding-3-small"
    dimensions = 1536
    # US dollars per million tokens, read from the provider's model page on 2026-11-24.
    price_usd_per_million_tokens = 0.02

    def __init__(self, client=None) -> None:
        self._client = client

    def _the_client(self):
        if self._client is None:
            api_key = settings.openai_api_key()
            import openai

            self._client = openai.OpenAI(api_key=api_key, max_retries=_RETRIES)
        return self._client

    def embed(self, texts: Sequence[str]) -> Embedded:
        """Embed the texts, each as one input and unchanged. An error of the provider that
        the retries do not cure reaches the caller."""
        vectors: list[list[float]] = []
        tokens = 0
        reported = self.model
        for request in _requests(texts):
            response = self._the_client().embeddings.create(model=self.model, input=request)
            data = sorted(response.data, key=lambda item: item.index)
            if len(data) != len(request):
                raise RuntimeError(
                    f"the provider returned {len(data)} vectors for {len(request)} texts"
                )
            vectors.extend(list(item.embedding) for item in data)
            tokens += response.usage.total_tokens
            reported = response.model
        return Embedded(vectors=vectors, tokens=tokens, model=reported)
