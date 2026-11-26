"""The embedder (tasks T038): `src/wixqa_rag/embedding.py`, with a double in place of the
provider's client.

Covers research.md, section 13: the model `text-embedding-3-small` with its vector size 1536;
each passage is one input, sent unchanged; one request carries at most 96 passages and at most
75,000 characters; the tokens embedded are the sum of the usage that the provider reports; the
model name is kept as requested and as reported; any error of the provider stops the work.
data-model.md, "Build record": `cost_usd` = `tokens_embedded` × `price_usd_per_million_tokens`
÷ 1,000,000. FR-010: the price used and the model identifier as specific as the provider
offers.

No request leaves the test: the client double stands for the client of the provider's
library, `openai.OpenAI`, and offers the one call the embedder makes,
`client.embeddings.create(model=..., input=[...])`. These tests need three names from
`embedding.py`:

    class Embedder                         # Embedder(client)
        provider: str                      # "openai"
        model: str                         # the model name sent to the provider
        dimensions: int                    # the size of a vector
        price_usd_per_million_tokens: float
        embed(texts: Sequence[str]) -> an object with
            vectors: list[list[float]]     # one vector for each text, in the order of the texts
            tokens: int                    # the sum of the usage reported for these texts
            model: str                     # the model name in the provider's responses

    cost_usd(tokens: int, price_usd_per_million_tokens: float) -> float

An embedder double with the same attributes and the same `embed` takes the place of
`Embedder` in the integration tests (research.md, section 17). The build reads the four
attributes before it knows whether anything has to be embedded, so they need no client and
no key.

All documents named here are in specs/001-corpus-and-audit/.
"""

import importlib
from types import SimpleNamespace

import pytest

REQUESTED = "text-embedding-3-small"
# The provider may report a more specific identifier than the one requested.
REPORTED = "text-embedding-3-small-as-reported"

MOST_PASSAGES = 96
MOST_CHARACTERS = 75_000


def load_embedding():
    """Import the module; it fails while `src/wixqa_rag/embedding.py` does not exist."""
    return importlib.import_module("wixqa_rag.embedding")


def vector_of(text: str) -> list[float]:
    """A vector of 1536 numbers that tells one text from another."""
    return [float(len(text)), float(sum(text.encode("utf-8")) % 997)] + [0.0] * 1534


class ClientDouble:
    """Stands for `openai.OpenAI`: it keeps every request and answers as the provider does."""

    def __init__(self, *, tokens_of=lambda text: len(text.split()), fail_at_request=None):
        self.requests: list[dict] = []
        self.tokens_of = tokens_of
        self.fail_at_request = fail_at_request
        self.embeddings = SimpleNamespace(create=self._create)

    def _create(self, **request):
        assert not isinstance(request["input"], str), "`input` is a list of texts, not one text"
        self.requests.append(request)
        if self.fail_at_request == len(self.requests):
            raise RuntimeError("the stand-in provider refused the request")
        inputs = request["input"]
        return SimpleNamespace(
            model=REPORTED,
            data=[
                SimpleNamespace(index=place, embedding=vector_of(text), object="embedding")
                for place, text in enumerate(inputs)
            ],
            usage=SimpleNamespace(
                prompt_tokens=sum(self.tokens_of(text) for text in inputs),
                total_tokens=sum(self.tokens_of(text) for text in inputs),
            ),
        )

    @property
    def inputs(self) -> list[list[str]]:
        return [list(request["input"]) for request in self.requests]

    @property
    def sent(self) -> list[str]:
        return [text for inputs in self.inputs for text in inputs]


def embedder_with(client):
    return load_embedding().Embedder(client)


def assert_within_the_limits(client: ClientDouble) -> None:
    for number, inputs in enumerate(client.inputs, start=1):
        assert all(isinstance(text, str) for text in inputs), (
            "each passage is one input: `input` is a list of texts"
        )
        assert 1 <= len(inputs) <= MOST_PASSAGES, (
            f"request {number} carries {len(inputs)} passages; the limit is {MOST_PASSAGES}"
        )
        characters = sum(len(text) for text in inputs)
        assert characters <= MOST_CHARACTERS, (
            f"request {number} carries {characters} characters; the limit is {MOST_CHARACTERS}"
        )


# --- The model, the vector size and the price -------------------------------------------------


def test_the_embedder_names_the_model_the_vector_size_and_the_price():
    """research.md, section 13: OpenAI `text-embedding-3-small` with its default vector size,
    1536, at 0.02 US dollars per million tokens; the price is kept next to the model name."""
    embedder = embedder_with(ClientDouble())

    assert embedder.provider == "openai"
    assert embedder.model == REQUESTED
    assert embedder.dimensions == 1536
    assert embedder.price_usd_per_million_tokens == 0.02


def test_every_request_names_the_model():
    """research.md, section 13: the model is `text-embedding-3-small`."""
    client = ClientDouble()

    embedder_with(client).embed([f"passage {number}" for number in range(200)])

    assert client.requests
    assert all(request["model"] == REQUESTED for request in client.requests)


def test_the_model_name_is_kept_as_requested_and_as_reported():
    """research.md, section 13, and FR-010: the record stores the model name as requested and
    as the provider's response reports it."""
    embedder = embedder_with(ClientDouble())

    embedded = embedder.embed(["one passage", "another passage"])

    assert embedder.model == REQUESTED
    assert embedded.model == REPORTED


# --- Each passage is one input, sent unchanged ------------------------------------------------


def test_each_passage_is_one_input_and_its_text_is_sent_unchanged():
    """research.md, section 13: "Each passage is one input, and its text is sent unchanged."
    The vectors come back one for each text, in the order of the texts."""
    texts = [
        "Reset your password\nUse these steps when you cannot sign in.",
        "  leading and trailing spaces stay  ",
        "The Plus plan costs 9 € per month.",
        "tab\tand no-break space",
        "x",
    ]
    client = ClientDouble()

    embedded = embedder_with(client).embed(texts)

    assert client.sent == texts
    assert [list(vector) for vector in embedded.vectors] == [vector_of(text) for text in texts]
    assert all(len(vector) == 1536 for vector in embedded.vectors)


def test_the_vectors_keep_the_order_of_the_texts_across_requests():
    """research.md, section 13: requests are sent one after another; the vectors of 250
    passages come back in the order of the passages."""
    texts = [f"passage number {number} " + "w" * (number % 13) for number in range(250)]
    client = ClientDouble()

    embedded = embedder_with(client).embed(texts)

    assert client.sent == texts, "every passage is sent once, in order"
    assert [list(vector) for vector in embedded.vectors] == [vector_of(text) for text in texts]


# --- The limits of one request ----------------------------------------------------------------


@pytest.mark.parametrize("passages", [1, 95, 96, 97, 192, 193, 500])
def test_a_request_carries_at_most_96_passages(passages):
    """research.md, section 13: one request carries at most 96 passages."""
    texts = [f"short passage {number}" for number in range(passages)]
    client = ClientDouble()

    embedder_with(client).embed(texts)

    assert_within_the_limits(client)
    assert client.sent == texts


@pytest.mark.parametrize(
    "lengths",
    [
        [2000] * 38,
        [2000] * 96,
        [2000] * 200,
        [1999, 2000, 1, 2000] * 40,
        [75_000 // 96 + 1] * 96,
    ],
    ids=["76,000 characters", "96 full passages", "200 full passages", "mixed", "just over"],
)
def test_a_request_carries_at_most_75000_characters(lengths):
    """research.md, section 13: one request carries at most 75,000 characters, so that by the
    bound of section 12 no request can exceed the provider's 300,000 tokens."""
    texts = [chr(ord("a") + place % 26) * length for place, length in enumerate(lengths)]
    client = ClientDouble()

    embedded = embedder_with(client).embed(texts)

    assert_within_the_limits(client)
    assert client.sent == texts
    assert len(embedded.vectors) == len(texts)


# --- Tokens and cost --------------------------------------------------------------------------


def test_the_tokens_embedded_are_the_sum_of_the_reported_usage():
    """research.md, section 13: "The number of tokens embedded is the sum of
    `usage.total_tokens` over the responses." The double reports 7 tokens for every text."""
    texts = [f"passage {number}" for number in range(250)]
    client = ClientDouble(tokens_of=lambda text: 7)

    embedded = embedder_with(client).embed(texts)

    assert len(client.requests) >= 3
    assert embedded.tokens == 250 * 7


def test_the_tokens_are_those_the_provider_reports_not_an_estimate():
    """research.md, section 13: "The usage that the provider reports is the number the
    provider charges for." The double reports a number that no estimate would give."""
    client = ClientDouble(tokens_of=lambda text: 1_000_003)

    embedded = embedder_with(client).embed(["one", "two", "three"])

    assert embedded.tokens == 3 * 1_000_003


@pytest.mark.parametrize(
    ("tokens", "price", "cost"),
    [
        (180, 0.02, 0.0000036),
        (0, 0.02, 0.0),
        (1_000_000, 0.02, 0.02),
        (12_000_000, 0.02, 0.24),
        (250, 0.5, 0.000125),
    ],
)
def test_the_cost_is_tokens_times_price_per_million(tokens, price, cost):
    """data-model.md, "Build record": `cost_usd` = `tokens_embedded` ×
    `price_usd_per_million_tokens` ÷ 1,000,000. The first row is the example of
    contracts/records.md: 180 tokens at 0.02 cost 0.0000036 US dollars."""
    assert load_embedding().cost_usd(tokens, price) == pytest.approx(cost, rel=1e-12, abs=1e-18)


# --- An error of the provider -----------------------------------------------------------------


@pytest.mark.parametrize("failing_request", [1, 3])
def test_an_error_of_the_provider_stops_the_work(failing_request):
    """research.md, section 13: "Any other error stops the build, and the transaction is
    rolled back." The error reaches the caller, and no further request is sent."""
    texts = [f"passage {number}" for number in range(400)]
    client = ClientDouble(fail_at_request=failing_request)

    with pytest.raises(RuntimeError, match="the stand-in provider refused the request"):
        embedder_with(client).embed(texts)

    assert len(client.requests) == failing_request
